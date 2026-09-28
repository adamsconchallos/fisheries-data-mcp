"""Read FAO FishStat Global Production and Aquaculture without FishStatJ or pandas.

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
AQUACULTURE_ZIP_NAME = f"Aquaculture_{DATASET_VERSION}.zip"
AQUACULTURE_SOURCE_URL = f"https://www.fao.org/fishery/static/Data/{AQUACULTURE_ZIP_NAME}"
AQUACULTURE_FILES = {
    "quantity": ("Aquaculture_Quantity.csv", "Q_tlw"),
    "value": ("Aquaculture_Value.csv", "V_USD_1000"),
}
AQUACULTURE_COVERAGE = {"quantity": [1950, 2024], "value": [1984, 2024]}
AQUACULTURE_TABLE_STRUCTURE = {
    "row_definition": "One original observation per country, species, FAO area, culture environment, year and measure. Quantity and monetary value occupy separate rows.",
    "column_descriptions": {
        "country": "FAO country/area name.",
        "country_code": "FAO UN country/area code; retain as text.",
        "species": "English species name, with scientific-name fallback.",
        "species_code": "ASFIS three-letter species item code.",
        "scientific_name": "Scientific name supplied by FAO.",
        "area_code": "FAO major fishing area code; retain as text.",
        "environment_code": "FAO culture environment code.",
        "environment": "FAO culture environment name.",
        "year": "Production year.",
        "measure": "Q_tlw for production quantity; V_USD_1000 for production value.",
        "value": "Observation in the stated unit. Monetary values retain the source scale of thousands of USD.",
        "unit": "Tonnes live weight for aquatic animals, tonnes wet weight for plants, or thousands of USD.",
        "status": "Original FAO observation flag; see status_legend.",
    },
    "preparation": "Filter the two Aquaculture tables and append their records in long format, adding reference labels. Preserve source dimensions, units and flags; no summation, joining, inflation adjustment or growth calculation.",
    "missing_values": "L, M, O, Q and blank source values become empty CSV cells. Reported zeroes and N flags are retained. Missing observations are not filled; quantity and value can have different coverage.",
}

TABLE_STRUCTURE = {
    "row_definition": "One FAO country/area for the requested year and species/source selection.",
    "column_descriptions": {
        "country": "FAO country/area name.",
        "country_code": "UN country/area code used by FAO; retain as text.",
        "year": "Production year.",
        "tonnes": "Sum of available production quantities; see weight_basis for live or wet weight.",
        "status": "Comma-separated FAO flags from the selected observations; see status_legend.",
        "warnings": "Warnings about the selected observations; a JSON list in the CSV cell.",
    },
    "preparation": "Filter by species, year and production source, then sum available quantities by country across selected species and areas. Source 'all' combines capture and aquaculture.",
    "missing_values": "Q observations are excluded from the sum. Totals with some Q observations are partial; tonnes is empty when all selected observations for a country are Q. Countries with no observations are omitted.",
}

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


def _validate_archive(archive: zipfile.ZipFile, collection: str = "GlobalProduction") -> None:
    data_files = (
        ("Aquaculture_Quantity.csv", "Aquaculture_Value.csv", "CL_FI_PRODENVIRONMENT.csv", "CL_FI_SYMBOL_SDMX.csv")
        if collection == "Aquaculture" else ("Global_production_quantity.csv",)
    )
    required = (*data_files,
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
        label = "Aquaculture" if collection == "Aquaculture" else "Global Production"
        raise ValueError(f"Expected FishStat {label} release {DATASET_VERSION}")


def _provenance(collection: str = "GlobalProduction") -> dict:
    accessed = date.today()
    access_label = f"{accessed.day} {calendar.month_name[accessed.month]} {accessed.year}"
    return {
        "dataset_version": DATASET_VERSION,
        "collection": collection,
        "source_url": AQUACULTURE_SOURCE_URL if collection == "Aquaculture" else SOURCE_URL,
        "accessed_on": accessed.isoformat(),
        "citation": (
            ("FAO. 2026. FishStat: Global aquaculture production 1950-2024. "
             if collection == "Aquaculture" else
             "FAO. 2026. FishStat: Global production by production source 1950-2024. ") +
            f"[Accessed on {access_label}]. In: FishStatJ. Available at "
            "https://www.fao.org/fishery/en/statistics/software/fishstatj. "
            "Licence: CC-BY-4.0."
        ),
    }


def _zip_path(collection: str = "GlobalProduction") -> Path:
    aquaculture = collection == "Aquaculture"
    env_name = "FISHSTAT_AQUACULTURE_ZIP" if aquaculture else "FISHSTAT_ZIP"
    zip_name = AQUACULTURE_ZIP_NAME if aquaculture else ZIP_NAME
    source_url = AQUACULTURE_SOURCE_URL if aquaculture else SOURCE_URL
    override = os.getenv(env_name)
    if override:
        path = Path(override).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"{env_name} does not exist: {path}")
        return path

    base = os.getenv("LOCALAPPDATA") or os.getenv("XDG_DATA_HOME")
    data_dir = Path(base) if base else Path.home() / ".local" / "share"
    path = data_dir / "fisheries_data_mcp" / zip_name
    if path.is_file():
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        try:
            request = urllib.request.Request(source_url, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "*/*",
                "Referer": "https://www.fao.org/fishery/static/Data/",
            })
            with urllib.request.urlopen(request, timeout=60) as response:
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as target:
                    temporary = Path(target.name)
                    shutil.copyfileobj(response, target)
        except OSError as exc:
            raise RuntimeError(
                f"Could not download FishStat from {source_url}. "
                f"Download the ZIP in a browser and set {env_name} to its local path."
            ) from exc
        with zipfile.ZipFile(temporary) as archive:
            _validate_archive(archive, collection)
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


def search_countries(query: str, limit: int = 20) -> dict:
    """Resolve a country name or UN/ISO code using the Aquaculture reference list."""
    folded = _fold(query)
    if not folded or limit < 1:
        raise ValueError("Give a country name or code and a positive limit.")
    with zipfile.ZipFile(_zip_path("Aquaculture")) as archive:
        _validate_archive(archive, "Aquaculture")
        countries = list(_rows(archive, "CL_FI_COUNTRY_GROUPS.csv"))
        matches = [
            row for row in countries
            if any(folded == _fold(row.get(field, "")) for field in ("UN_Code", "ISO2_Code", "ISO3_Code"))
        ]
        if not matches:
            matches = [row for row in countries if any(
                folded in _fold(row.get(field, "")) for field in ("Name_En", "Name_Es", "Name_Fr")
            )]
    matches.sort(key=lambda row: row["Name_En"])
    return {
        "query": query,
        "total_matches": len(matches),
        "countries": [
            {"country_code": row["UN_Code"], "name_en": row["Name_En"],
             "name_es": row.get("Name_Es", ""), "iso3_code": row.get("ISO3_Code", "")}
            for row in matches[:limit]
        ],
        "note": "Reference-list membership does not guarantee observations for a requested species and period.",
        **_provenance("Aquaculture"),
    }


def aquaculture_records(
    query: str,
    start_year: int,
    end_year: int,
    country_code: str = "",
    species_code: str = "",
    measure: str = "both",
) -> dict:
    """Select original aquaculture quantity/value records, retaining every source dimension."""
    if measure not in ("quantity", "value", "both"):
        raise ValueError("measure must be 'quantity', 'value', or 'both'")
    if (type(start_year) is not int or type(end_year) is not int
            or not 1950 <= start_year <= end_year <= 2024):
        raise ValueError("Choose start_year <= end_year within the 1950-2024 release coverage.")
    country_code = country_code.strip()
    selected_measures = list(AQUACULTURE_FILES) if measure == "both" else [measure]
    result = {
        "query": query,
        "start_year": start_year,
        "end_year": end_year,
        "country_code": country_code,
        "requested_measure": measure,
        "selection_rule": _selection_rule(query, species_code or None),
        "coverage": AQUACULTURE_COVERAGE,
        "table_structure": AQUACULTURE_TABLE_STRUCTURE,
        "value_basis": "Nominal aquaculture production value in thousands of USD, as supplied by FAO; no currency conversion or inflation adjustment by this server.",
        **_provenance("Aquaculture"),
        "species": [],
        "rows": [],
        "status_legend": {},
        "warnings": [],
    }
    if "value" in selected_measures and start_year < 1984:
        result["warnings"].append("Aquaculture production values cover 1984-2024; earlier years are not filled.")
    with zipfile.ZipFile(_zip_path("Aquaculture")) as archive:
        _validate_archive(archive, "Aquaculture")
        countries = {row["UN_Code"]: row["Name_En"] for row in _rows(archive, "CL_FI_COUNTRY_GROUPS.csv")}
        if country_code and country_code not in countries:
            raise ValueError("Unknown FAO UN country_code. Use search_fishstat_countries to resolve the country.")
        species = _matched_species(list(_rows(archive, "CL_FI_SPECIES_GROUPS.csv")), query, species_code or None)
        if not species:
            result["warnings"].append("No matching species item in the FishStat reference list.")
            return result
        by_species = {row["3A_Code"]: row for row in species}
        environments = {row["Code"]: row["Name_En"] for row in _rows(archive, "CL_FI_PRODENVIRONMENT.csv")}
        symbols = {row["Symbol"]: row["Name_En"] for row in _rows(archive, "CL_FI_SYMBOL_SDMX.csv")}
        observed_species = set()
        observed_flags = set()
        for selection in selected_measures:
            filename, expected_measure = AQUACULTURE_FILES[selection]
            for row in _rows(archive, filename):
                if (row["SPECIES.ALPHA_3_CODE"] not in by_species
                        or not start_year <= int(row["PERIOD"]) <= end_year
                        or (country_code and row["COUNTRY.UN_CODE"] != country_code)):
                    continue
                if row["MEASURE"] != expected_measure:
                    raise ValueError(f"Unexpected measure in {filename}: {row['MEASURE']}")
                item = by_species[row["SPECIES.ALPHA_3_CODE"]]
                unit = ("thousands of USD" if selection == "value" else
                        "tonnes wet weight" if item["Major_Group"] == "PLANTAE AQUATICAE" else
                        "tonnes live weight")
                status = row["STATUS"]
                missing = status in {"L", "M", "O", "Q"} or not row["VALUE"].strip()
                result["rows"].append({
                    "country": countries.get(row["COUNTRY.UN_CODE"], row["COUNTRY.UN_CODE"]),
                    "country_code": row["COUNTRY.UN_CODE"],
                    "species": item["Name_En"] or item["Scientific_Name"],
                    "species_code": item["3A_Code"],
                    "scientific_name": item["Scientific_Name"],
                    "area_code": row["AREA.CODE"],
                    "environment_code": row["ENVIRONMENT.ALPHA_2_CODE"],
                    "environment": environments.get(row["ENVIRONMENT.ALPHA_2_CODE"], row["ENVIRONMENT.ALPHA_2_CODE"]),
                    "year": int(row["PERIOD"]),
                    "measure": expected_measure,
                    "value": None if missing else float(Decimal(row["VALUE"])),
                    "unit": unit,
                    "status": status,
                })
                observed_species.add(item["3A_Code"])
                observed_flags.add(status)
        result["species"] = [_species_summary(item) for item in species if item["3A_Code"] in observed_species]
        result["status_legend"] = {flag: symbols.get(flag, "Unspecified source flag") for flag in sorted(observed_flags)}
    result["rows"].sort(key=lambda row: (
        row["country_code"], row["species_code"], row["year"], row["area_code"], row["environment_code"], row["measure"]
    ))
    if not result["rows"]:
        result["warnings"].append("No observations for the selected country, species, period and measure.")
    return result


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
        "table_structure": TABLE_STRUCTURE,
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
