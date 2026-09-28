"""Install the local server and prepare credentials and MCP configuration."""

import json
import os
from pathlib import Path
import subprocess
import sys
import venv


def main() -> int:
    if sys.version_info < (3, 11):
        print("Python 3.11 or newer is required.", file=sys.stderr)
        return 1

    project = Path(__file__).resolve().parent
    environment = project / ".venv"
    scripts = environment / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    server = scripts / ("fisheries-data-mcp.exe" if os.name == "nt" else "fisheries-data-mcp")

    try:
        if not environment.exists():
            print("Creating the Python environment...", flush=True)
            venv.EnvBuilder(with_pip=True).create(environment)
        if not python.is_file():
            raise RuntimeError(f"The existing environment has no Python executable: {python}")

        print("Installing or updating Fisheries Data MCP...", flush=True)
        subprocess.run(
            [str(python), "-m", "pip", "install", "--upgrade", str(project)],
            cwd=project,
            check=True,
        )
        if not server.is_file():
            raise RuntimeError(f"The installed server executable was not found: {server}")

        credentials = project / ".env"
        template = (project / ".env.example").read_bytes()
        try:
            with credentials.open("xb") as destination:
                destination.write(template)
            print(f"Created credentials template: {credentials}")
        except FileExistsError:
            print(f"Kept your existing credentials file: {credentials}")

        config = project / "mcp-config.json"
        config_existed = config.exists()
        config.write_text(
            json.dumps(
                {"mcpServers": {"fisheries-data": {"command": str(server)}}},
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        print(f"{'Regenerated' if config_existed else 'Created'} MCP configuration: {config}")
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Setup failed: {error}", file=sys.stderr)
        return 1

    print("\nInstallation complete.")
    print(f"1. Optional: open {credentials} in a text editor and fill in the credentials you need.")
    print("   FishStat does not require credentials. Leave unused fields blank.")
    print("   UN Comtrade downloads require your own free API subscription key in UN_COMTRADE_API_KEY.")
    print(f"2. Import {config} into a compatible MCP client, or copy its fisheries-data entry")
    print("   into the client's mcpServers configuration. For other clients, register this command:")
    print(f"   {server}")
    print("3. Restart your AI client and enable the Fisheries Data MCP tools.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
