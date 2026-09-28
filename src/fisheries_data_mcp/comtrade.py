"""UN Comtrade goods trade queries using the official API and reference lists."""

import json
import os
import re
import unicodedata
from datetime import date
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_BASE = "https://comtradeapi.un.org"
REFERENCE_FILES = {
    "reporter": "Reporters.json",
    "partner": "partnerAreas.json",
    "flow": "tradeRegimes.json",
}
CLASSIFICATIONS = {"HS", "H0", "H1", "H2", "H3", "H4", "H5", "H6"}
TABLE_STRUCTURE = {
    "grain": "One original UN Comtrade goods record per period, reporter, partner, HS commodity, trade flow and any source dimensions retained by the API.",
    "value_units": {
        "primaryValue": "US dollars; valuation basis depends on the reported flow and country",
        "netWgt": "kilograms when reported",
        "grossWgt": "kilograms when reported",
        "qty": "unit given by qtyUnitAbbr in each record",
        "altQty": "unit given by altQtyUnitAbbr in each record",
    },
    "source_fields": "All fields returned by the UN Comtrade API are preserved, including reporting and estimation flags.",
}


def _get_json(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "fisheries-data-mcp/0.1"})
    try:
        with urlopen(request, timeout=60) as response:
            return json.load(response)
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise RuntimeError("UN Comtrade rejected the API key or access tier (HTTP 401/403).") from None
        if exc.code == 429:
            raise RuntimeError("UN Comtrade rate limit reached (HTTP 429); retry later.") from None
        raise RuntimeError(f"UN Comtrade request failed (HTTP {exc.code}); check the selected codes and period.") from None
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("Could not reach the UN Comtrade API; retry when the service is available.") from None
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("UN Comtrade returned an invalid JSON response.") from None


@lru_cache(maxsize=11)
def _reference(kind: str, classification: str) -> list[dict]:
    filename = f"{classification}.json" if kind == "commodity" else REFERENCE_FILES[kind]
    url = f"{API_BASE}/files/v1/app/reference/{filename}"
    payload = _get_json(url)
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise RuntimeError("UN Comtrade returned an unexpected reference-list format.")
    return payload["results"]


def _fold(value: object) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", str(value).casefold())
        if not unicodedata.combining(char)
    )


def search_reference(kind: str, query: str, classification: str = "HS", limit: int = 20) -> dict:
    """Resolve current Comtrade reporter, partner, HS commodity or trade-flow codes."""
    kind = kind.lower().strip()
    classification = classification.upper().strip()
    query = query.strip()
    if kind not in (*REFERENCE_FILES, "commodity"):
        raise ValueError("kind must be reporter, partner, commodity or flow")
    if classification not in CLASSIFICATIONS:
        raise ValueError("classification must be HS or H0-H6")
    if not query:
        raise ValueError("Give a name or code to search.")
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError("limit must be an integer between 1 and 50")

    terms = _fold(query)
    matches = [
        row for row in _reference(kind, classification)
        if terms in _fold(row.get("id", "")) or terms in _fold(row.get("text", ""))
        or (kind == "reporter" and terms in _fold(row.get("reporterCodeIsoAlpha3", "")))
    ]
    matches.sort(key=lambda row: (_fold(row.get("id")) != terms, _fold(row.get("text")) != terms, str(row.get("id"))))
    results = []
    for row in matches[:limit]:
        item = {"code": str(row["id"]), "description": row["text"]}
        if kind == "reporter":
            item["iso3"] = row.get("reporterCodeIsoAlpha3")
        if kind == "commodity":
            item["standard_unit"] = row.get("standardUnitAbbr")
        results.append(item)
    filename = f"{classification}.json" if kind == "commodity" else REFERENCE_FILES[kind]
    return {
        "kind": kind,
        "query": query,
        "classification": classification if kind == "commodity" else None,
        "total_matches": len(matches),
        "results": results,
        "reference_url": f"{API_BASE}/files/v1/app/reference/{filename}",
        "note": "A reference-code match does not establish observations for a reporter, period or product.",
    }


def trade_records(
    period: str,
    reporter_code: int,
    commodity_code: str,
    flow_code: str,
    partner_code: int = 0,
    frequency: str = "A",
    classification: str = "HS",
) -> dict:
    """Retrieve one bounded goods trade query without silently claiming completeness."""
    period = str(period).strip()
    commodity_code = commodity_code.upper().strip()
    flow_code = flow_code.upper().strip()
    frequency = frequency.upper().strip()
    classification = classification.upper().strip()
    if frequency not in ("A", "M"):
        raise ValueError("frequency must be A (annual) or M (monthly)")
    period_pattern = r"\d{4}" if frequency == "A" else r"\d{6}"
    if not re.fullmatch(period_pattern, period):
        raise ValueError("period must be YYYY for annual or YYYYMM for monthly data")
    if frequency == "M" and not 1 <= int(period[-2:]) <= 12:
        raise ValueError("period month must be 01-12")
    if type(reporter_code) is not int or reporter_code <= 0:
        raise ValueError("reporter_code must be a positive UN Comtrade reporter code")
    if type(partner_code) is not int or partner_code < 0:
        raise ValueError("partner_code must be a nonnegative UN Comtrade partner code; 0 means World")
    if not re.fullmatch(r"TOTAL|\d{2}(?:\d{2})?(?:\d{2})?", commodity_code):
        raise ValueError("commodity_code must be one HS code of 2, 4 or 6 digits, or TOTAL")
    if flow_code not in ("M", "X", "RM", "RX"):
        raise ValueError("flow_code must be M, X, RM or RX; use search_comtrade_reference for meanings")
    if classification not in CLASSIFICATIONS:
        raise ValueError("classification must be HS or H0-H6")

    api_key = os.environ.get("UN_COMTRADE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "UN_COMTRADE_API_KEY is required for UN Comtrade downloads. "
            "Add your free subscription key to the project's .env file and restart the MCP server."
        )
    max_records = 100_000
    params = {
        "period": period,
        "reporterCode": reporter_code,
        "partnerCode": partner_code,
        "cmdCode": commodity_code,
        "flowCode": flow_code,
        "breakdownMode": "classic",
        "maxRecords": max_records,
        "includeDesc": "true",
    }
    base_url = f"{API_BASE}/data/v1/get/C/{frequency}/{classification}"
    public_url = f"{base_url}?{urlencode(params)}"
    request_url = f"{public_url}&{urlencode({'subscription-key': api_key})}"
    payload = _get_json(request_url)
    rows = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("UN Comtrade returned an unexpected trade-data format.")
    provider_count = payload.get("count")
    possibly_truncated = len(rows) >= max_records or (
        type(provider_count) is int and provider_count > len(rows)
    )
    warnings = []
    if possibly_truncated:
        warnings.append(
            f"The query reached or exceeded the {max_records:,}-record limit; "
            "the exported rows may be incomplete. Narrow the product, partner or period selection."
        )
    if not rows:
        warnings.append("No observations returned for the selected codes and period.")
    return {
        "source": "UN Comtrade",
        "access_mode": "subscription_key",
        "selection": {"period": period, "reporter_code": reporter_code, "partner_code": partner_code,
                      "commodity_code": commodity_code, "flow_code": flow_code,
                      "frequency": frequency, "classification": classification},
        "source_url": public_url,
        "accessed_on": date.today().isoformat(),
        "citation": f"United Nations Statistics Division, UN Comtrade database, accessed {date.today().isoformat()}.",
        "provider_count": provider_count,
        "possibly_truncated": possibly_truncated,
        "table_structure": TABLE_STRUCTURE,
        "warnings": warnings,
        "rows": rows,
    }
