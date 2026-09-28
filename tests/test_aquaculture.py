"""Offline checks for the official Aquaculture quantity/value table formats."""

import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from fisheries_data_mcp import fishstat
from test_fishstat import _sample_zip as _global_production_zip


def _aquaculture_zip(version="2026.1.0"):
    header = (
        "COUNTRY.UN_CODE,SPECIES.ALPHA_3_CODE,AREA.CODE,"
        "ENVIRONMENT.ALPHA_2_CODE,MEASURE,PERIOD,VALUE,STATUS\n"
    )
    tables = {
        "CL_FI_SPECIES_GROUPS.csv": (
            "3A_Code,Name_En,Name_Es,Scientific_Name,ISSCAAP_Group_En,Major_Group\n"
            "SAL,Atlantic salmon,Salmon del Atlantico,Salmo salar,Salmonids,PISCES\n"
            "TRR,Rainbow trout,Trucha arco iris,Oncorhynchus mykiss,Salmonids,PISCES\n"
            "LAM,Kelp,Alga,Saccharina latissima,Brown seaweeds,PLANTAE AQUATICAE\n"
        ),
        "CL_FI_COUNTRY_GROUPS.csv": (
            "UN_Code,ISO2_Code,ISO3_Code,Name_En,Name_Es,Name_Fr\n"
            "578,NO,NOR,Norway,Noruega,Norvege\n"
            "574,NF,NFK,Norfolk Island,Isla Norfolk,Ile Norfolk\n"
            "724,ES,ESP,Spain,Espana,Espagne\n"
        ),
        "CL_FI_PRODENVIRONMENT.csv": (
            "Code,Identifier,Name_En\nIN,1,Freshwater\nBW,2,Brackishwater\nMA,3,Marine\n"
        ),
        "CL_FI_SYMBOL_SDMX.csv": (
            "Symbol,Name_En\nA,Official value\nN,Not significant (<0.5)\n"
            "O,Missing value\nQ,Missing value; suppressed\n"
        ),
        "CL_History.txt": (
            f"{version}  30-Mar-2026  release of Aquaculture/Capture/GlobalProduction 1950-2024\n"
        ),
        "Aquaculture_Quantity.csv": header + (
            "578,SAL,27,MA,Q_tlw,2024,10.25,A\n"
            "578,SAL,27,BW,Q_tlw,2024,2.5,A\n"
            "578,SAL,05,IN,Q_tlw,2024,0,N\n"
            "578,SAL,27,MA,Q_tlw,2023,9,A\n"
            "578,SAL,27,MA,Q_tlw,1983,5,A\n"
            "578,SAL,27,MA,Q_tlw,1984,6,A\n"
            "724,SAL,27,MA,Q_tlw,2024,99,A\n"
            "578,TRR,27,MA,Q_tlw,2024,88,A\n"
            "578,LAM,27,MA,Q_tlw,2024,7,A\n"
        ),
        "Aquaculture_Value.csv": header + (
            "578,SAL,27,MA,V_USD_1000,2024,123.456,A\n"
            "578,SAL,27,BW,V_USD_1000,2024,0,O\n"
            "578,SAL,05,IN,V_USD_1000,2024,0,Q\n"
            "578,SAL,27,MA,V_USD_1000,2023,0,A\n"
            "578,SAL,27,BW,V_USD_1000,2023,0,N\n"
            "578,SAL,05,IN,V_USD_1000,2023,,A\n"
            "578,SAL,27,MA,V_USD_1000,1984,5.1,A\n"
            "724,SAL,27,MA,V_USD_1000,2024,998,A\n"
            "578,TRR,27,MA,V_USD_1000,2024,887,A\n"
            "578,LAM,27,MA,V_USD_1000,2024,3.5,A\n"
        ),
    }
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, contents in tables.items():
            archive.writestr(name, contents)
    return data.getvalue()


class AquacultureTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.archive = self.folder / fishstat.AQUACULTURE_ZIP_NAME
        self.archive.write_bytes(_aquaculture_zip())
        environment = patch.dict(os.environ, {
            "FISHSTAT_AQUACULTURE_ZIP": str(self.archive),
            "FISHSTAT_ZIP": str(self.folder / "unused-global-production.zip"),
        })
        environment.start()
        self.addCleanup(environment.stop)
        network = patch("urllib.request.urlopen", side_effect=AssertionError("Unexpected network request"))
        network.start()
        self.addCleanup(network.stop)

    def test_filters_country_species_and_year_without_combining_dimensions(self):
        result = fishstat.aquaculture_records(
            "", 2024, 2024, country_code="578", species_code="sal"
        )
        rows = result["rows"]
        self.assertEqual(len(rows), 6)
        self.assertEqual({row["country_code"] for row in rows}, {"578"})
        self.assertEqual({row["species_code"] for row in rows}, {"SAL"})
        self.assertEqual({row["year"] for row in rows}, {2024})
        quantity = [row for row in rows if row["measure"] == "Q_tlw"]
        self.assertEqual(
            {(row["area_code"], row["environment_code"], row["value"]) for row in quantity},
            {("27", "MA", 10.25), ("27", "BW", 2.5), ("05", "IN", 0.0)},
        )
        monetary = next(row for row in rows if row["measure"] == "V_USD_1000" and row["status"] == "A")
        self.assertEqual(monetary["value"], 123.456)
        self.assertEqual(monetary["unit"], "thousands of USD")
        self.assertEqual(result["collection"], "Aquaculture")
        self.assertEqual(result["source_url"], fishstat.AQUACULTURE_SOURCE_URL)

    def test_missing_and_suppressed_values_do_not_become_reported_zeroes(self):
        result = fishstat.aquaculture_records("salmon", 2023, 2024, "578", measure="value")
        rows = result["rows"]
        self.assertEqual(len(rows), 6)
        self.assertEqual({row["measure"] for row in rows}, {"V_USD_1000"})
        by_key = {(row["year"], row["area_code"], row["environment_code"]): row for row in rows}
        self.assertIsNone(by_key[(2024, "27", "BW")]["value"])
        self.assertEqual(by_key[(2024, "27", "BW")]["status"], "O")
        self.assertIsNone(by_key[(2024, "05", "IN")]["value"])
        self.assertEqual(by_key[(2024, "05", "IN")]["status"], "Q")
        self.assertIsNone(by_key[(2023, "05", "IN")]["value"])
        self.assertEqual(by_key[(2023, "27", "MA")]["value"], 0.0)
        self.assertEqual(by_key[(2023, "27", "MA")]["status"], "A")
        self.assertEqual(by_key[(2023, "27", "BW")]["value"], 0.0)
        self.assertEqual(by_key[(2023, "27", "BW")]["status"], "N")
        self.assertEqual(result["status_legend"]["O"], "Missing value")

    def test_quantity_selection_and_species_specific_weight_units(self):
        salmon = fishstat.aquaculture_records("salmon", 2023, 2023, "578", measure="quantity")
        self.assertEqual(len(salmon["rows"]), 1)
        self.assertEqual(salmon["rows"][0]["value"], 9.0)
        self.assertEqual(salmon["rows"][0]["unit"], "tonnes live weight")
        plants = fishstat.aquaculture_records("algas", 2024, 2024, "578")
        by_measure = {row["measure"]: row for row in plants["rows"]}
        self.assertEqual(by_measure["Q_tlw"]["unit"], "tonnes wet weight")
        self.assertEqual(by_measure["V_USD_1000"]["unit"], "thousands of USD")
        self.assertEqual({row["species_code"] for row in plants["rows"]}, {"LAM"})

    def test_earlier_quantity_years_do_not_invent_monetary_observations(self):
        result = fishstat.aquaculture_records("salmon", 1983, 1984, "578")
        self.assertEqual(
            {(row["year"], row["measure"]) for row in result["rows"]},
            {(1983, "Q_tlw"), (1984, "Q_tlw"), (1984, "V_USD_1000")},
        )
        self.assertTrue(any("1984" in warning for warning in result["warnings"]))
        missing = fishstat.aquaculture_records("salmon", 1983, 1983, "578", measure="value")
        self.assertEqual(missing["rows"], [])
        self.assertTrue(any("1984" in warning for warning in missing["warnings"]))

    def test_country_lookup_accepts_names_and_reference_codes(self):
        for query in ("Noruega", "Norway", "578", "NOR", "NO"):
            with self.subTest(query=query):
                found = fishstat.search_countries(query)
                self.assertEqual(found["total_matches"], 1)
                self.assertEqual(found["countries"][0]["country_code"], "578")
        self.assertEqual(fishstat.search_countries("Atlantis")["countries"], [])

    def test_invalid_selection_is_rejected_and_unknown_species_returns_no_data(self):
        with self.assertRaisesRegex(ValueError, "country_code"):
            fishstat.aquaculture_records("salmon", 2024, 2024, "999")
        for start, end in ((1949, 2024), (2024, 2025), (2024, 2023), (True, 2024)):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                fishstat.aquaculture_records("salmon", start, end)
        with self.assertRaisesRegex(ValueError, "measure"):
            fishstat.aquaculture_records("salmon", 2024, 2024, measure="price")
        missing = fishstat.aquaculture_records("cattle", 2024, 2024)
        self.assertEqual(missing["rows"], [])
        self.assertTrue(missing["warnings"])

    def test_collections_download_to_separate_caches_and_reuse_them(self):
        with patch.dict(os.environ, {"LOCALAPPDATA": str(self.folder)}, clear=True):
            with patch("urllib.request.urlopen", side_effect=[
                io.BytesIO(_global_production_zip()), io.BytesIO(_aquaculture_zip())
            ]) as download:
                self.assertEqual(fishstat.search_species("oysters")["total_matches"], 2)
                self.assertEqual(fishstat.search_countries("Norway")["total_matches"], 1)
                self.assertEqual(fishstat.search_species("oysters")["total_matches"], 2)
                self.assertEqual(fishstat.search_countries("Norway")["total_matches"], 1)
        self.assertEqual(download.call_count, 2)
        self.assertEqual(
            {call.args[0].full_url for call in download.call_args_list},
            {fishstat.SOURCE_URL, fishstat.AQUACULTURE_SOURCE_URL},
        )
        cache = self.folder / "fisheries_data_mcp"
        self.assertTrue((cache / fishstat.ZIP_NAME).is_file())
        self.assertTrue((cache / fishstat.AQUACULTURE_ZIP_NAME).is_file())

    def test_aquaculture_override_rejects_wrong_release(self):
        self.archive.write_bytes(_aquaculture_zip("2027.1.0"))
        with self.assertRaisesRegex(ValueError, "Expected FishStat Aquaculture release"):
            fishstat.aquaculture_records("salmon", 2024, 2024)


if __name__ == "__main__":
    unittest.main()
