"""Bounded Copernicus Marine catalogue searches and data downloads.

Uses the official Copernicus Marine Toolbox with credentials from the project's
``.env`` file or a saved ``copernicusmarine login``.
"""

from __future__ import annotations

import inspect
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import get_args

import copernicusmarine


MAX_FILE_MB = 200
MAX_TRANSFER_MB = 500
MAX_DESCRIBE_VARIABLES = 50
FORMATS = {"netcdf", "zarr", "csv"}
CATALOGUE_URL = "https://data.marine.copernicus.eu/"


def _date(value: str, name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"{name} must be an ISO date or datetime") from exc
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _status(response: object) -> str:
    status = getattr(response, "status", None)
    return str(getattr(status, "value", status))


def _variables(version: object) -> dict[str, object]:
    found: dict[str, object] = {}
    for part in getattr(version, "parts", []):
        for service in getattr(part, "services", []):
            for variable in getattr(service, "variables", []):
                found.setdefault(variable.short_name, variable)
    return found


def _dataset(catalogue: object, dataset_id: str) -> tuple[object, object]:
    for product in getattr(catalogue, "products", []):
        for dataset in getattr(product, "datasets", []):
            if dataset.dataset_id == dataset_id:
                return product, dataset
    raise ValueError(f"Dataset {dataset_id!r} was not found in the live Copernicus Marine catalogue")


def _citation(product: object) -> str | None:
    doi = getattr(product, "digital_object_identifier", None)
    if not doi:
        return None
    title = getattr(product, "title", None) or getattr(product, "product_id", "Copernicus Marine product")
    accessed = datetime.now(timezone.utc).strftime("%d %b %Y")
    return f"{title}. E.U. Copernicus Marine Service Information (CMEMS). Marine Data Store (MDS). DOI: {doi} (Accessed on {accessed})"


