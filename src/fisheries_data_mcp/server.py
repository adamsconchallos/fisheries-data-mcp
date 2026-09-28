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


mcp = MCPServer("Fisheries Data")


def _output_dir() -> Path:
    configured = os.environ.get("FISHERIES_MCP_OUTPUT_DIR")
    return Path(configured).expanduser() if configured else Path.home() / "fisheries-data-mcp" / "exports"


def _export_rows(rows: list[dict], metadata: dict, label: str) -> dict[str, str]:
    if not rows:
        return {}
    directory = _output_dir()
    directory.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:60] or "query"
    stem = f"{slug}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
    csv_path = directory / f"{stem}.csv"
    columns = list(dict.fromkeys(key for row in rows for key in row))
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
    return {"csv_path": str(csv_path), "metadata_path": str(metadata_path)}


def _tool_error(exc: Exception) -> ToolError:
    return exc if isinstance(exc, ToolError) else ToolError(str(exc))


@mcp.tool()
def list_data_sources() -> dict:
    """List connected sources and their coverage so the assistant can choose the right one."""
    return {
        "sources": [
            {
                "id": "fishstat",
                "name": "FAO FishStat Global Production",
                "covers": "Annual aquatic capture and aquaculture production by country, species and area; 1950-2024 in release 2026.1.0.",
                "tools": ["search_fishstat_species", "fishstat_production_by_country"],
                "url": "https://www.fao.org/fishery/static/Data/",
            },
            {
                "id": "barentswatch",
                "name": "BarentsWatch Fish Health",
                "covers": "Norwegian aquaculture locality data, including weekly salmon lice reports.",
                "tools": ["barentswatch_lice_by_locality"],
                "url": "https://developer.barentswatch.no/docs/fishhealth/",
            },
            {
                "id": "copernicus_marine",
                "name": "Copernicus Marine Service",
                "covers": "Ocean observations, reanalyses and forecasts by variable, area, time and depth.",
                "tools": ["search_copernicus_datasets", "describe_copernicus_dataset", "subset_copernicus_dataset"],
                "url": "https://data.marine.copernicus.eu/",
            },
        ],
        "scope_note": "These sources have different units and spatial and temporal scales. Do not join or sum them without an explicit method.",
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
    """Find annual production tonnes by FAO country/area for an aquatic species or group; export a CSV. Source: all, capture or aquaculture. Optionally set an exact ASFIS species_code. The weight basis depends on the species group."""
    try:
        result = fishstat.production_by_country(query, year, source, species_code or None)
        result.update(_export_rows(result.get("rows", []), {k: v for k, v in result.items() if k != "rows"}, f"fishstat-{query}-{year}"))
        return result
    except Exception as exc:
        raise _tool_error(exc) from exc


@mcp.tool()
def barentswatch_lice_by_locality(locality_id: int, year: int) -> dict:
    """Retrieve weekly mean adult female salmon lice for a Norwegian aquaculture locality and year."""
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
