"""Read-only access to BarentsWatch Fish Health data.

API and authentication: https://developer.barentswatch.no/docs/tutorial/
Data terms: https://www.barentswatch.no/en/articles/api-terms-and-conditions/
"""

import json
import os
from datetime import date, datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


TOKEN_URL = "https://id.barentswatch.no/connect/token"
API_BASE = "https://www.barentswatch.no/bwapi"
TIMEOUT_SECONDS = 20
DOCUMENTATION_URL = "https://developer.barentswatch.no/docs/fishhealth/"

# Only documented, live-verified read endpoints are exposed by locality_data.
LOCALITY_DATASETS = {
    "lice_stages": ("v1", "liceTypeDistribution", "lice per fish"),
    "sea_temperature": ("v1", "seatemperature", "degrees Celsius"),
    "treatments": ("v1", "liceTreatments", "provider treatment records"),
    "diseases": ("v3", "disease", "provider disease case records"),
    "escapes": ("v1", "escape", "provider escape incident records"),
    "capacity": ("v1", "capacity", "provider capacity unit; inspect locality details"),
}

_DATASET_COLUMNS = {
    "lice_stages": {
        "avgAdultFemaleLice": "Provider weekly mean adult female lice per fish.",
        "avgMobileLice": "Provider weekly mean mobile lice per fish.",
        "avgStationaryLice": "Provider weekly mean stationary lice per fish.",
        "hasReportedLice": "Whether lice were reported. False means accompanying zeroes are not evidence of zero lice.",
    },
    "sea_temperature": {
        "seaTemperature": "Reported water temperature at or near the site, degrees Celsius.",
        "hasReported": "Whether temperature was reported for this week.",
    },
    "treatments": {
        "medicinalTreatments": "Provider medicinal treatment details, retained as a nested list.",
        "nonMedicinalTreatments": "Provider non-medicinal treatment details, retained as a nested list.",
        "combinationTreatments": "Provider combination treatment details, retained as a nested list.",
        "cleanerFishTreatments": "Historical cleaner-fish treatments; not included after week 16 of 2018.",
        "mechanicalRemoval": "Provider flag for mechanical lice removal.",
        "version": "Provider treatment record version; fields can vary across versions.",
    },
    "diseases": {
        "name": "Disease name in the provider's original language.",
        "subType": "Provider disease subtype, if present.",
        "status": "Provider case status, such as DIAGNOSED.",
        "suspicionDate": "Date a case was suspected; may precede the requested year.",
        "diagnosisDate": "Case diagnosis date, if present.",
        "emptiedDate": "Date the site was emptied, if present.",
        "closureDate": "Case closure date, if present.",
    },
    "escapes": {"escapes": "Nested list of escape incident records for the week."},
    "capacity": {"capacity": "Permitted site capacity, not realized biomass or annual production. The endpoint omits a unit; inspect locality details."},
}

TABLE_STRUCTURE = {
    "row_definition": "One provider-reported week for the requested aquaculture locality and year.",
    "column_descriptions": {
        "locality_id": "BarentsWatch aquaculture locality identifier.",
        "year": "Requested reporting year.",
        "week": "Reporting week as supplied by BarentsWatch.",
        "value": "Provider-reported weekly mean adult female lice per fish.",
    },
    "preparation": "Add the requested locality ID and year to the provider's weekly records. Preserve provider fields and values; no averages are computed by this server.",
    "missing_values": "Absent weeks are omitted. Null values become empty CSV cells; supplied zeroes remain zero. Consult the source notes before interpreting zeroes.",
    "additional_columns": "Extra fields returned by the provider are retained with their original names.",
}


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


def _query(path: str) -> tuple[str, object]:
    url = f"{API_BASE}/{path}"
    request = Request(url, headers={
        "Accept": "application/json", "Authorization": f"Bearer {_access_token()}",
    }, method="GET")
    return url, _read_json(request, purpose="Fish Health query")


def _provenance(url: str) -> dict:
    return {
        "source": "BarentsWatch Fish Health API",
        "source_url": url,
        "documentation_url": DOCUMENTATION_URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "attribution": "Data delivered by BarentsWatch from the Norwegian Food Safety Authority, Directorate of Fisheries and Veterinary Institute; ownership varies by field.",
        "license": "NLOD",
    }


def _validate_locality_year(locality_id: int, year: int) -> None:
    if type(locality_id) is not int or locality_id <= 0:
        raise ValueError("locality_id must be a positive integer")
    if type(year) is not int or not 2012 <= year <= datetime.now(timezone.utc).year:
        raise ValueError("year must be between 2012 and the current year; coverage varies by dataset")


def search_localities(query: str = "", limit: int = 50) -> dict:
    """Find current aquaculture site IDs by site name or number, not municipality.

    Results can include non-salmonid sites. A matching site does not establish
    that it reported lice or was operating in a particular historical year.
    """
    if not isinstance(query, str) or len(query) > 500:
        raise ValueError("query must be a string of at most 500 characters")
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("limit must be an integer between 1 and 1000")
    url, payload = _query("v1/geodata/fishhealth/localities?" + urlencode({"query": query}))
    if not isinstance(payload, list) or not all(
        isinstance(item, dict) and type(item.get("localityNo")) is int
        for item in payload
    ):
        raise BarentsWatchError("BarentsWatch locality search returned an unexpected response.")
    return {
        **_provenance(url), "query": query, "total_matches": len(payload),
        "returned_count": min(limit, len(payload)), "truncated": len(payload) > limit,
        "rows": payload[:limit],
        "notes": ["Use localityNo as locality_id in data requests. Search matches names or IDs, not municipality names.",
                  "The current directory is not a census of operating salmon farms in a historical year. Narrow the query if results are truncated."],
    }


