"""Check that local setup preserves credentials and works from another directory."""

from contextlib import chdir, redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "local_installer", Path(__file__).resolve().parents[1] / "install.py"
)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def make_project(self, directory):
        project = Path(directory) / "project with spaces"
        project.mkdir()
        scripts = project / ".venv" / ("Scripts" if os.name == "nt" else "bin")
        scripts.mkdir(parents=True)
        (scripts / ("python.exe" if os.name == "nt" else "python")).touch()
        server = scripts / ("fisheries-data-mcp.exe" if os.name == "nt" else "fisheries-data-mcp")
        server.touch()
        (project / ".env.example").write_bytes(b"BARENTSWATCH_CLIENT_ID=\n")
        return project, server

    def test_setup_from_other_directory_and_update_preserve_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            project, server = self.make_project(directory)
            output = io.StringIO()
            with (
                patch.object(installer, "__file__", str(project / "install.py")),
                patch.object(installer.subprocess, "run"),
                redirect_stdout(output),
                chdir(directory),
            ):
                self.assertEqual(installer.main(), 0)
                credentials = project / ".env"
                self.assertEqual(credentials.read_bytes(), b"BARENTSWATCH_CLIENT_ID=\n")
                credentials.write_bytes(b"BARENTSWATCH_CLIENT_ID=my-existing-id\r\n")
                self.assertEqual(installer.main(), 0)

            self.assertEqual(credentials.read_bytes(), b"BARENTSWATCH_CLIENT_ID=my-existing-id\r\n")
            config = json.loads((project / "mcp-config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["mcpServers"]["fisheries-data"]["command"], str(server.resolve()))
            self.assertFalse((Path(directory) / ".env").exists())
            self.assertIn("Regenerated MCP configuration", output.getvalue())

    def test_failed_package_install_does_not_report_success_or_write_setup_files(self):
        with tempfile.TemporaryDirectory() as directory:
            project, _ = self.make_project(directory)
            output, errors = io.StringIO(), io.StringIO()
            with (
                patch.object(installer, "__file__", str(project / "install.py")),
                patch.object(
                    installer.subprocess,
                    "run",
                    side_effect=subprocess.CalledProcessError(1, "pip"),
                ),
                redirect_stdout(output),
                redirect_stderr(errors),
            ):
                self.assertEqual(installer.main(), 1)

            self.assertFalse((project / ".env").exists())
            self.assertFalse((project / "mcp-config.json").exists())
            self.assertNotIn("Installation complete", output.getvalue())
            self.assertIn("Setup failed", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
