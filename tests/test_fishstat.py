"""Offline checks for FishStat species selection and annual aggregation."""

import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from fisheries_data_mcp.fishstat import (
    ZIP_NAME,
    production_by_country,
    search_species,
)


def _sample_zip(version: str = "2026.1.0", last_year: str = "2024") -> bytes:
    tables = {
        "CL_FI_SPECIES_GROUPS.csv": (
            "3A_Code,Name_En,Name_Es,Scientific_Name,ISSCAAP_Group_En,Major_Group\n"
            "OYG,Pacific cupped oyster,Ostión japonés,Magallana gigas,Oysters,MOLLUSCA\n"
            "OST,Flat and cupped oysters NEI,Ostras y ostiones NEP,Ostreidae,Oysters,MOLLUSCA\n"
            "PNF,Japanese pearl oyster,Ostra perlera japonesa,Pinctada fucata,\"Pearls, mother-of-pearl, shells\",MOLLUSCA\n"
            "HYQ,Oyster blenny,,Hypleurochilus aequipinnis,Miscellaneous coastal fishes,PISCES\n"
        ),
        "CL_FI_COUNTRY_GROUPS.csv": (
            "UN_Code,Name_En\n156,China\n724,Spain\n"
        ),
        "Global_production_quantity.csv": (
            "COUNTRY.UN_CODE,SPECIES.ALPHA_3_CODE,AREA.CODE,PRODUCTION_SOURCE_DET.CODE,MEASURE,PERIOD,VALUE,STATUS\n"
            "156,OYG,61,CAPTURE,Q_tlw,2024,10,A\n"
            "156,OYG,61,MARINE,Q_tlw,2024,40,A\n"
            "156,OST,61,MARINE,Q_tlw,2024,20,I\n"
            "156,PNF,61,MARINE,Q_tlw,2024,100,A\n"
            "156,HYQ,61,CAPTURE,Q_tlw,2024,200,A\n"
            "724,OYG,27,CAPTURE,Q_tlw,2024,5,A\n"
            "724,OYG,27,MARINE,Q_tlw,2024,0,Q\n"
            "724,OYG,27,MARINE,Q_no_1,2024,999,A\n"
            "156,OYG,61,MARINE,Q_tlw,2023,999,A\n"
        ),
        "CL_History.txt": (
            "FAO time-series history:\n"
            f"{version}  30-Mar-2026  release of Aquaculture/Capture/GlobalProduction 1950-{last_year}\n"
        ),
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, contents in tables.items():
            archive.writestr(name, contents)
    return output.getvalue()


class FishStatTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / ZIP_NAME
        self.path.write_bytes(_sample_zip())
        override = patch.dict(os.environ, {"FISHSTAT_ZIP": str(self.path)})
        override.start()
        self.addCleanup(override.stop)

    def test_oyster_alias_excludes_unrelated_names_and_counts_nei_once(self):
        found = search_species("ostras")
        self.assertEqual({item["code"] for item in found["species"]}, {"OYG", "OST"})

        result = production_by_country("oyster", 2024)
        rows = {row["country"]: row for row in result["rows"]}
        self.assertEqual(rows["China"]["tonnes"], 70.0)
        self.assertEqual(rows["China"]["status"], "A,I")
        self.assertEqual(rows["Spain"]["tonnes"], 5.0)
        self.assertIn("Q", rows["Spain"]["status"])
        self.assertTrue(any("parcial" in warning for warning in rows["Spain"]["warnings"]))
        self.assertEqual(result["measure"], "Q_tlw")
        self.assertEqual(result["weight_basis"], "live weight")
        self.assertEqual(result["dataset_version"], "2026.1.0")
        self.assertIn("[Accessed on", result["citation"])
        self.assertIn("2026.1.0.zip", result["source_url"])
        self.assertRegex(result["accessed_on"], r"\d{4}-\d{2}-\d{2}")

    def test_capture_and_aquaculture_are_separate(self):
        capture = {row["country"]: row for row in production_by_country("ostras", 2024, "capture")["rows"]}
        aquaculture = {row["country"]: row for row in production_by_country("ostras", 2024, "aquaculture")["rows"]}
        self.assertEqual(capture["China"]["tonnes"], 10.0)
        self.assertEqual(aquaculture["China"]["tonnes"], 60.0)
        self.assertIsNone(aquaculture["Spain"]["tonnes"])

    def test_specific_species_and_missing_query(self):
        result = production_by_country("", 2024, species_code="OYG")
        china = next(row for row in result["rows"] if row["country"] == "China")
        self.assertEqual(china["tonnes"], 50.0)
        self.assertEqual([item["code"] for item in result["species"]], ["OYG"])
        missing = production_by_country("vacas", 2024)
        self.assertEqual(missing["rows"], [])
        self.assertTrue(missing["warnings"])

    def test_downloads_once_to_user_cache(self):
        with patch.dict(os.environ, {"LOCALAPPDATA": self.directory.name}, clear=True):
            with patch("urllib.request.urlopen", return_value=io.BytesIO(_sample_zip())) as download:
                self.assertEqual(search_species("oysters")["total_matches"], 2)
                self.assertEqual(search_species("oysters")["total_matches"], 2)
        self.assertEqual(download.call_count, 1)
        self.assertTrue((Path(self.directory.name) / "fisheries_data_mcp" / ZIP_NAME).is_file())

    def test_rejects_wrong_release_even_with_expected_filename(self):
        self.path.write_bytes(_sample_zip("2027.1.0", "2025"))
        with self.assertRaisesRegex(ValueError, "Expected FishStat Global Production release 2026.1.0"):
            search_species("oysters")


if __name__ == "__main__":
    unittest.main()
