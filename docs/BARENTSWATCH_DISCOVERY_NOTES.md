# BarentsWatch catalogue and retrieval audit

Verified on **28 September 2026** against the provider's public OpenAPI documents and small authenticated requests. API calls were sequential, following the [Fish Health download guidance](https://developer.barentswatch.no/docs/fishhealth/). No credentials or tokens are stored in this report or catalogue.

## What the MCP knows

The packaged [BarentsWatch catalogue](../src/fisheries_data_mcp/catalogues/barentswatch.json) contains **28 dataset/service families**. It records every **GET operation in the inspected Fish Health schema: 126 operations across 27 tags**. The schema has 128 paths in total; the two paths without GET operations are outside this read-only inventory.

The inventory also records GET operations from the public FiskInfo, buoy, reporting, drift, polar-low, Saltstraumen and wave-forecast schemas. Combined, these public schema inventories contain **291 GET operations**. AIS is described separately using its official documentation. An operation appearing in the catalogue does **not** mean the MCP can call it or that the configured client has permission. Each entry lists the implemented `download_tools`; each inventoried operation has an `available_in_mcp` flag. Deprecated operations remain labelled as such.

This is a dated inventory, not a guarantee that all of BarentsWatch's holdings or future endpoints are represented. Restricted/private services, WMS/WFS layers published separately, and future schema changes may need additional discovery.

### Fish Health and AquaInfo families

| Family | Implemented retrieval |
|---|---|
| Site directory | Search current site names or numbers; return identifiers and municipality fields |
| Lice stages | One site-year of adult female, mobile and stationary lice, with reporting flags |
| Site water temperature | One site-year of reported temperatures and reporting flags |
| Treatments | One site-year of the provider's weekly treatment records |
| Disease cases | Version 3 case records for a site-year |
| Escapes | One site-year of reported events, grouped by week |
| Permitted capacity | One site-year of weekly capacity values; inspect site details for units |
| Weekly site snapshot | Version 2 nested site, licenses/species, health and location record |
| National/region threshold statistics | Catalogue only |
| National and multi-site weekly health overview | Catalogue only |
| Species and license-holder reference lists | Catalogue only |
| Bulk CSV/spreadsheet health exports | Catalogue only |
| Disease/treatment controls and export restrictions | Catalogue only |
| AquaInfo locality statistics and environmental surveys | Catalogue only |
| AquaInfo municipality licenses and species counts | Catalogue only |
| AquaInfo municipal statistics, including fund payments | Catalogue only |
| Production-area context | Catalogue only |
| Marine geography, habitats and protected areas | Catalogue only |
| Slaughterhouse information | Catalogue only |
| Vessel visits and tracks around farms | Catalogue only |

The catalogue's `api_operations` preserve the provider's paths, parameter names, tags and deprecation flags so a future connector can locate the authoritative schema. They are descriptive metadata, not an unrestricted HTTP tool.

## Implemented tool contract

1. `barentswatch_search_localities(query="Varden", limit=50)` matches site names or identifiers. It reports truncation and returns the provider's fields, including `localityNo`, `name`, `municipalityNo` and `municipality` when supplied. Search does not match municipality names. The directory includes non-salmonid sites and is not a historical list of operating salmon farms.
2. `barentswatch_get_locality_data(locality_id=35657, year=2024, dataset="lice_stages")` accepts `lice_stages`, `sea_temperature`, `treatments`, `diseases`, `escapes` or `capacity`. Results retain source fields, units/limitations, retrieval time and the request URL. CSV export retains nested values as JSON cells.
3. `barentswatch_get_locality_details(locality_id=35657, year=2024, week=34)` retrieves the nested weekly snapshot for JSON export.
4. The existing `barentswatch_lice_by_locality` tool remains available. Prefer the `lice_stages` dataset when preparing research data because it retains reporting flags that the older adult-female graph endpoint does not provide.

All requests are read-only except the OAuth token exchange. These tools retrieve source records; they do not calculate annual averages, growth rates, treatment effects, or links to FAO data.

## Authenticated verification

The existing project credentials successfully obtained a token with the `api` scope. The following small requests succeeded:

