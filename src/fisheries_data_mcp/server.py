"""Read-only data queries exposed to MCP clients over local stdio."""

import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from .settings import load_local_credentials

load_local_credentials()  # Copernicus Marine reads environment credentials during import.
from . import barentswatch, catalogue, copernicus, fishstat


mcp = MCPServer(
    "Fisheries Data",
    instructions=(
        "Find, describe and download fisheries and marine datasets. "
        "For research questions, use search_data_catalogue then describe_data_dataset to propose relevant data. "
        "Label catalogue_only entries as external/manual routes that this MCP cannot download. "
        "Label suggestions beyond the reviewed catalogue as external sources whose access through this MCP is unverified. "
        "Search matches are candidate datasets, not proof of observations: resolve species, countries, "
        "localities, periods and variables with the source tools before claiming availability. "
        "Clarify ambiguous species, countries, periods, variables or table structure before downloading. "
        "Explain the delivered fields, units, selection, missing values and source citation. "
        "FishStat country totals are documented query aggregations. "
        "This server supplies data for subsequent analysis; it does not fit models, test hypotheses, "
        "interpret scientific results or join data sources. State when a requested dataset or table "
        "structure is unsupported instead of inventing data. "
        "The catalogue documents more FishStat collections and BarentsWatch services than the "
        "implemented download tools. Read access requirements and limitations before recommending a route. "
        "Use the live Copernicus catalogue for its dataset-level coverage. "
        "Preserve provider reporting flags: an unreported observation must not be presented as a measured zero."
    ),
)


def _output_dir() -> Path:
    configured = os.environ.get("FISHERIES_MCP_OUTPUT_DIR")
    return Path(configured).expanduser() if configured else Path.home() / "fisheries-data-mcp" / "exports"


def _export_rows(rows: list[dict], metadata: dict, label: str) -> dict:
    if not rows:
        return {}
    directory = _output_dir()
    directory.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:60] or "query"
    stem = f"{slug}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
    csv_path = directory / f"{stem}.csv"
    columns = list(dict.fromkeys(key for row in rows for key in row))
    table_structure = {
        **metadata.get("table_structure", {}),
        "columns": columns,
        "row_count": len(rows),
        "csv_encoding": "UTF-8 with BOM",
        "nested_values": "Lists and objects are JSON-encoded within CSV cells.",
    }
    metadata = {**metadata, "table_structure": table_structure}
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(
            {
                key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                for key, value in row.items()
            }
            for row in rows
        )
    metadata_path = directory / f"{stem}.metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return {
        "csv_path": str(csv_path), "metadata_path": str(metadata_path),
        "table_structure": table_structure,
    }


def _tool_error(exc: Exception) -> ToolError:
    return exc if isinstance(exc, ToolError) else ToolError(str(exc))


@mcp.tool()
def list_data_sources() -> dict:
    """List available sources, coverage and output structure before choosing a dataset to download."""
    return {
        "discovery_tools": ["list_datasets", "search_data_catalogue", "describe_data_dataset"],
        "catalogue_scope": catalogue.CATALOGUE_SCOPE,
        "sources": [
            {
                "id": "fishstat",
                "name": "FAO FishStat Global Production",
                "covers": "Annual aquatic capture and aquaculture production by country, species and area; 1950-2024 in release 2026.1.0.",
                "tools": ["search_fishstat_species", "fishstat_production_by_country"],
                "url": "https://www.fao.org/fishery/static/Data/",
                "table_structure": fishstat.TABLE_STRUCTURE,
                "limitations": "This download tool supplies quantities only. Use fishstat_aquaculture_records for aquaculture monetary production values. Use list_datasets(provider='fishstat') for other documented collections and their download status.",
            },
            {
                "id": "fishstat_aquaculture",
                "name": "FAO FishStat Global Aquaculture Production",
                "covers": "Annual aquaculture quantity and monetary production value by country, species, FAO area and culture environment, release 2026.1.0.",
                "coverage": fishstat.AQUACULTURE_COVERAGE,
                "variables": {
                    "Q_tlw": "Tonnes live weight for animals; tonnes wet weight for plants.",
                    "V_USD_1000": "Nominal production value in thousands of USD; not an export value or a price per tonne.",
                },
                "tools": ["search_fishstat_countries", "search_fishstat_species", "fishstat_aquaculture_records"],
                "url": fishstat.AQUACULTURE_SOURCE_URL,
                "table_structure": fishstat.AQUACULTURE_TABLE_STRUCTURE,
                "limitations": "Actual country/species coverage must be checked in the returned records. Quantity and value are separate rows; missing observations are not filled. No capture-fisheries monetary values.",
            },
            {
                "id": "barentswatch",
                "name": "BarentsWatch Fish Health",
                "covers": "Find Norwegian aquaculture localities; retrieve lice stages, sea temperature, treatments, disease cases, escapes, capacity and weekly site snapshots.",
                "tools": ["barentswatch_search_localities", "barentswatch_get_locality_data", "barentswatch_get_locality_details", "barentswatch_lice_by_locality"],
                "url": "https://developer.barentswatch.no/docs/fishhealth/",
                "output_structure": "Site-year datasets export CSV plus metadata describing fields, units, reporting flags and any nested JSON cells. Weekly site details export nested JSON. Each query returns its specific structure.",
                "catalogue_note": "Use list_datasets(provider='barentswatch') to discover other Fish Health datasets and BarentsWatch services, including those without an implemented download tool.",
            },
            {
                "id": "copernicus_marine",
                "name": "Copernicus Marine Service",
                "covers": "Ocean observations, reanalyses and forecasts by variable, area, time and depth.",
                "tools": ["search_copernicus_datasets", "describe_copernicus_dataset", "subset_copernicus_dataset"],
                "url": "https://data.marine.copernicus.eu/",
                "output_structure": "NetCDF or Zarr subset; CSV when supported by the installed Toolbox. Variables, units and dimensions depend on the dataset: call describe_copernicus_dataset before downloading. The server does not calculate spatial or temporal averages.",
            },
        ],
        "scope_note": "Search, describe and download data with source metadata. The server prepares source-specific selections and documented country totals; statistical analysis, scientific interpretation and joins between sources are outside its scope.",
    }


