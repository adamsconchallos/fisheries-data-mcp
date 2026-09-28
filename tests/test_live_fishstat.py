"""Optional end-to-end check against the pinned official FAO release."""

import csv
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp import Client

from fisheries_data_mcp.server import mcp


@unittest.skipUnless(os.environ.get("FISHSTAT_ZIP"), "Set FISHSTAT_ZIP to the official 2026.1.0 ZIP")
class LiveFishStatTests(unittest.IsolatedAsyncioTestCase):
    async def test_oysters_2024_through_mcp(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"FISHERIES_MCP_OUTPUT_DIR": directory}):
                async with Client(mcp) as client:
                    response = await client.call_tool(
                        "fishstat_production_by_country", {"query": "ostras", "year": 2024}
                    )
                self.assertFalse(response.is_error, response.content)
                result = json.loads(response.content[0].text)
                self.assertEqual(result["weight_basis"], "live weight")
                self.assertEqual(len(result["rows"]), 58)
                china = next(row for row in result["rows"] if row["country_code"] == "156")
                self.assertEqual(china["tonnes"], 7252494.0)
                self.assertTrue(Path(result["csv_path"]).is_file())
                self.assertTrue(Path(result["metadata_path"]).is_file())


@unittest.skipUnless(os.environ.get("FISHSTAT_AQUACULTURE_ZIP"), "Set FISHSTAT_AQUACULTURE_ZIP to the official 2026.1.0 ZIP")
class LiveAquacultureTests(unittest.IsolatedAsyncioTestCase):
    async def test_norwegian_salmon_quantity_and_value_through_mcp(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"FISHERIES_MCP_OUTPUT_DIR": directory}):
                async with Client(mcp) as client:
                    response = await client.call_tool("fishstat_aquaculture_records", {
                        "query": "", "species_code": "SAL", "country_code": "578",
                        "start_year": 2012, "end_year": 2024,
                    })
                self.assertFalse(response.is_error, response.content)
                result = json.loads(response.content[0].text)
                self.assertEqual(result["row_count"], 26)
                self.assertEqual(len(result["rows_preview"]), 20)
                self.assertNotIn("rows", result)
                with Path(result["csv_path"]).open(encoding="utf-8-sig", newline="") as handle:
                    reader = csv.DictReader(handle)
                    rows = list(reader)
                    self.assertEqual(reader.fieldnames, result["table_structure"]["columns"])
                self.assertEqual(len(rows), 26)
                last_year = {row["measure"]: row for row in rows if row["year"] == "2024"}
                self.assertEqual(float(last_year["Q_tlw"]["value"]), 1552887.32)
                self.assertEqual(float(last_year["V_USD_1000"]["value"]), 9628744.361)
                self.assertEqual(last_year["V_USD_1000"]["unit"], "thousands of USD")
                metadata = json.loads(Path(result["metadata_path"]).read_text(encoding="utf-8"))
                self.assertEqual(metadata["table_structure"]["row_count"], 26)
                self.assertEqual(metadata["collection"], "Aquaculture")


if __name__ == "__main__":
    unittest.main()
