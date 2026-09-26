"""Optional end-to-end check against the pinned official FAO release."""

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


if __name__ == "__main__":
    unittest.main()
