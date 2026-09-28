"""Load optional local data-source credentials before provider imports."""

import os
import sys
from pathlib import Path

from dotenv import dotenv_values


_CREDENTIAL_KEYS = frozenset(
    {
        "BARENTSWATCH_CLIENT_ID",
        "BARENTSWATCH_CLIENT_SECRET",
        "COPERNICUSMARINE_SERVICE_USERNAME",
        "COPERNICUSMARINE_SERVICE_PASSWORD",
    }
)


def load_local_credentials() -> None:
    """Read the project .env independently of the MCP client's working directory."""
    configured = os.environ.get("FISHERIES_MCP_ENV_FILE")
    if configured:
        env_file = Path(configured).expanduser()
        if not env_file.is_absolute():
            raise ValueError("FISHERIES_MCP_ENV_FILE must be an absolute path")
        if not env_file.is_file():
            raise FileNotFoundError(f"Credential file not found: {env_file}")
    else:
        venv = Path(sys.prefix)
        if venv.name != ".venv":
            return
        env_file = venv.parent / ".env"
        if not env_file.is_file():
            return

    for name, value in dotenv_values(env_file, interpolate=False).items():
        if name in _CREDENTIAL_KEYS and value and name not in os.environ:
            os.environ[name] = value