@mcp.tool()
def list_datasets(provider: str = "all") -> dict:
    """List the reviewed dataset inventory and which datasets have MCP download tools. Providers: all, fishstat, barentswatch, copernicus_marine. Includes catalogue-only datasets with external/manual access routes."""
    try:
        return catalogue.list_datasets(provider)
    except Exception as exc:
        raise _tool_error(exc) from exc


@mcp.tool()
def search_data_catalogue(query: str, provider: str = "all", limit: int = 10) -> dict:
    """Find candidate datasets from English or Spanish research topics (production/value, trade, employment, sea lice, temperature, disease). Search reviewed metadata without credentials or downloading data. Results distinguish downloadable from catalogue_only and surface unmatched terms. Verify actual coverage before recommending a download; use live source searches as needed."""
    try:
        return catalogue.search_data_catalogue(query, provider, limit)
    except Exception as exc:
        raise _tool_error(exc) from exc


@mcp.tool()
def describe_data_dataset(dataset_id: str) -> dict:
    """Describe one catalogue dataset's variables, units, dimensions, coverage, access requirements, available tools, limitations and primary references. Use the exact ID returned by list_datasets or search_data_catalogue."""
    try:
        return catalogue.describe_data_dataset(dataset_id)
    except Exception as exc:
        raise _tool_error(exc) from exc


@mcp.tool()
def search_fishstat_species(query: str, limit: int = 20) -> dict:
    """Find FishStat aquatic species or species groups by name or code, including oysters/ostras."""
    try:
        return fishstat.search_species(query, limit)
    except Exception as exc:
        raise _tool_error(exc) from exc


@mcp.tool()
def search_fishstat_countries(query: str, limit: int = 20) -> dict:
    """Find exact FAO country codes by English, Spanish or French name or UN/ISO code before selecting aquaculture records."""
    try:
        return fishstat.search_countries(query, limit)
    except Exception as exc:
        raise _tool_error(exc) from exc


@mcp.tool()
def fishstat_aquaculture_records(
    query: str, start_year: int, end_year: int, country_code: str = "",
    species_code: str = "", measure: str = "both",
) -> dict:
    """Download original FAO aquaculture records: quantity (1950-2024), value (1984-2024), or both. Values are nominal thousands of USD. Resolve country_code with search_fishstat_countries; empty selects all countries. Optionally select exact ASFIS species_code. Preserve country/species/area/environment/year/measure and quality flags; no aggregation or joins. Returns complete CSV and metadata paths and up to 20 preview rows."""
    try:
        result = fishstat.aquaculture_records(query, start_year, end_year, country_code, species_code, measure)
        rows = result.pop("rows")
        result.update(_export_rows(rows, result, f"fishstat-aquaculture-{country_code or 'all'}-{start_year}-{end_year}"))
        result["row_count"] = len(rows)
        result["rows_preview"] = rows[:20]
        return result
    except Exception as exc:
        raise _tool_error(exc) from exc


