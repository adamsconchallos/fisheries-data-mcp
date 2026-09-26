"""Read-only access to BarentsWatch Fish Health data.

API and authentication: https://developer.barentswatch.no/docs/tutorial/
Data terms: https://www.barentswatch.no/en/articles/api-terms-and-conditions/
"""

import json
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


TOKEN_URL = "https://id.barentswatch.no/connect/token"
API_BASE = "https://www.barentswatch.no/bwapi"
TIMEOUT_SECONDS = 20


class BarentsWatchError(RuntimeError):
    """An authenticated BarentsWatch request could not be completed."""


def _read_json(request: Request, *, purpose: str) -> object:
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise BarentsWatchError(
            f"BarentsWatch {purpose} failed with HTTP {exc.code}."
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise BarentsWatchError(f"BarentsWatch {purpose} could not connect.") from exc
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BarentsWatchError(f"BarentsWatch {purpose} returned invalid JSON.") from exc


def _access_token() -> str:
    client_id = os.environ.get("BARENTSWATCH_CLIENT_ID")
    client_secret = os.environ.get("BARENTSWATCH_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise BarentsWatchError(
            "Set BARENTSWATCH_CLIENT_ID and BARENTSWATCH_CLIENT_SECRET "
            "for a registered BarentsWatch API client."
        )

    form = urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "api",
        }
    ).encode("ascii")
    request = Request(
        TOKEN_URL,
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    payload = _read_json(request, purpose="authentication")
    if not isinstance(payload, dict) or not isinstance(payload.get("access_token"), str):
        raise BarentsWatchError("BarentsWatch authentication returned no access token.")
    return payload["access_token"]


def lice_by_locality(locality_id: int, year: int) -> dict:
    """Return weekly average adult female salmon lice per fish at one locality.

    Weeks absent from the upstream response are not filled. Null values and
    reported zeroes are preserved as supplied by BarentsWatch.
    """
    if type(locality_id) is not int or locality_id <= 0:
        raise ValueError("locality_id must be a positive integer")
    if type(year) is not int or year <= 0:
        raise ValueError("year must be a positive integer")

    url = (
        f"{API_BASE}/v1/geodata/fishhealth/locality/"
        f"{locality_id}/avgfemalelice/{year}"
    )
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {_access_token()}",
        },
        method="GET",
    )
    payload = _read_json(request, purpose="Fish Health query")
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("data"), list)
        or not all(isinstance(item, dict) for item in payload["data"])
    ):
        raise BarentsWatchError("BarentsWatch Fish Health returned an unexpected response.")

    return {
        "source": "BarentsWatch Fish Health API",
        "source_url": url,
        "documentation_url": "https://developer.barentswatch.no/docs/tutorial/",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "attribution": "Data delivered by BarentsWatch; lice data provided by Mattilsynet",
        "license": "NLOD",
        "locality_id": locality_id,
        "year": year,
        "indicator": payload.get("type", "avgAdultFemaleLice"),
        "unit": "adult female lice per fish",
        "rows": [
            {"locality_id": locality_id, "year": year, **item}
            for item in payload["data"]
        ],
        "notes": [
            "Raw farm reports may contain errors and have not been manually corrected before publication.",
            "Missing weeks are omitted; a zero in lice exports can mean either a reported zero or an empty field.",
        ],
    }
