import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs
from urllib.error import HTTPError

from fisheries_data_mcp import barentswatch


class BarentsWatchTests(unittest.TestCase):
    @patch.dict(
        os.environ,
        {"BARENTSWATCH_CLIENT_ID": "research-client", "BARENTSWATCH_CLIENT_SECRET": "test-secret"},
    )
    @patch.object(barentswatch, "urlopen")
    def test_lice_query_authenticates_and_preserves_source_values(self, open_url):
        upstream = {
            "localityNo": 35657,
            "year": 2022,
            "type": "avgAdultFemaleLice",
            "data": [{"week": 34, "value": 0}, {"week": 35, "value": None}],
        }
        open_url.side_effect = [
            io.BytesIO(json.dumps({"access_token": "test-token"}).encode()),
            io.BytesIO(json.dumps(upstream).encode()),
        ]

        result = barentswatch.lice_by_locality(35657, 2022)

        token_request = open_url.call_args_list[0].args[0]
        data_request = open_url.call_args_list[1].args[0]
        self.assertEqual(token_request.full_url, barentswatch.TOKEN_URL)
        self.assertEqual(token_request.get_method(), "POST")
        self.assertEqual(parse_qs(token_request.data.decode())["scope"], ["api"])
        self.assertEqual(
            data_request.full_url,
            "https://www.barentswatch.no/bwapi/v1/geodata/fishhealth/locality/"
            "35657/avgfemalelice/2022",
        )
        self.assertEqual(data_request.get_header("Authorization"), "Bearer test-token")
        self.assertEqual(
            result["rows"],
            [
                {"locality_id": 35657, "year": 2022, "week": 34, "value": 0},
                {"locality_id": 35657, "year": 2022, "week": 35, "value": None},
            ],
        )
        self.assertEqual(result["unit"], "adult female lice per fish")

    @patch.dict(os.environ, {}, clear=True)
    @patch.object(barentswatch, "urlopen")
    def test_missing_credentials_fails_before_network_request(self, open_url):
        with self.assertRaisesRegex(barentswatch.BarentsWatchError, "BARENTSWATCH_CLIENT_ID"):
            barentswatch.lice_by_locality(35657, 2022)
        open_url.assert_not_called()

    def test_rejects_non_integer_identifiers(self):
        with self.assertRaises(ValueError):
            barentswatch.lice_by_locality(True, 2022)
        with self.assertRaises(ValueError):
            barentswatch.lice_by_locality(35657, "2022")

    @patch.object(barentswatch, "_query")
    def test_locality_search_encodes_query_and_discloses_truncation(self, query):
        records = [{"localityNo": 1, "name": "A & B"}, {"localityNo": 2, "name": "A"}]
        query.return_value = ("https://example.test/localities", records)
        result = barentswatch.search_localities("A & B", limit=1)
        query.assert_called_once_with("v1/geodata/fishhealth/localities?query=A+%26+B")
        self.assertEqual(result["rows"], records[:1])
        self.assertEqual(result["total_matches"], 2)
        self.assertTrue(result["truncated"])

    @patch.object(barentswatch, "_query")
    def test_lice_stages_preserve_unreported_zeroes_and_flags(self, query):
        records = [
            {"week": 1, "avgAdultFemaleLice": 0, "avgMobileLice": 0, "avgStationaryLice": 0, "hasReportedLice": False},
            {"week": 3, "avgAdultFemaleLice": 0, "avgMobileLice": 0.1, "avgStationaryLice": 0, "hasReportedLice": True},
        ]
        query.return_value = ("https://example.test/lice", {"localityNo": 35657, "year": 2024, "data": records})
        result = barentswatch.locality_data(35657, 2024)
        self.assertEqual(len(result["rows"]), 2)  # Missing week 2 is not filled.
        self.assertFalse(result["rows"][0]["hasReportedLice"])
        self.assertEqual(result["rows"][0]["avgAdultFemaleLice"], 0)
        self.assertIn("must not be interpreted", " ".join(result["notes"]))

    @patch.object(barentswatch, "_query")
    def test_temperature_nulls_and_nested_treatments_are_preserved(self, query):
        rows = [{"week": 2, "seaTemperature": None, "hasReported": False}]
        query.return_value = ("https://example.test/temp", {"localityNo": 35657, "year": 2024, "data": rows})
        result = barentswatch.locality_data(35657, 2024, "sea_temperature")
        self.assertIsNone(result["rows"][0]["seaTemperature"])
        self.assertFalse(result["rows"][0]["hasReported"])
        treatments = [{"week": 36, "medicinalTreatments": [{"name": "Emamectin benzoat", "entireLocality": True}], "version": 1}]
        query.return_value = ("https://example.test/treat", {"localityNo": 35657, "year": 2022, "data": treatments})
        result = barentswatch.locality_data(35657, 2022, "treatments")
        self.assertEqual(result["rows"][0]["medicinalTreatments"], treatments[0]["medicinalTreatments"])

    @patch.object(barentswatch, "_query")
    def test_disease_cases_can_span_years_and_capacity_uses_week_keys(self, query):
        query.return_value = ("https://example.test/disease", [{"name": "PANKREASSYKDOM", "diagnosisDate": "2023-02-03", "closureDate": "2024-07-15"}])
        result = barentswatch.locality_data(35657, 2024, "diseases")
        self.assertEqual(result["rows"][0]["diagnosisDate"], "2023-02-03")
        self.assertIn("new diagnosis", " ".join(result["notes"]))
        query.return_value = ("https://example.test/capacity", {"1": {"capacity": 7020.0}, "3": {"capacity": None}})
        result = barentswatch.locality_data(35657, 2024, "capacity")
        self.assertEqual([row["week"] for row in result["rows"]], [1, 3])
        self.assertIsNone(result["rows"][1]["capacity"])
        self.assertIn("no unit field", " ".join(result["notes"]))

    @patch.object(barentswatch, "_query")
    def test_snapshot_retains_license_species_and_reporting_flags(self, query):
        payload = {"locality": {"no": 35657}, "aquaCultureRegister": {"species": ["Laks"], "unit": "TN"}, "liceReport": {"hasReported": False, "isFallow": True}}
        query.return_value = ("https://example.test/detail", payload)
        result = barentswatch.locality_details(35657, 2024, 34)
        self.assertEqual(result["data"], payload)
        query.assert_called_once_with("v2/geodata/fishhealth/locality/35657/2024/34")

    @patch.object(barentswatch, "_query")
    def test_invalid_queries_are_rejected_before_authentication(self, query):
        for args in [(True, 2024, "lice_stages"), (1, 2011, "lice_stages"), (1, 2024, "arbitrary/path"), (1, 2024, [])]:
            with self.assertRaises(ValueError):
                barentswatch.locality_data(*args)
        with self.assertRaises(ValueError):
            barentswatch.locality_details(35657, 2024, 53)  # 2024 has 52 ISO weeks.
        with self.assertRaises(ValueError):
            barentswatch.search_localities("x", limit=True)
        query.assert_not_called()

    @patch.object(barentswatch, "_query")
    def test_wrong_site_and_malformed_source_shapes_fail_explicitly(self, query):
        query.return_value = ("https://example.test", {"localityNo": 999, "year": 2024, "data": []})
        with self.assertRaisesRegex(barentswatch.BarentsWatchError, "different locality"):
            barentswatch.locality_data(35657, 2024)
        query.return_value = ("https://example.test", {"not-a-week": {"capacity": 1}})
        with self.assertRaisesRegex(barentswatch.BarentsWatchError, "unexpected response"):
            barentswatch.locality_data(35657, 2024, "capacity")

    @patch.object(barentswatch, "urlopen")
    def test_auth_failure_message_does_not_include_provider_body(self, open_url):
        open_url.side_effect = HTTPError("https://example.test", 401, "secret provider body", {}, None)
        from urllib.request import Request
        with self.assertRaisesRegex(barentswatch.BarentsWatchError, "HTTP 401") as caught:
            barentswatch._read_json(Request("https://example.test"), purpose="authentication")
        self.assertNotIn("secret", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
