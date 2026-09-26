"""Read FAO FishStat Global Production without requiring FishStatJ or pandas.

The ZIP is downloaded on first use into the user's data directory. Set
``FISHSTAT_ZIP`` to an existing copy to work offline or pin a local file.
"""

from __future__ import annotations

import csv
import calendar
import io
import os
import shutil
import tempfile
import unicodedata
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path


DATASET_VERSION = "2026.1.0"
ZIP_NAME = f"GlobalProduction_{DATASET_VERSION}.zip"
SOURCE_URL = f"https://www.fao.org/fishery/static/Data/{ZIP_NAME}"
MEASURE = "Q_tlw"  # FAO's quantity code; plants are reported in wet weight.

_SOURCES = {
    "all": {"CAPTURE", "FRESHWATER", "BRACKISHWATER", "MARINE"},
    "capture": {"CAPTURE"},
    "aquaculture": {"FRESHWATER", "BRACKISHWATER", "MARINE"},
}
_OYSTER_TERMS = {"oyster", "oysters", "ostra", "ostras", "ostion", "ostiones"}
_SEAWEED_TERMS = {"seaweed", "seaweeds", "alga", "algas", "macroalga", "macroalgas"}
_SEAWEED_GROUPS = {"Brown seaweeds", "Red seaweeds", "Green seaweeds"}
_FLAG_WARNINGS = {
    "Q": "Q: hay datos suprimidos; la suma disponible es parcial.",
    "N": "N: algunos valores son no significativos (<0,5) y figuran como cero.",
    "I": "I: la suma incluye valores imputados por FAO.",
    "E": "E: la suma incluye valores estimados.",
    "P": "P: la suma incluye valores provisionales.",
    "X": "X: la suma incluye datos de una organización internacional.",
}
_STATUS_LEGEND = {
    "A": "Valor oficial",
    "E": "Valor estimado",
    "I": "Valor imputado por la agencia receptora",
    "N": "Valor no significativo (<0,5)",
    "P": "Valor provisional",
    "Q": "Valor faltante o suprimido",
    "X": "Valor de organización internacional",
}


def _fold(value: str) -> str:
    """Compare English/Spanish names without case or accent differences."""
    return "".join(
        char for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char)
    ).strip()


def _validate_archive(archive: zipfile.ZipFile) -> None:
    required = (
        "Global_production_quantity.csv",
        "CL_FI_SPECIES_GROUPS.csv",
        "CL_FI_COUNTRY_GROUPS.csv",
        "CL_History.txt",
    )
    for filename in required:
        archive.getinfo(filename)
    history = archive.read("CL_History.txt").decode("utf-8-sig")
    releases = [
        line for line in history.splitlines()
        if "release of Aquaculture/Capture/GlobalProduction" in line
    ]
    if not releases or releases[-1].split()[0] != DATASET_VERSION:
        raise ValueError(f"Expected FishStat Global Production release {DATASET_VERSION}")


def _provenance() -> dict:
    accessed = date.today()
    access_label = f"{accessed.day} {calendar.month_name[accessed.month]} {accessed.year}"
    return {
        "dataset_version": DATASET_VERSION,
        "source_url": SOURCE_URL,
        "accessed_on": accessed.isoformat(),
        "citation": (
            "FAO. 2026. FishStat: Global production by production source 1950-2024. "
            f"[Accessed on {access_label}]. In: FishStatJ. Available at "
            "https://www.fao.org/fishery/en/statistics/software/fishstatj. "
            "Licence: CC-BY-4.0."
        ),
    }


def _zip_path() -> Path:
    override = os.getenv("FISHSTAT_ZIP")
    if override:
        path = Path(override).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"FISHSTAT_ZIP does not exist: {path}")
        return path

    base = os.getenv("LOCALAPPDATA") or os.getenv("XDG_DATA_HOME")
    data_dir = Path(base) if base else Path.home() / ".local" / "share"
    path = data_dir / "fisheries_data_mcp" / ZIP_NAME
    if path.is_file():
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        try:
            with urllib.request.urlopen(SOURCE_URL, timeout=60) as response:
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as target:
                    temporary = Path(target.name)
                    shutil.copyfileobj(response, target)
        except OSError as exc:
            raise RuntimeError(
                f"Could not download FishStat from {SOURCE_URL}. "
                "Download the ZIP in a browser and set FISHSTAT_ZIP to its local path."
            ) from exc
        with zipfile.ZipFile(temporary) as archive:
            _validate_archive(archive)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


def _rows(archive: zipfile.ZipFile, filename: str):
    with archive.open(filename) as raw:
        with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text:
            yield from csv.DictReader(text)


def _matched_species(species: list[dict], query: str, species_code: str | None = None) -> list[dict]:
    if species_code:
        return [row for row in species if row["3A_Code"] == species_code.upper().strip()]
    folded = _fold(query)
    if not folded:
        raise ValueError("Give a species name or ASFIS species_code.")
    if folded in _OYSTER_TERMS:
        matches = [row for row in species if row["ISSCAAP_Group_En"] == "Oysters"]
    elif folded in _SEAWEED_TERMS:
        matches = [row for row in species if row["ISSCAAP_Group_En"] in _SEAWEED_GROUPS]
    else:
        fields = ("3A_Code", "Name_En", "Name_Es", "Scientific_Name")
        matches = [row for row in species if any(folded in _fold(row[field]) for field in fields)]
    return sorted(matches, key=lambda row: (not row["Name_En"], row["Name_En"], row["3A_Code"]))


