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
from . import barentswatch, copernicus, fishstat


mcp = MCPServer(
    "Fisheries Data",
    instructions=(
        "Find, describe and download fisheries and marine datasets. "
        "Use list_data_sources to check coverage and output structure. "
        "Clarify ambiguous species, countries, periods, variables or table structure before downloading. "
        "Explain the delivered fields, units, selection, missing values and source citation. "
        "FishStat country totals are documented query aggregations. "
        "This server supplies data for subsequent analysis; it does not fit models, test hypotheses, "
        "interpret scientific results or join data sources. State when a requested dataset or table "
        "structure is unsupported instead of inventing data."
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
        "sources": [
            {
                "id": "fishstat",
                "name": "FAO FishStat Global Production",
                "covers": "Annual aquatic capture and aquaculture production by country, species and area; 1950-2024 in release 2026.1.0.",
                "tools": ["search_fishstat_species", "fishstat_production_by_country"],
                "url": "https://www.fao.org/fishery/static/Data/",
                "table_structure": fishstat.TABLE_STRUCTURE,
            },
            {
                "id": "barentswatch",
                "name": "BarentsWatch Fish Health",
                "covers": "Norwegian aquaculture locality data, including weekly salmon lice reports.",
                "tools": ["barentswatch_lice_by_locality"],
                "url": "https://developer.barentswatch.no/docs/fishhealth/",
                "table_structure": barentswatch.TABLE_STRUCTURE,
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
def search_fishstat_species(query: str, limit: int = 20) -> dict:
    """Find FishStat aquatic species or species groups by name or code, including oysters/ostras."""
    try:
        return fishstat.search_species(query, limit)
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
def barentswatch_lice_by_locality(locality_id: int, year: int) -> dict:
    """Download provider-reported weekly mean adult female salmon lice for a Norwegian aquaculture locality and year, with table structure and provenance. The means are supplied by BarentsWatch."""
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
