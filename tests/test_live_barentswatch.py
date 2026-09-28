"""Opt-in, sequential checks of authenticated BarentsWatch discovery and exports."""

import csv
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp import Client

from fisheries_data_mcp.server import mcp


@unittest.skipUnless(os.environ.get("FISHERIES_MCP_LIVE_BARENTSWATCH") == "1",
                     "Set FISHERIES_MCP_LIVE_BARENTSWATCH=1 to use local provider credentials")
class LiveBarentsWatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_find_site_then_download_lice_and_site_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"FISHERIES_MCP_OUTPUT_DIR": directory}):
                async with Client(mcp) as client:
                    found = await client.call_tool("barentswatch_search_localities", {"query": "35657", "limit": 5})
                    self.assertFalse(found.is_error, found.content)
                    sites = json.loads(found.content[0].text)
                    self.assertIn(35657, [row["localityNo"] for row in sites["rows"]])
                    response = await client.call_tool("barentswatch_get_locality_data", {
                        "locality_id": 35657, "year": 2024, "dataset": "lice_stages",
                    })
                    self.assertFalse(response.is_error, response.content)
                    result = json.loads(response.content[0].text)
                    self.assertGreater(result["row_count"], 0)
                    self.assertLessEqual(len(result["rows_preview"]), 20)
                    with Path(result["csv_path"]).open(encoding="utf-8-sig", newline="") as handle:
                        reader = csv.DictReader(handle)
                        self.assertIn("hasReportedLice", reader.fieldnames)
                        rows = list(reader)
                    self.assertEqual(len(rows), result["row_count"])
                    self.assertEqual({row["locality_id"] for row in rows}, {"35657"})
                    metadata = json.loads(Path(result["metadata_path"]).read_text(encoding="utf-8"))
                    self.assertTrue(any("hasReportedLice" in note for note in metadata["notes"]))
                    snapshot = await client.call_tool("barentswatch_get_locality_details", {
                        "locality_id": 35657, "year": 2024, "week": 20,
                    })
                    self.assertFalse(snapshot.is_error, snapshot.content)
                    snapshot_result = json.loads(snapshot.content[0].text)
                    saved = json.loads(Path(snapshot_result["json_path"]).read_text(encoding="utf-8"))
                    self.assertEqual(saved, snapshot_result["data"])
                    self.assertEqual(saved["locality"]["no"], 35657)
                    self.assertTrue(Path(snapshot_result["metadata_path"]).is_file())
