"""Verify local credentials reach both providers before their imports."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fisheries_data_mcp import settings


class CredentialSettingsTests(unittest.TestCase):
    def test_project_env_is_found_without_using_the_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / ".venv").mkdir()
            (project / ".env").write_text(
                "BARENTSWATCH_CLIENT_ID=from_file\n"
                "BARENTSWATCH_CLIENT_SECRET=${HOME}sample_secret\n"
                "COPERNICUSMARINE_SERVICE_USERNAME=\n"
                "UN_COMTRADE_API_KEY=example_comtrade_key\n"
                "UNRELATED_VARIABLE=ignored\n",
                encoding="utf-8",
            )
            with patch.object(settings.sys, "prefix", str(project / ".venv")):
                with patch.dict(os.environ, {"BARENTSWATCH_CLIENT_ID": "from_process"}, clear=True):
                    settings.load_local_credentials()
                    self.assertEqual(os.environ["BARENTSWATCH_CLIENT_ID"], "from_process")
                    self.assertEqual(os.environ["BARENTSWATCH_CLIENT_SECRET"], "${HOME}sample_secret")
                    self.assertNotIn("COPERNICUSMARINE_SERVICE_USERNAME", os.environ)
                    self.assertEqual(os.environ["UN_COMTRADE_API_KEY"], "example_comtrade_key")
                    self.assertNotIn("UNRELATED_VARIABLE", os.environ)

    def test_copernicus_sees_env_credentials_on_fresh_server_import(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "COPERNICUSMARINE_SERVICE_USERNAME=example_user\n"
                "COPERNICUSMARINE_SERVICE_PASSWORD=example_password\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            for key in (
                "COPERNICUSMARINE_SERVICE_USERNAME",
                "COPERNICUSMARINE_SERVICE_PASSWORD",
            ):
                environment.pop(key, None)
            environment["FISHERIES_MCP_ENV_FILE"] = str(env_file)
            source_dir = Path(__file__).resolve().parents[1] / "src"
            environment["PYTHONPATH"] = os.pathsep.join(
                [str(source_dir), environment.get("PYTHONPATH", "")]
            )
            code = (
                "from fisheries_data_mcp import server\n"
                "from copernicusmarine.core_functions import environment_variables as credentials\n"
                "assert credentials.COPERNICUSMARINE_SERVICE_USERNAME == 'example_user'\n"
                "assert credentials.COPERNICUSMARINE_SERVICE_PASSWORD == 'example_password'\n"
            )
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=directory,
                env=environment,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