@mcp.tool()
def fishstat_production_by_country(
    query: str, year: int, source: str = "all", species_code: str = ""
) -> dict:
    """Download a CSV of annual production tonnes grouped by FAO country/area for an aquatic species or group. Sums selected observations across species and areas. Source: all, capture or aquaculture. Optionally set an exact ASFIS species_code. Returns table structure, weight basis, quality flags and provenance."""
    try:
        result = fishstat.production_by_country(query, year, source, species_code or None)
        result.update(_export_rows(result.get("rows", []), {k: v for k, v in result.items() if k != "rows"}, f"fishstat-{query}-{year}"))
        return result
    except Exception as exc:
        raise _tool_error(exc) from exc


@mcp.tool()
def barentswatch_search_localities(query: str = "", limit: int = 50) -> dict:
    """Find current Norwegian aquaculture site IDs by locality name or number. Returns localityNo, name and municipality. Query does not search municipality names. Limit 1-1000; narrow a truncated search. A directory match does not prove that the site reported lice or operated in a historical year."""
    try:
        return barentswatch.search_localities(query, limit)
    except Exception as exc:
        raise _tool_error(exc) from exc


@mcp.tool()
def barentswatch_get_locality_data(locality_id: int, year: int, dataset: str = "lice_stages") -> dict:
    """Download one site-year as CSV with metadata. Datasets: lice_stages, sea_temperature, treatments, diseases, escapes, capacity. Preserves provider fields, reporting flags and nested event lists. Disease cases can span years; capacity is an administrative limit, not production. Does not compute annual indicators. Returns all rows in the file and up to 20 preview rows."""
    try:
        result = barentswatch.locality_data(locality_id, year, dataset)
        rows = result.pop("rows")
        result.update(_export_rows(rows, result, f"barentswatch-{dataset}-{locality_id}-{year}"))
        result["row_count"] = len(rows)
        result["rows_preview"] = rows[:20]
        return result
    except Exception as exc:
        raise _tool_error(exc) from exc


@mcp.tool()
def barentswatch_get_locality_details(locality_id: int, year: int, week: int) -> dict:
    """Download a site's nested JSON snapshot for an ISO year/week: licenses and permitted species/capacity, location, fish-health reports and reporting flags. License species are not proof of actual stocked species. Returns the source snapshot, JSON file and provenance; no flattening or joins."""
    try:
        result = barentswatch.locality_details(locality_id, year, week)
        directory = _output_dir()
        directory.mkdir(parents=True, exist_ok=True)
        stem = f"barentswatch-site-{locality_id}-{year}-{week}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
        json_path = directory / f"{stem}.json"
        metadata_path = directory / f"{stem}.metadata.json"
        json_path.write_text(json.dumps(result["data"], ensure_ascii=False, indent=2), encoding="utf-8")
        metadata = {key: value for key, value in result.items() if key != "data"}
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return {**result, "json_path": str(json_path), "metadata_path": str(metadata_path)}
    except Exception as exc:
        raise _tool_error(exc) from exc


@mcp.tool()
def barentswatch_lice_by_locality(locality_id: int, year: int) -> dict:
    """Download provider-reported weekly mean adult female salmon lice for a locality/year. For new research queries, prefer barentswatch_get_locality_data(dataset='lice_stages'), which also includes reporting flags and other lice stages. This older endpoint cannot distinguish every unreported zero."""
    try:
        result = barentswatch.lice_by_locality(locality_id, year)
        result.update(_export_rows(result.get("rows", []), {k: v for k, v in result.items() if k != "rows"}, f"barentswatch-lice-{locality_id}-{year}"))
        return result
    except Exception as exc:
        raise _tool_error(exc) from exc


@mcp.tool()
def search_copernicus_datasets(query: str, limit: int = 10) -> dict:
    """Search live Copernicus Marine catalogue for ocean variables and dataset IDs."""
    try:
        return copernicus.search_datasets(query, limit)
    except Exception as exc:
        raise _tool_error(exc) from exc


@mcp.tool()
def describe_copernicus_dataset(dataset_id: str) -> dict:
    """Describe a Copernicus Marine dataset's variables, units, coverage, version and product DOI before choosing a subset."""
    try:
        return copernicus.describe_dataset(dataset_id)
    except Exception as exc:
        raise _tool_error(exc) from exc


@mcp.tool()
def subset_copernicus_dataset(
    dataset_id: str,
    variable: str,
    west: float,
    east: float,
    south: float,
    north: float,
    start: str,
    end: str,
    file_format: str = "netcdf",
) -> dict:
    """Download a bounded Copernicus Marine subset by dataset, variable, bounding box and dates. Returns a local NetCDF, Zarr or CSV file with provenance."""
    try:
        return copernicus.subset_dataset(
            dataset_id, variable, west, east, south, north, start, end, _output_dir(), file_format
        )
    except Exception as exc:
        raise _tool_error(exc) from exc


def main() -> None:
    """Start the local stdio MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