def locality_data(locality_id: int, year: int, dataset: str = "lice_stages") -> dict:
    """Fetch one site-year of source records without annual aggregation or joins."""
    _validate_locality_year(locality_id, year)
    if not isinstance(dataset, str) or dataset not in LOCALITY_DATASETS:
        raise ValueError("dataset must be one of: " + ", ".join(LOCALITY_DATASETS))
    version, endpoint, unit = LOCALITY_DATASETS[dataset]
    url, payload = _query(f"{version}/geodata/fishhealth/locality/{locality_id}/{endpoint}/{year}")
    provider_metadata = {}
    if dataset == "diseases":
        records = payload
    elif dataset == "capacity":
        if not isinstance(payload, dict) or not all(
            isinstance(k, str) and k.isdigit() and 1 <= int(k) <= 53 and isinstance(v, dict)
            for k, v in payload.items()
        ):
            raise BarentsWatchError("BarentsWatch capacity returned an unexpected response.")
        records = [{"week": int(week), **item} for week, item in payload.items()]
    else:
        records = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(payload, dict):
            provider_metadata = {key: value for key, value in payload.items() if key != "data"}
            if payload.get("localityNo") != locality_id or payload.get("year") != year:
                raise BarentsWatchError("BarentsWatch returned a different locality or year than requested.")
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        raise BarentsWatchError("BarentsWatch locality data returned an unexpected response.")
    row_definition = (
        "One disease case returned for the requested site and year; dates can span years."
        if dataset == "diseases" else
        "One provider-returned week for the requested site and year; event weeks can contain nested lists."
    )
    notes = [
        "Source records may contain reporting errors and are not manually corrected before API publication.",
        "No annual mean, total, growth rate, or join with another source is computed by this server.",
    ]
    if dataset == "lice_stages":
        notes.append("When hasReportedLice is false, zero-valued lice fields must not be interpreted as a reported zero. Original values and reporting flags are preserved.")
    if dataset == "sea_temperature":
        notes.append("Check hasReported. Null temperatures denote no supplied measurement, including future weeks.")
    if dataset == "treatments":
        notes.append("Cleaner-fish data are not included after week 16 of 2018; an empty list does not demonstrate no cleaner-fish use.")
    if dataset == "diseases":
        notes.append("A case may have begun in an earlier year. Do not count every returned case as a new diagnosis in the requested year.")
    if dataset == "capacity":
        notes.append("Capacity is an administrative limit, not actual biomass or production. This endpoint has no unit field; inspect the locality snapshot before interpreting it.")
    return {
        **_provenance(url), "locality_id": locality_id, "year": year,
        "dataset": dataset, "unit": unit, "provider_metadata": provider_metadata,
        "table_structure": {
            "row_definition": row_definition,
            "column_descriptions": {
                "locality_id": "Requested aquaculture site identifier.",
                "year": "Requested ISO reporting year; not necessarily the case start year.",
                **({"week": "Reporting week as supplied by the provider."} if dataset != "diseases" else {}),
                **_DATASET_COLUMNS[dataset],
            },
            "preparation": "Add requested site ID and year; for capacity, turn week keys into a week column. Preserve all source fields and nested records. No averages are calculated.",
            "missing_values": "Preserve nulls, zeroes and reporting flags. Do not fill absent rows. An empty result means the endpoint supplied no records for this request.",
            "additional_columns": "Extra provider fields are retained with their original names. Nested lists and objects require JSON encoding in CSV.",
        },
        "rows": [{**item, "locality_id": locality_id, "year": year} for item in records],
        "notes": notes,
    }


def locality_details(locality_id: int, year: int, week: int) -> dict:
    """Return the provider's nested site snapshot for a valid ISO week.

    Includes licenses/species, permitted capacity and unit, coordinates,
    disease cases, escapes, lice-report flags, temperature and treatments.
    Species on licenses are authorized species, not proof of fish present.
    """
    _validate_locality_year(locality_id, year)
    if type(week) is not int:
        raise ValueError("week must be a valid integer ISO week for the requested year")
    try:
        date.fromisocalendar(year, week, 1)
    except ValueError as exc:
        raise ValueError("week must be a valid integer ISO week for the requested year") from exc
    url, payload = _query(f"v2/geodata/fishhealth/locality/{locality_id}/{year}/{week}")
    if not isinstance(payload, dict) or not isinstance(payload.get("locality"), dict) or payload["locality"].get("no") != locality_id:
        raise BarentsWatchError("BarentsWatch locality details returned an unexpected response.")
    return {
        **_provenance(url), "locality_id": locality_id, "year": year, "week": week,
        "data": payload,
        "structure": "A nested JSON site snapshot. Licenses, organizations, diseases and treatments contain arrays. geometry uses GeoJSON longitude, latitude coordinates.",
        "notes": [
            "License species and permitted capacity do not establish realized species production or actual biomass.",
            "Check liceReport.hasReported and isFallow before interpreting lice values.",
            "Names and categories are retained in the source language; no automatic category translation is applied.",
            "Cleaner-fish data are not included after week 16 of 2018.",
        ],
    }


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
        "table_structure": TABLE_STRUCTURE,
        "rows": [
            {"locality_id": locality_id, "year": year, **item}
            for item in payload["data"]
        ],
        "notes": [
            "Raw farm reports may contain errors and have not been manually corrected before publication.",
            "Missing weeks are omitted; a zero in lice exports can mean either a reported zero or an empty field.",
        ],
    }