def search_datasets(query: str, limit: int = 10) -> dict:
    """Search the live catalogue and return dataset IDs with variable names."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a nonempty search term")
    if type(limit) is not int or not 1 <= limit <= 25:
        raise ValueError("limit must be an integer between 1 and 25")

    try:
        catalogue = copernicusmarine.describe(contains=[query.strip()], disable_progress_bar=True)
    except Exception as exc:
        raise RuntimeError(f"Copernicus Marine catalogue search failed ({type(exc).__name__})") from None

    results: list[dict] = []
    for product in getattr(catalogue, "products", []):
        for dataset in getattr(product, "datasets", []):
            version = dataset.versions[0] if dataset.versions else None
            names = sorted(_variables(version)) if version else []
            results.append({
                "dataset_id": dataset.dataset_id,
                "dataset_name": dataset.dataset_name,
                "product_id": product.product_id,
                "product_title": product.title,
                "product_doi": getattr(product, "digital_object_identifier", None),
                "dataset_version": getattr(version, "label", None),
                "variables": names,
            })
            if len(results) >= limit:
                return {"query": query.strip(), "datasets": results, "source": CATALOGUE_URL, "limit": limit}
    return {"query": query.strip(), "datasets": results, "source": CATALOGUE_URL, "limit": limit}


def describe_dataset(dataset_id: str) -> dict:
    """Describe one dataset from the live catalogue without downloading data."""
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        raise ValueError("dataset_id must be nonempty")
    dataset_id = dataset_id.strip()
    try:
        catalogue = copernicusmarine.describe(dataset_id=dataset_id, disable_progress_bar=True)
    except Exception as exc:
        raise RuntimeError(f"Copernicus Marine dataset lookup failed ({type(exc).__name__})") from None
    product, dataset = _dataset(catalogue, dataset_id)
    version = dataset.versions[0] if dataset.versions else None
    available = _variables(version) if version else {}
    variables = []
    for name in sorted(available)[:MAX_DESCRIBE_VARIABLES]:
        item = available[name]
        details = {
            "short_name": name,
            "standard_name": getattr(item, "standard_name", None),
            "units": getattr(item, "units", None),
            "bbox": getattr(item, "bbox", None),
        }
        for coordinate in getattr(item, "coordinates", []):
            coordinate_id = getattr(coordinate, "coordinate_id", None)
            if coordinate_id in {"time", "depth", "elevation"}:
                details[coordinate_id] = {
                    "minimum": getattr(coordinate, "minimum_value", None),
                    "maximum": getattr(coordinate, "maximum_value", None),
                    "unit": getattr(coordinate, "coordinate_unit", None),
                }
        variables.append(details)

    product_id = product.product_id
    return {
        "dataset_id": dataset.dataset_id,
        "dataset_name": dataset.dataset_name,
        "dataset_version": getattr(version, "label", None),
        "product_id": product_id,
        "product_title": product.title,
        "product_doi": getattr(product, "digital_object_identifier", None),
        "citation": _citation(product),
        "variables": variables,
        "variable_count": len(available),
        "variables_truncated": len(available) > MAX_DESCRIBE_VARIABLES,
        "source_url": f"https://data.marine.copernicus.eu/product/{product_id}/description",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def _check_coverage(variable: object, west: float, east: float, south: float, north: float,
                    start: datetime, end: datetime) -> None:
    bbox = getattr(variable, "bbox", None)
    if bbox and len(bbox) == 4:
        data_west, data_south, data_east, data_north = bbox
        if south < data_south or north > data_north:
            raise ValueError("Requested latitude is outside the variable's catalogue coverage")
        if data_west <= data_east and not any(
            data_west <= west + shift and east + shift <= data_east
            for shift in (-360, 0, 360)
        ):
            raise ValueError("Requested longitude is outside the variable's catalogue coverage")

    for coordinate in getattr(variable, "coordinates", []):
        if getattr(coordinate, "coordinate_id", None) != "time":
            continue
        minimum = getattr(coordinate, "minimum_value", None)
        maximum = getattr(coordinate, "maximum_value", None)
        if isinstance(minimum, str) and isinstance(maximum, str):
            try:
                first, last = _date(minimum, "catalogue time"), _date(maximum, "catalogue time")
            except ValueError:
                return  # Some catalogue calendars are not ISO datetimes.
            if start < first or end > last:
                raise ValueError("Requested dates are outside the variable's catalogue coverage")


def subset_dataset(
    dataset_id: str,
    variable: str,
    west: float,
    east: float,
    south: float,
    north: float,
    start: str,
    end: str,
    output_dir: str | Path,
    file_format: str = "netcdf",
) -> dict:
    """Download one bounded subset after checking metadata and a size estimate."""
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        raise ValueError("dataset_id must be nonempty")
    if not isinstance(variable, str) or not variable.strip():
        raise ValueError("variable must be nonempty")
    if file_format not in FORMATS:
        raise ValueError(f"file_format must be one of {sorted(FORMATS)}")
    for name, value, low, high in (
        ("west", west, -180, 180), ("east", east, -180, 180),
        ("south", south, -90, 90), ("north", north, -90, 90),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"{name} must be a finite number between {low} and {high}")
    if west >= east or south >= north:
        raise ValueError("Bounding box must have west < east and south < north; split antimeridian requests")
    start_date, end_date = _date(start, "start"), _date(end, "end")
    if start_date > end_date:
        raise ValueError("start must be before or equal to end")

    format_parameter = inspect.signature(copernicusmarine.subset).parameters.get("file_format")
    supported = get_args(format_parameter.annotation) if format_parameter else ()
    if supported and file_format not in supported:
        raise RuntimeError(f"Installed copernicusmarine does not support {file_format}; update the Toolbox")

    try:
        catalogue = copernicusmarine.describe(dataset_id=dataset_id.strip(), disable_progress_bar=True)
    except Exception as exc:
        raise RuntimeError(f"Copernicus Marine dataset lookup failed ({type(exc).__name__})") from None
    product, dataset = _dataset(catalogue, dataset_id.strip())
    if not dataset.versions:
        raise ValueError("The dataset has no available version")
    version = dataset.versions[0]  # describe() returns the current default version.
    available = _variables(version)
    if not available:
        raise ValueError("This dataset has no subset variables in the catalogue; try the Toolbox's get command")
    if variable not in available:
        raise ValueError(f"Variable {variable!r} is unavailable for subset; available: {', '.join(sorted(available))}")
    _check_coverage(available[variable], west, east, south, north, start_date, end_date)

    # check_credentials_valid does not prompt for input, unlike a missing login
    # during subset(). This matters for a server whose stdin carries MCP messages.
    try:
        authenticated = copernicusmarine.login(check_credentials_valid=True)
    except Exception:
        authenticated = False
    if not authenticated:
        raise RuntimeError(
            "Copernicus Marine credentials are unavailable or invalid; "
            "set them in the project's .env or run 'copernicusmarine login' locally"
        )

    directory = Path(output_dir).expanduser().resolve()
    request = dict(
        dataset_id=dataset_id.strip(), dataset_version=version.label,
        variables=[variable], minimum_longitude=west, maximum_longitude=east,
        minimum_latitude=south, maximum_latitude=north,
        start_datetime=start, end_datetime=end, file_format=file_format,
        output_directory=directory, disable_progress_bar=True,
    )
    try:
        preview = copernicusmarine.subset(**request, dry_run=True)
    except Exception as exc:
        raise RuntimeError(f"Copernicus Marine size preview failed ({type(exc).__name__})") from None
    if _status(preview) != "001":
        raise RuntimeError("Copernicus Marine did not return a successful dry-run preview")
    estimates = (
        ("file_size", MAX_FILE_MB), ("data_transfer_size", MAX_TRANSFER_MB),
    )
    known = False
    for field, cap in estimates:
        size = getattr(preview, field, None)
        if size is None:
            continue
        known = True
        if not math.isfinite(size) or size < 0:
            raise RuntimeError("Copernicus Marine returned an invalid size estimate")
        if size > cap:
            raise ValueError(f"Estimated {field} is {size:.1f} MB, above this MCP's {cap} MB limit")
    if not known:
        raise RuntimeError("Copernicus Marine did not provide a size estimate; download was not started")

    directory.mkdir(parents=True, exist_ok=True)
    try:
        result = copernicusmarine.subset(**request)
    except Exception as exc:
        raise RuntimeError(f"Copernicus Marine subset failed ({type(exc).__name__})") from None
    if _status(result) != "000":
        raise RuntimeError("Copernicus Marine did not report a successful download")
    relative = Path(result.file_path)
    candidates = [relative] if relative.is_absolute() else [directory / relative, relative]
    path = next((candidate.resolve() for candidate in candidates if candidate.exists()), None)
    if path is None:
        raise RuntimeError("Copernicus Marine reported success but the downloaded file was not found")

    product_id = product.product_id
    metadata = {
        "file_path": str(path), "file_format": file_format,
        "source": "Copernicus Marine Service",
        "toolbox_version": copernicusmarine.__version__,
        "dataset_id": dataset.dataset_id, "dataset_version": version.label,
        "product_id": product_id, "product_title": product.title,
        "product_doi": getattr(product, "digital_object_identifier", None),
        "variable": variable, "unit": getattr(available[variable], "units", None),
        "estimated_file_size_mb": getattr(preview, "file_size", None),
        "estimated_transfer_mb": getattr(preview, "data_transfer_size", None),
        "source_url": f"https://data.marine.copernicus.eu/product/{product_id}/description",
        "citation": _citation(product),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "selection": {"west": west, "east": east, "south": south, "north": north,
                      "start": start, "end": end},
    }
    metadata_path = path.with_name(f"{path.name}.metadata.json")
    metadata["metadata_path"] = str(metadata_path)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata
