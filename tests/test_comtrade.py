"""Offline checks for UN Comtrade API selection, limits and MCP export."""

import csv
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from mcp import Client

from fisheries_data_mcp import comtrade
from fisheries_data_mcp.server import mcp


SAMPLE_ROW = {
    "period": 2023,
    "reporterCode": 152,
    "partnerCode": 0,
    "cmdCode": "0302",
    "flowCode": "X",
    "primaryValue": 1250000,
    "netWgt": 500000,
    "qty": None,
    "qtyUnitAbbr": None,
    "isReported": True,
}


class ComtradeTests(unittest.TestCase):
    def test_search_reference_uses_official_codes_and_retains_leading_zeroes(self):
        comtrade._reference.cache_clear()
        payload = {"results": [
            {"id": "0302", "text": "0302 - Fish; fresh or chilled", "standardUnitAbbr": "kg"},
            {"id": "0303", "text": "0303 - Fish; frozen", "standardUnitAbbr": "kg"},
        ]}
        with patch.object(comtrade, "_get_json", return_value=payload) as fetch:
            result = comtrade.search_reference("commodity", "fresh", classification="H6")
        self.assertEqual(result["results"], [
            {"code": "0302", "description": "0302 - Fish; fresh or chilled", "standard_unit": "kg"}
        ])
        self.assertEqual(result["reference_url"], "https://comtradeapi.un.org/files/v1/app/reference/H6.json")
        fetch.assert_called_once_with(result["reference_url"])
        comtrade._reference.cache_clear()

    def test_missing_key_stops_before_api_call(self):
        with patch.dict(os.environ, {"UN_COMTRADE_API_KEY": ""}):
            with patch.object(comtrade, "_get_json") as fetch:
                with self.assertRaisesRegex(RuntimeError, "UN_COMTRADE_API_KEY"):
                    comtrade.trade_records("2023", 152, "0302", "X")
        fetch.assert_not_called()

    def test_keyed_query_preserves_source_rows_and_safe_url(self):
        with patch.dict(os.environ, {"UN_COMTRADE_API_KEY": "private-test-key"}):
            with patch.object(comtrade, "_get_json", return_value={"count": 1, "data": [SAMPLE_ROW]}) as fetch:
                result = comtrade.trade_records("2023", 152, "0302", "X")
        url = fetch.call_args.args[0]
        params = parse_qs(urlparse(url).query)
        self.assertIn("/data/v1/get/C/A/HS", url)
        self.assertEqual(params["cmdCode"], ["0302"])
        self.assertEqual(params["partnerCode"], ["0"])
        self.assertEqual(params["maxRecords"], ["100000"])
        self.assertEqual(params["breakdownMode"], ["classic"])
        self.assertEqual(params["subscription-key"], ["private-test-key"])
        self.assertEqual(result["rows"], [SAMPLE_ROW])
        self.assertFalse(result["possibly_truncated"])
        self.assertNotIn("private-test-key", json.dumps(result))

    def test_keyed_query_never_exposes_key_and_flags_incomplete_result(self):
        with patch.dict(os.environ, {"UN_COMTRADE_API_KEY": "private-test-key"}):
            with patch.object(comtrade, "_get_json", return_value={"count": 3, "data": [SAMPLE_ROW]}) as fetch:
                result = comtrade.trade_records("202301", 152, "0302", "X", 0, "M", "H6")
        request_url = fetch.call_args.args[0]
        self.assertIn("/data/v1/get/C/M/H6", request_url)
        self.assertEqual(parse_qs(urlparse(request_url).query)["maxRecords"], ["100000"])
        self.assertEqual(parse_qs(urlparse(request_url).query)["subscription-key"], ["private-test-key"])
        self.assertNotIn("private-test-key", json.dumps(result))
        self.assertTrue(result["possibly_truncated"])
        self.assertTrue(result["warnings"])

    def test_invalid_selection_is_rejected_before_api_call(self):
        selections = [
            ("202313", 152, "0302", "X", 0, "M", "HS"),
            ("2023", 152, "030", "X", 0, "A", "HS"),
            ("2023", 152, "0302", "INVALID", 0, "A", "HS"),
            ("2023", True, "0302", "X", 0, "A", "HS"),
        ]
        with patch.object(comtrade, "_get_json") as fetch:
            for args in selections:
                with self.subTest(args=args), self.assertRaises(ValueError):
                    comtrade.trade_records(*args)
        fetch.assert_not_called()

    def test_http_error_never_includes_subscription_key(self):
        url = "https://comtradeapi.un.org/data/v1/get/C/A/HS?subscription-key=private-test-key"
        with patch.object(comtrade, "urlopen", side_effect=HTTPError(url, 403, "Forbidden", {}, None)):
            with self.assertRaisesRegex(RuntimeError, "API key") as caught:
                comtrade._get_json(url)
        self.assertNotIn("private-test-key", str(caught.exception))


class ComtradeMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_mcp_tool_exports_csv_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"FISHERIES_MCP_OUTPUT_DIR": directory, "UN_COMTRADE_API_KEY": "private-test-key"}):
                with patch.object(comtrade, "_get_json", return_value={"count": 1, "data": [SAMPLE_ROW]}):
                    async with Client(mcp) as client:
                        tools = {tool.name for tool in (await client.list_tools()).tools}
                        self.assertIn("search_comtrade_reference", tools)
                        self.assertIn("comtrade_trade_records", tools)
                        called = await client.call_tool("comtrade_trade_records", {
                            "period": "2023", "reporter_code": 152,
                            "commodity_code": "0302", "flow_code": "X",
                        })
            self.assertFalse(called.is_error, called.content)
            result = json.loads(called.content[0].text)
            self.assertEqual(result["row_count"], 1)
            self.assertEqual(result["rows_preview"], [SAMPLE_ROW])
            with Path(result["csv_path"]).open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["cmdCode"], "0302")
            metadata = json.loads(Path(result["metadata_path"]).read_text(encoding="utf-8"))
            self.assertEqual(metadata["table_structure"]["row_count"], 1)
            self.assertEqual(metadata["selection"]["reporter_code"], 152)
            self.assertNotIn("private-test-key", json.dumps(metadata))

    async def test_mcp_tool_reports_missing_key_without_export(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"FISHERIES_MCP_OUTPUT_DIR": directory, "UN_COMTRADE_API_KEY": ""}):
                with patch.object(comtrade, "_get_json") as fetch:
                    async with Client(mcp) as client:
                        called = await client.call_tool("comtrade_trade_records", {
                            "period": "2023", "reporter_code": 152,
                            "commodity_code": "0302", "flow_code": "X",
                        })
            self.assertTrue(called.is_error)
            self.assertIn("UN_COMTRADE_API_KEY", called.content[0].text)
            self.assertFalse(list(Path(directory).iterdir()))
            fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