| Request | Observed response |
|---|---|
| Directory query `35657` | One match: Varden, municipality Hitra |
| Lice stages, site 35657, 2024 | 52 weekly rows and `hasReportedLice` flags |
| Temperature, site 35657, 2024 | 52 weekly rows, including null values and `hasReported` flags |
| Treatments, site 35657, 2022 | Six weekly records with nested medicinal/non-medicinal fields |
| Diseases, site 35657, 2024 | One case with a diagnosis in 2023 and closure in 2024 |
| Escapes, site 35657, 2024 | Empty source event list |
| Capacity, site 35657, 2024 | 52 week-keyed capacity values |
| Site snapshot, site 35657, week 34 of 2024 | Coordinates, registry/licenses, authorized species, reporting/fallow flags and health/treatment objects |
| Municipality capacity, 5056, 2024 | Two provider species-category records; this endpoint remains catalogue only |
| National lice-threshold summary, 2024 | Provider weighted site-count and proportion statistics; this endpoint remains catalogue only |

The new provider functions were subsequently exercised against the live service for the directory, all six site-year datasets and the weekly snapshot. The provider test suite includes checks for query encoding/truncation, reporting flags, nested records, cases spanning years, capacity week keys, invalid ISO weeks, source identity mismatches and sanitized HTTP errors.

Only these responses were credential-tested. No AIS, vessel-visit, fishing-facility, user-report, tracking-buoy or drift data were requested. Successful Fish Health authentication does not establish access to those services.

## Interpretation that the assistant must preserve

- **Unreported lice can be zero-valued.** The live stage endpoint returned zero counts with `hasReportedLice=false`. Preserve the flag and explain why those values are not observed zero lice. Temperature has its own reporting flag.
- **Disease cases can cross calendar years.** A case returned for 2024 may have been diagnosed in 2023. Counting returned cases does not give new annual diagnoses.
- **Capacity is a permit limit.** It is not actual standing biomass, harvest volume or annual production. The capacity series omits its unit; the weekly registry snapshot carries a unit such as `TN`. Check rather than inventing units.
- **License species are authorized species.** A permit for salmon and trout does not prove that both were present at a site in the requested week.
- **Treatment reporting changes over time.** Cleaner-fish records are unavailable after week 16 of 2018 in these endpoints; empty lists do not prove no use.
- **Provider summaries answer different questions.** The national threshold endpoint describes sites above general lice limits, not the national mean number of lice per fish. Its statistics have provider-defined weighting and denominators. Regional grouping uses current counties; exemptions may not be represented.
- **Source structures differ from FAO's.** Farm-week health records and country-year production/value records are different units of observation. Choosing annual aggregation and linkage rules belongs to the research analysis, not this MCP.

## Other services and access limits

- **AIS:** separate `ais` OAuth scope and separate service endpoints. The documented open service covers a defined Norwegian sea area, excludes certain smaller vessels and limits historical access to 14 days. It is not a multiyear fleet panel supplied by this MCP. [Live AIS](https://developer.barentswatch.no/docs/AIS/live-ais-api/), [historical AIS](https://developer.barentswatch.no/docs/AIS/historic-ais-api/).
- **FiskInfo:** fishing/navigation layers and download formats are documented, but detailed vessel information in fishing-facility data has separate permission and agreement requirements. [FiskInfo](https://developer.barentswatch.no/docs/FiskInfo/).
- **Reporting and buoys:** user/vendor-associated reports and access are distinct from general open data. The repository does not call their writing endpoints. [Reporting](https://developer.barentswatch.no/docs/FiskInfo/fiskinforeporting/), [FiskInfo service group](https://developer.barentswatch.no/docs/category/fiskinfo/).
- **Forecasts/alerts:** Saltstraumen, coastal wave/current forecasts and polar-low alert schemas are catalogued; current coverage and permissions were not live-tested. [Saltstraumen](https://developer.barentswatch.no/docs/saltstraumen/), [waves](https://developer.barentswatch.no/docs/waveforecast/).
- **Drift:** the schema advertises object/status/path reads, but its scientific applicability and access were not established. The catalogue states this uncertainty.

## Source evidence and maintenance

The public discovery configuration is [OpenAPI `index.js`](https://www.barentswatch.no/bwapi/openapi/index.js). The authoritative Fish Health schema is [fishhealth/openapi.json](https://www.barentswatch.no/bwapi/openapi/fishhealth/openapi.json). Other inspected schemas use the same URL pattern with `fiskinfo`, `fiskinfo-buoys`, `fiskinfo-reporting`, `drift`, `polarlows`, `saltstraumen` and `waveforecast` in place of `fishhealth`.

The public schema snapshots and bounded source responses used in this audit are stored locally under Git-ignored `data/bw_*`; they contain no authentication material and are not required to install or use the MCP. Packaged catalogue entries include official reference URLs and a verification date. Updating an API schema still requires reviewing the affected connector and metadata.
