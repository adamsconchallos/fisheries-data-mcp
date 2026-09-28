"""Check that a real MCP client can discover and call a data tool."""

import csv
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import copernicusmarine
from mcp import Client, StdioServerParameters

from fisheries_data_mcp import fishstat
from fisheries_data_mcp.server import mcp


class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_server_starts_over_stdio(self):
        source_dir = Path(__file__).resolve().parents[1] / "src"
        package_site = Path(copernicusmarine.__file__).resolve().parents[1]
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "fisheries_data_mcp.server"],
            cwd=source_dir.parent,
            env={
                "PYTHONPATH": os.pathsep.join(
                    [str(source_dir), str(package_site), os.environ.get("PYTHONPATH", "")]
                )
            },
        )
        async with Client(params) as client:
            names = {tool.name for tool in (await client.list_tools()).tools}
        self.assertIn("fishstat_production_by_country", names)
        self.assertIn("fishstat_aquaculture_records", names)
        self.assertIn("search_fishstat_countries", names)
        self.assertIn("describe_copernicus_dataset", names)
        self.assertIn("comtrade_trade_records", names)

    async def test_fishstat_query_is_discoverable_and_exports_csv(self):
        sample = {
            "query": "oyster",
            "year": 2024,
            "source": "all",
            "unit": "tonnes live weight",
            "table_structure": fishstat.TABLE_STRUCTURE,
            "source_url": "https://www.fao.org/fishery/static/Data/GlobalProduction_2026.1.0.zip",
            "rows": [{"country": "Example", "country_code": "999", "year": 2024, "tonnes": 12.5, "status": "A", "warnings": []}],
        }
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"FISHERIES_MCP_OUTPUT_DIR": directory}):
                with patch("fisheries_data_mcp.server.fishstat.production_by_country", return_value=sample):
                    async with Client(mcp) as client:
                        listed = await client.list_tools()
                        names = {tool.name for tool in listed.tools}
                        self.assertIn("fishstat_production_by_country", names)
                        self.assertIn("search_copernicus_datasets", names)
                        self.assertIn("describe_copernicus_dataset", names)
                        result = await client.call_tool(
                            "fishstat_production_by_country", {"query": "oyster", "year": 2024}
                        )
                    self.assertFalse(result.is_error, result.content)
                    output = json.loads(result.content[0].text)
                    self.assertEqual(output["rows"][0]["tonnes"], 12.5)
                    self.assertTrue(Path(output["csv_path"]).is_file())
                    self.assertTrue(Path(output["metadata_path"]).is_file())
                    with Path(output["csv_path"]).open(encoding="utf-8-sig", newline="") as handle:
                        table = csv.DictReader(handle)
                        self.assertEqual(output["table_structure"]["columns"], table.fieldnames)
                        self.assertEqual(output["table_structure"]["row_count"], len(list(table)))
                    saved_metadata = json.loads(Path(output["metadata_path"]).read_text(encoding="utf-8"))
                    self.assertEqual(saved_metadata["table_structure"], output["table_structure"])
                    self.assertEqual(
                        set(output["table_structure"]["column_descriptions"]),
                        set(output["table_structure"]["columns"]),
                    )


if __name__ == "__main__":
    unittest.main()
