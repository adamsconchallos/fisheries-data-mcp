import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

from fisheries_data_mcp import copernicus


def catalogue():
    variable = NS(
        short_name="thetao", standard_name="sea_water_potential_temperature", units="degrees_C",
        bbox=[-20, 40, 0, 60],
        coordinates=[NS(coordinate_id="time", minimum_value="2024-01-01T00:00:00Z",
                        maximum_value="2024-12-31T23:59:59Z", coordinate_unit="UTC"),
                     NS(coordinate_id="depth", minimum_value=0.5,
                        maximum_value=100.0, coordinate_unit="m")],
    )
    version = NS(label="202401", parts=[NS(services=[NS(variables=[variable])])])
    dataset = NS(dataset_id="example_dataset", dataset_name="Ocean temperature", versions=[version])
    product = NS(product_id="EXAMPLE_PRODUCT", title="Ocean physics",
                 digital_object_identifier="10.48670/moi-00000", datasets=[dataset])
    return NS(products=[product])


class CopernicusTests(unittest.TestCase):
    def test_search_returns_dataset_and_variable(self):
        with patch.object(copernicus.copernicusmarine, "describe", return_value=catalogue()) as describe:
            result = copernicus.search_datasets("temperature", 1)
        describe.assert_called_once_with(contains=["temperature"], disable_progress_bar=True)
        self.assertEqual(result["datasets"][0]["variables"], ["thetao"])
        self.assertEqual(result["datasets"][0]["product_doi"], "10.48670/moi-00000")

    def test_describe_dataset_returns_scoped_metadata_without_download(self):
        with patch.object(copernicus.copernicusmarine, "describe", return_value=catalogue()) as describe, \
             patch.object(copernicus.copernicusmarine, "subset") as subset:
            result = copernicus.describe_dataset("example_dataset")
        describe.assert_called_once_with(dataset_id="example_dataset", disable_progress_bar=True)
        subset.assert_not_called()
        self.assertEqual(result["dataset_version"], "202401")
        self.assertEqual(result["product_doi"], "10.48670/moi-00000")
        self.assertEqual(result["variable_count"], 1)
        self.assertEqual(result["variables"][0]["standard_name"], "sea_water_potential_temperature")
        self.assertEqual(result["variables"][0]["time"]["minimum"], "2024-01-01T00:00:00Z")
        self.assertEqual(result["variables"][0]["depth"]["maximum"], 100.0)

    def test_bad_variable_rejected_before_authentication_or_download(self):
        with patch.object(copernicus.copernicusmarine, "describe", return_value=catalogue()), \
             patch.object(copernicus.copernicusmarine, "login") as login, \
             patch.object(copernicus.copernicusmarine, "subset") as subset:
            with self.assertRaisesRegex(ValueError, "unavailable"):
                copernicus.subset_dataset("example_dataset", "cattle", -10, -5, 45, 50,
                                         "2024-05-01", "2024-05-02", ".")
        login.assert_not_called()
        subset.assert_not_called()

    def test_large_preview_stops_before_download(self):
        calls = []

        def fake_subset(*, file_format="netcdf", **kwargs):
            calls.append(kwargs)
            return NS(status="001", file_size=250.0, data_transfer_size=10.0)

        with tempfile.TemporaryDirectory() as folder, \
             patch.object(copernicus.copernicusmarine, "describe", return_value=catalogue()), \
             patch.object(copernicus.copernicusmarine, "login", return_value=True), \
             patch.object(copernicus.copernicusmarine, "subset", new=fake_subset):
            with self.assertRaisesRegex(ValueError, "200 MB limit"):
                copernicus.subset_dataset("example_dataset", "thetao", -10, -5, 45, 50,
                                         "2024-05-01", "2024-05-02", folder)
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0]["dry_run"])

    def test_small_subset_returns_local_file_and_provenance(self):
        calls = []

        def fake_subset(*, file_format="netcdf", **kwargs):
            calls.append(kwargs)
            if kwargs.get("dry_run"):
                return NS(status="001", file_size=1.0, data_transfer_size=2.0)
            Path(kwargs["output_directory"], "result.nc").write_bytes(b"test")
            return NS(status="000", file_path="result.nc")

        with tempfile.TemporaryDirectory() as folder, \
             patch.object(copernicus.copernicusmarine, "describe", return_value=catalogue()), \
             patch.object(copernicus.copernicusmarine, "login", return_value=True), \
             patch.object(copernicus.copernicusmarine, "subset", new=fake_subset):
            result = copernicus.subset_dataset("example_dataset", "thetao", -10, -5, 45, 50,
                                              "2024-05-01", "2024-05-02", folder)
            self.assertTrue(Path(result["file_path"]).is_file())
            sidecar = Path(result["metadata_path"])
            self.assertTrue(sidecar.is_file())
            self.assertEqual(json.loads(sidecar.read_text(encoding="utf-8"))["product_doi"],
                             "10.48670/moi-00000")
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[0]["dry_run"])
        self.assertNotIn("dry_run", calls[1])
        self.assertEqual(calls[1]["dataset_version"], "202401")
        self.assertEqual(calls[1]["variables"], ["thetao"])
        self.assertEqual(calls[1]["minimum_longitude"], -10)
        self.assertEqual(result["dataset_version"], "202401")
        self.assertEqual(result["unit"], "degrees_C")
        self.assertIn("10.48670/moi-00000", result["citation"])


if __name__ == "__main__":
    unittest.main()
