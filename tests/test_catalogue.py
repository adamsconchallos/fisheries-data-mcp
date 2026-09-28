"""Offline checks for research discovery and honest download capabilities."""

import json
import unittest
from unittest.mock import patch

from mcp import Client

from fisheries_data_mcp import catalogue
from fisheries_data_mcp.server import mcp


class CatalogueTests(unittest.TestCase):
    def test_salmon_question_finds_quantity_value_and_lice_in_both_languages(self):
        questions = (
            "I want to study salmon production growth and production value in Norway and lice by year",
            "Quiero investigar crecimiento de producción y valor de salmones en Noruega y piojos por año",
        )
        for question in questions:
            with self.subTest(question=question):
                result = catalogue.search_data_catalogue(question)
                candidates = result["results"]
                self.assertTrue(any(
                    "fishstat_aquaculture_records" in entry["download_tools"]
                    for entry in candidates
                ), candidates)
                self.assertTrue(any(
                    entry["provider"] == "barentswatch" and entry["download_tools"]
                    for entry in candidates
                ), candidates)
                self.assertIn("not confirmed observations", result["note"])

    def test_inventory_distinguishes_documentation_from_downloads(self):
        inventory = catalogue.list_datasets()
        self.assertEqual(inventory["count"], len(inventory["datasets"]))
        self.assertEqual(
            {entry["provider"] for entry in inventory["datasets"]},
            {"fishstat", "barentswatch", "copernicus_marine", "comtrade"},
        )
        statuses = set()
        for summary in inventory["datasets"]:
            with self.subTest(dataset=summary["id"]):
                entry = catalogue.describe_data_dataset(summary["id"])
                statuses.add(entry["availability"])
                expected = "downloadable" if entry["download_tools"] else "catalogue_only"
                self.assertEqual(entry["availability"], expected)
                self.assertTrue(entry["availability_note"])
                for field in ("variables", "coverage", "dimensions", "access", "limitations", "references"):
                    self.assertTrue(entry[field], field)
                self.assertRegex(entry["verified_on"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertTrue(all(url.startswith("https://") for url in entry["references"]))
                self.assertTrue(all(variable.get("unit") for variable in entry["variables"]))
        self.assertEqual(statuses, {"downloadable", "catalogue_only"})

    def test_unconnected_research_topics_remain_discoverable(self):
        for topic in ("trade", "employment", "food balance"):
            with self.subTest(topic=topic):
                result = catalogue.search_data_catalogue(topic, limit=50)
                entries = [entry for entry in result["results"] if entry["availability"] == "catalogue_only"]
                self.assertTrue(entries, result)
                self.assertTrue(all(not entry["download_tools"] for entry in entries))

    def test_provider_filter_and_unknown_topic_do_not_invent_sources(self):
        selected = catalogue.list_datasets("fishstat")
        self.assertTrue(selected["datasets"])
        self.assertTrue(all(entry["provider"] == "fishstat" for entry in selected["datasets"]))
        result = catalogue.search_data_catalogue("zzunsupportedtopiczz", provider="fishstat")
        self.assertEqual(result["total_matches"], 0)
        self.assertEqual(result["results"], [])
        self.assertEqual(result["query_terms_without_matches"], ["zzunsupportedtopiczz"])
        self.assertIn("not proof that data do not exist", result["note"])

    def test_negative_mentions_do_not_claim_variable_coverage(self):
        entry = {
            "id": "test_aquaculture", "provider": "fishstat", "title": "Aquaculture production",
            "description": "Annual aquatic production quantities", "topics": ["production", "producción"],
            "variables": [{"name": "Quantity", "description": "Reported tonnes"}],
            "dimensions": ["country", "year"], "coverage": {"geography": "Global"},
            "limitations": ["Cattle production is not covered."], "download_tools": [],
            "availability": "catalogue_only", "availability_note": "No connector", "verified_on": "2026-09-28",
        }
        with patch.object(catalogue, "_load_entries", return_value=[entry]):
            cattle = catalogue.search_data_catalogue("cattle")
            partial = catalogue.search_data_catalogue("cattle production")
            accented = catalogue.search_data_catalogue("PRODUCCION")
        self.assertEqual(cattle["results"], [])
        self.assertEqual(partial["query_terms_without_matches"], ["cattle"])
        self.assertEqual(partial["results"][0]["matched_terms"], ["production"])
        self.assertEqual(accented["results"][0]["id"], "test_aquaculture")

    def test_invalid_selections_fail_explicitly(self):
        with self.assertRaisesRegex(ValueError, "provider"):
            catalogue.list_datasets("unconnected")
        with self.assertRaisesRegex(ValueError, "provider"):
            catalogue.search_data_catalogue("production", provider="unconnected")
        for limit in (0, 51, True, "10"):
            with self.subTest(limit=limit), self.assertRaisesRegex(ValueError, "limit"):
                catalogue.search_data_catalogue("production", limit=limit)
        with self.assertRaisesRegex(ValueError, "topic"):
            catalogue.search_data_catalogue(" ")
        with self.assertRaisesRegex(ValueError, "Unknown dataset_id"):
            catalogue.describe_data_dataset("not_a_real_dataset")


class CatalogueMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_catalogue_calls_work_and_all_advertised_tools_exist(self):
        async with Client(mcp) as client:
            names = {tool.name for tool in (await client.list_tools()).tools}
            self.assertTrue(
                {"list_datasets", "search_data_catalogue", "describe_data_dataset"} <= names
            )
            result = await client.call_tool("list_datasets", {"provider": "all"})
            self.assertFalse(result.is_error, result.content)
            inventory = json.loads(result.content[0].text)
            for entry in inventory["datasets"]:
                detail = await client.call_tool("describe_data_dataset", {"dataset_id": entry["id"]})
                self.assertFalse(detail.is_error, detail.content)
                data = json.loads(detail.content[0].text)
                advertised = set(data["download_tools"]) | set(data.get("search_tools", []))
                self.assertTrue(advertised <= names, f"{data['id']}: missing tools {advertised - names}")
            search = await client.call_tool("search_data_catalogue", {"query": "salmon lice"})
            self.assertFalse(search.is_error, search.content)
            self.assertTrue(json.loads(search.content[0].text)["results"])


if __name__ == "__main__":
    unittest.main()