def _species_summary(row: dict) -> dict:
    return {
        "code": row["3A_Code"],
        "name_en": row["Name_En"] or row["Scientific_Name"],
        "name_es": row["Name_Es"],
        "scientific_name": row["Scientific_Name"],
    }


def _selection_rule(query: str, species_code: str | None = None) -> str:
    if species_code:
        return f"Exact ASFIS species item {species_code.upper().strip()}"
    folded = _fold(query)
    if folded in _OYSTER_TERMS:
        return "FAO ISSCAAP group 'Oysters' (excludes pearl oysters and unrelated common names)"
    if folded in _SEAWEED_TERMS:
        return "FAO ISSCAAP groups Brown, Red and Green seaweeds"
    return f"Name or ASFIS code contains {query!r}"


def search_species(query: str, limit: int = 20) -> dict:
    """Find ASFIS species items by code, common name, or scientific name.

    Generic oyster/seaweed terms select FAO ISSCAAP groups. An ASFIS ``NEI``
    item denotes otherwise unidentified production; it is not a precomputed
    total and can be counted alongside identified species items.
    """
    if limit < 1:
        raise ValueError("limit must be positive")
    with zipfile.ZipFile(_zip_path()) as archive:
        _validate_archive(archive)
        matches = _matched_species(list(_rows(archive, "CL_FI_SPECIES_GROUPS.csv")), query)
    return {
        "query": query,
        "selection_rule": _selection_rule(query),
        "total_matches": len(matches),
        "species": [_species_summary(row) for row in matches[:limit]],
        **_provenance(),
    }


def production_by_country(
    query: str,
    year: int,
    source: str = "all",
    species_code: str | None = None,
) -> dict:
    """Return annual production tonnes by FAO country/area.

    ``source`` is ``all``, ``capture``, or ``aquaculture``. Generic oyster and
    seaweed requests use FAO's ISSCAAP groups, not substring matching: this
    excludes unrelated names such as oyster blenny and pearl-oyster products.
    Rows with status ``Q`` are suppressed, despite their CSV value of zero;
    their country totals are flagged as incomplete. No aggregate species
    totals are added to the species-item observations.
    """
    source = source.lower().strip()
    if source not in _SOURCES:
        raise ValueError("source must be 'all', 'capture', or 'aquaculture'")
    year = int(year)
    result = {
        "query": query,
        "year": year,
        "source": source,
        "selection_rule": _selection_rule(query, species_code),
        "measure": MEASURE,
        "unit": "tonnes",
        "weight_basis": None,
        **_provenance(),
        "species": [],
        "matched_species_count": 0,
        "rows": [],
        "status_legend": {},
        "warnings": [],
    }
    if not 1950 <= year <= 2024:
        result["warnings"].append("FishStat Global Production 2026.1.0 covers 1950–2024.")
        return result

    with zipfile.ZipFile(_zip_path()) as archive:
        _validate_archive(archive)
        species = _matched_species(list(_rows(archive, "CL_FI_SPECIES_GROUPS.csv")), query, species_code)
        if not species:
            result["warnings"].append("No matching species item exists in FishStat Global Production.")
            return result
        plant_selection = {row["Major_Group"] == "PLANTAE AQUATICAE" for row in species}
        if len(plant_selection) != 1:
            result["warnings"].append("La selección mezcla plantas y animales, cuyas cantidades usan bases de peso distintas; especifique un grupo.")
            return result
        result["weight_basis"] = "wet weight" if True in plant_selection else "live weight"
        result["matched_species_count"] = len(species)
        codes = {row["3A_Code"] for row in species}
        countries = {row["UN_Code"]: row["Name_En"] for row in _rows(archive, "CL_FI_COUNTRY_GROUPS.csv")}

        totals: dict[str, Decimal] = defaultdict(Decimal)
        flags: dict[str, Counter] = defaultdict(Counter)
        observed_codes = set()
        for row in _rows(archive, "Global_production_quantity.csv"):
            if (
                row["PERIOD"] != str(year)
                or row["SPECIES.ALPHA_3_CODE"] not in codes
                or row["PRODUCTION_SOURCE_DET.CODE"] not in _SOURCES[source]
                or row["MEASURE"] != MEASURE
            ):
                continue
            country_code = row["COUNTRY.UN_CODE"]
            status = row["STATUS"]
            observed_codes.add(row["SPECIES.ALPHA_3_CODE"])
            flags[country_code][status] += 1
            if status != "Q":
                totals[country_code] += Decimal(row["VALUE"])
        result["species"] = [_species_summary(row) for row in species if row["3A_Code"] in observed_codes]

    seen_flags = set()
    for country_code in sorted(flags, key=lambda code: (countries.get(code, code), code)):
        country_flags = flags[country_code]
        seen_flags.update(country_flags)
        result["rows"].append({
            "country": countries.get(country_code, country_code),
            "country_code": country_code,
            "year": year,
            "tonnes": float(totals[country_code]) if sum(country_flags.values()) > country_flags["Q"] else None,
            "status": ",".join(sorted(country_flags)),
            "warnings": [_FLAG_WARNINGS[flag] for flag in sorted(country_flags) if flag in _FLAG_WARNINGS],
        })
    result["warnings"] = [_FLAG_WARNINGS[flag] for flag in sorted(seen_flags) if flag in _FLAG_WARNINGS]
    result["status_legend"] = {
        flag: _STATUS_LEGEND.get(flag, "Consulte CL_FI_SYMBOL_SDMX.csv en el ZIP de FAO")
        for flag in sorted(seen_flags)
    }
    if not result["rows"]:
        result["warnings"].append("No observations for the selected species, year, and source.")
    return result
