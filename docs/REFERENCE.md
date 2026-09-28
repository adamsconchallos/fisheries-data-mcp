# Tools and data reference

For setup, see [installation](../INSTALL.md). For common questions, see the [FAQ](../FAQ.md).

## Available tools

### Discovery

| Tool | Purpose |
| --- | --- |
| `list_data_sources` | Summarize connected sources and output structures. |
| `list_datasets` | List reviewed datasets and their download status. |
| `search_data_catalogue` | Find candidate datasets from English or Spanish topics. |
| `describe_data_dataset` | Explain variables, units, coverage, access and limitations. |

`downloadable` identifies an implemented tool; it does not confirm credentials or particular observations. `catalogue_only` requires another access route. Verify selections with source tools before promising data. See the [FAO inventory](FAO_DISCOVERY_NOTES.md) and [BarentsWatch inventory](BARENTSWATCH_DISCOVERY_NOTES.md) for reviewed sources and dates.

### FAO FishStat

| Tool | Purpose |
| --- | --- |
| `search_fishstat_species` | Resolve species names, groups and codes. |
| `search_fishstat_countries` | Resolve country/area names and UN/ISO codes. |
| `fishstat_production_by_country` | Export one year's country totals for capture, aquaculture or both. |
| `fishstat_aquaculture_records` | Export quantity/value records over a year range, preserving source dimensions. |

### BarentsWatch

| Tool | Purpose |
| --- | --- |
| `barentswatch_search_localities` | Find current site names and IDs; municipality-name search is unsupported. |
| `barentswatch_get_locality_data` | Export a site-year: `lice_stages`, `sea_temperature`, `treatments`, `diseases`, `escapes` or `capacity`. |
| `barentswatch_get_locality_details` | Export a nested site snapshot for an ISO week. |
| `barentswatch_lice_by_locality` | Retrieve the older adult-female-lice series; prefer `lice_stages` for reporting flags. |

### Copernicus Marine

| Tool | Purpose |
| --- | --- |
| `search_copernicus_datasets` | Search the live catalogue. |
| `describe_copernicus_dataset` | Inspect variables, units, coverage, version and citation. |
| `subset_copernicus_dataset` | Download one variable by bounding box and dates. |

## Files and interpretation

Exports go to `~/fisheries-data-mcp/exports`, configurable with the operating-system environment variable `FISHERIES_MCP_OUTPUT_DIR`. FishStat and BarentsWatch table downloads produce CSV plus metadata JSON with provenance, columns, units, row counts and preparation notes. Nested values occupy JSON-encoded CSV cells. Aquaculture and BarentsWatch site-year responses preview 20 rows; files contain all matching rows. Empty table results produce no CSV. Site snapshots remain nested JSON.

- **FishStat quantities:** annual tonnes, live weight for animals and wet weight for plants. Country totals sum selected records; `source=all` combines capture and aquaculture. Suppressed `Q` observations are excluded, partial totals marked, and entirely suppressed totals left empty.
- **Aquaculture:** one row per country, species, area, culture environment, year and measure. In release 2026.1.0, quantity covers 1950–2024 and production value 1984–2024. Values are **thousands of nominal USD**, not export values. Flags `L`, `M`, `O`, `Q` and blank observations become empty cells; reported zeroes and `N` remain. Individual coverage varies.
- **BarentsWatch:** weekly locality reports and events differ from FAO's annual records. Unreported lice (`hasReportedLice=false`) and temperature (`hasReported=false`) must not become measured zeroes. Missing weeks remain absent. Disease cases can span years. Cleaner-fish data stop after week 16 of 2018. Permitted capacity and licensed species do not establish actual biomass, production or stocked species; check capacity units in site details.
- **Copernicus:** NetCDF or Zarr; CSV depends on installed Toolbox support. Requests are capped at estimated **200 MB output / 500 MB transfer**, server limits rather than provider quotas. No depth filter or spatial/temporal averages are implemented. Files retain dataset-specific coordinates and provenance.

## Attribution

The code's MIT license does not replace data-provider terms. Follow [FAO terms](https://www.fao.org/contact-us/terms/db-terms-of-use/en/), credit BarentsWatch and original owners under its [API terms](https://www.barentswatch.no/en/articles/api-terms-and-conditions/), and cite [Copernicus product DOIs](https://help.marine.copernicus.eu/en/articles/4444611-citing-copernicus-marine-products-and-services). Retain dataset versions and query metadata.

## Verification and contributions

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

On macOS/Linux: `.venv/bin/python -m unittest discover -s tests`.

Default tests use fixtures or mocked responses. Optional tests use local FAO archives via `FISHSTAT_ZIP` and `FISHSTAT_AQUACULTURE_ZIP`; `FISHERIES_MCP_LIVE_BARENTSWATCH=1` enables authenticated, sequential BarentsWatch checks.

Contributions should document coverage, preserve units and flags, and return files with provenance. Keep the scope to discovery and data retrieval, including documented query totals. Analysis and cross-source joins remain outside this server. Upstream API changes require maintenance; MCP discovery does not repair them automatically.
