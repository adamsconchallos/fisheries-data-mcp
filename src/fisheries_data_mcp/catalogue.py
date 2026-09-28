"""Source-backed dataset discovery, independent of credentials or downloads."""

import json
import re
import unicodedata
from importlib.resources import files


PROVIDERS = ("fishstat", "barentswatch", "copernicus_marine")
CATALOGUE_SCOPE = (
    "Reviewed inventory of current FAO FishStatJ collections and BarentsWatch data services; "
    "Copernicus has a live catalogue through search_copernicus_datasets. "
    "Each entry records its documentation date and source references. "
    "Catalogue knowledge is broader than the server's implemented download tools."
)
SEARCH_NOTE = (
    "Matches identify potentially relevant documented datasets, not confirmed observations for your selection. "
    "Use describe_data_dataset to check variables, units, periods, resolution and limitations. "
    "A catalogue_only entry cannot be downloaded through this MCP; label it as an external/manual route. "
    "No match means no match in this reviewed catalogue, not proof that data do not exist."
)
_STOP_WORDS = set(
    "i want need to study research analyse analyze find data dataset datasets about the of and in on "
    "for by with a an me my what which are available from this that our please "
    "quiero necesito investigar analizar buscar busca datos sobre de del la las el los y en por para "
    "con un una que cuales hay disponibles al como este esta favor".split()
)


def _terms(value: str) -> set[str]:
    folded = "".join(
        char for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char)
    )
    return {word for word in re.findall(r"[^\W_]+", folded) if len(word) >= 2 and word not in _STOP_WORDS}


def _load_entries() -> list[dict]:
    entries = []
    for provider in PROVIDERS:
        resource = files("fisheries_data_mcp").joinpath("catalogues", f"{provider}.json")
        for entry in json.loads(resource.read_text(encoding="utf-8")):
            if entry["provider"] != provider:
                raise ValueError(f"Catalogue provider mismatch: {entry['id']}")
            entry["availability"] = "downloadable" if entry["download_tools"] else "catalogue_only"
            entry["availability_note"] = (
                "This MCP has the listed download tools. Access still depends on credentials, permissions "
                "and the requested selection; not every provider field is necessarily exposed."
                if entry["download_tools"] else
                "This MCP can describe this collection but has no direct download tool for it. "
                "Use the linked provider route or add a connector."
            )
            if entry.get("related_access"):
                entry["availability_note"] += (
                    " A connected related dataset supplies a limited alternative; see related_access "
                    "for its exact tool, selection and scope."
                )
            entries.append(entry)
    if len({entry["id"] for entry in entries}) != len(entries):
        raise ValueError("Duplicate dataset IDs in the packaged catalogue")
    return entries


def _select(provider: str) -> list[dict]:
    if provider not in ("all", *PROVIDERS):
        raise ValueError(f"provider must be all or one of {', '.join(PROVIDERS)}")
    return [entry for entry in _load_entries() if provider == "all" or entry["provider"] == provider]


def _summary(entry: dict) -> dict:
    keys = ("id", "provider", "title", "description", "coverage", "availability",
            "availability_note", "download_tools", "verified_on")
    summary = {key: entry[key] for key in keys}
    if entry.get("related_access"):
        summary["related_access"] = entry["related_access"]
    return summary


def list_datasets(provider: str = "all") -> dict:
    """List documented datasets and distinguish catalogue knowledge from download capability."""
    entries = _select(provider)
    return {
        "provider": provider,
        "count": len(entries),
        "catalogue_scope": CATALOGUE_SCOPE,
        "datasets": [_summary(entry) for entry in entries],
    }


def describe_data_dataset(dataset_id: str) -> dict:
    """Return source-backed variables, coverage, access and limitations for one dataset."""
    for entry in _load_entries():
        if entry["id"] == dataset_id:
            return entry
    raise ValueError("Unknown dataset_id. Use list_datasets or search_data_catalogue to find an exact ID.")


def search_data_catalogue(query: str, provider: str = "all", limit: int = 10) -> dict:
    """Search reviewed English/Spanish metadata; the client interprets the research question."""
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError("limit must be an integer between 1 and 50")
    query_terms = _terms(query)
    if not query_terms:
        raise ValueError("Give a research topic or variable; use list_datasets for the full inventory.")
    results = []
    matched_anywhere = set()
    for entry in _select(provider):
        # Exclude limitations: a statement that a variable is unavailable is not positive coverage.
        topic_terms = _terms(" ".join(entry["topics"]))
        variable_terms = _terms(" ".join(
            variable["name"] + " " + variable.get("description", "") for variable in entry["variables"]
        ))
        other_terms = _terms(" ".join((
            entry["title"], entry["description"], " ".join(entry["dimensions"]),
            json.dumps(entry["coverage"], ensure_ascii=False),
        )))
        matches = query_terms & (topic_terms | variable_terms | other_terms)
        if not matches:
            continue
        matched_anywhere.update(matches)
        score = (4 * len(query_terms & topic_terms) + 2 * len(query_terms & variable_terms)
                 + len(query_terms & other_terms))
        results.append((score, {**_summary(entry), "matched_terms": sorted(matches)}))
    results.sort(key=lambda result: (-result[0], result[1]["id"]))
    return {
        "query": query,
        "provider": provider,
        "total_matches": len(results),
        "results": [entry for _, entry in results[:limit]],
        "query_terms_without_matches": sorted(query_terms - matched_anywhere),
        "note": SEARCH_NOTE,
    }
