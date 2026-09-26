import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs

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


if __name__ == "__main__":
    unittest.main()
