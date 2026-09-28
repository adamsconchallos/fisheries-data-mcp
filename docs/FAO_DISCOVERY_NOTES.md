# FishStat discovery audit

Verified **28 September 2026**. The bundled catalogue describes the current public FishStatJ workspace inventory, not every historical FAO release or every database operated by FAO.

## Inventory and provenance

The authoritative inventory is FAO's [FishStatJ update manifest](https://www.fao.org/fishery/static/FishStatJ/current_version.xml), cross-checked against the [FishStatJ download directory](https://www.fao.org/fishery/static/FishStatJ/) and [CSV ZIP directory](https://www.fao.org/fishery/static/Data/). The manifest lists **seven workspace families**, each at version **2026.1.0**:

- Global production: `FAO_FI_GLOBAL_PROD`
- Aquatic trade: `FAO_FI_GLOBAL_TRADE`
- Processed production: `FAO_FI_GLOBAL_PP`
- Food balance sheets: `FAO_FI_FBS`
- Regional capture: `FAO_FI_REGIONAL`
- Border rejections/import notifications: `FAO_FI_REJECTION`
- Primary-sector employment: `FAO_FI_EMPLOY`

The ten entries in `src/fisheries_data_mcp/catalogues/fishstat.json` split production into Global Production, Aquaculture and Capture, and trade into all-partner and bilateral collections. Regional capture includes four explicit subdatasets. Together these entries represent all seven families in the manifest on the verification date. A public archive URL is a provider reference; it does not mean the MCP has an implemented download tool for that archive.

| Catalogue collection | Verified years | Main measures | MCP record download today |
| --- | --- | --- | --- |
| Global Production | 1950–2024 | Production weight; source also contains animal counts | Country totals in tonnes only |
| Aquaculture | Quantity 1950–2024; value 1984–2024 | Tonnes; thousands of nominal USD | Original quantity/value records |
| Capture | 1950–2024 | Live/wet-weight tonnes; numbers for selected animals | Standalone archive not connected; country tonnes available through Global Production with `source="capture"` |
| Aquatic trade, all partners | 1976–2024 | Net product-weight tonnes; thousands of USD | Catalogue only |
| Aquatic trade, by partner | 2019–2024 | Net product-weight tonnes; thousands of USD | Catalogue only |
| Processed production | 1976–2024 | Tonnes of processed product | Catalogue only |
| Food balance sheets | 1961–2021 | Live-weight-equivalent tonnes, population and nutrient availability | Catalogue only |
| Regional capture | CECAF/GFCM 1970–2024; SEATL 1975–2024; RECOFI 1986–2024 | Live-weight tonnes by statistical division | Catalogue only |
| Import notifications | 2016–2025 | Monthly notification counts | Catalogue only |
| Employment | 1995–2024 | Number of people | Catalogue only |

These are dataset-level time ranges, not promises that every country, species or variable has observations in every year. The catalogue does not refresh itself automatically when FAO issues a new release.

## Evidence inspected

The audit read public source metadata and small archive headers rather than extrapolating from teaching extracts:

- Production: installed FAO 2026.1.0 workspace attachments `FIproduction_E.html`, `Aqua_E.html`, `Capture_E.html`; the current connector's two CSV schemas; and the [March 2026 release notice](https://www.fao.org/statistics/events/events-detail/global-production.-march-2026-update/en).
- Trade: `META_TRADE_EN.pdf` inside the locally installed 2026.1.0 trade workspace, metadata updated 30 June 2026. It verifies the two time ranges, reporter/partner distinction, product-weight quantities, thousands of USD, generally CIF imports and FOB exports, and ISSCFC products. The official distribution is [the trade workspace](https://www.fao.org/fishery/static/FishStatJ/FAO_FI_GLOBAL_TRADE_2026.1.0.fws). FAO already offers trade data; the separate UN Comtrade connector uses HS product codes and is another source, not the only trade source.
- Processed production: `META_PP_EN.pdf`, metadata updated 20 July 2026, in the installed [processed-production workspace](https://www.fao.org/fishery/static/FishStatJ/FAO_FI_GLOBAL_PP_2026.1.0.fws). The measure is output product weight and excludes unprocessed whole fresh/live products.
- Food balance sheets: `META_FOOD_BALANCE_EN.pdf`, metadata updated 24 July 2026, in the installed [food-balance workspace](https://www.fao.org/fishery/static/FishStatJ/FAO_FI_FBS_2026.1.0.fws). It explicitly gives **1961–2021**. Per-capita food and nutrient availability must be derived from totals and population. Newer dates in the separate FAOSTAT Food Balances domain must not be substituted for this FishStat collection. No current food-balance CSV ZIP was listed in the inspected FAO Data directory.
- Regional capture: the public [2026.1.0 regional ZIP](https://www.fao.org/fishery/static/Data/FI_Regional_2026.1.0.zip), its four data filenames and headers, plus the installed `CECAF_E.html`, `GFCM_E.html`, `ATL_SE_E.html` and `RECOFI_E.html` citations and definitions. Each CSV keeps country, species, statistical division, period, value, status and measure.
- Import notifications: the public [2026.1.0 ZIP](https://www.fao.org/fishery/static/Data/BorderRejections_2026.1.0.zip), `REJECTIONS_NUMBER.csv`, and `BorderRejections_Notes.html`. There are 8,300 source rows; the actual `PERIOD` range is **2016–2025**. Columns include importing/exporting countries, product, cause, month, year, measure, status and value. Counts are notifications, not a food-safety prevalence estimate.
- Employment: the public [2026.1.0 ZIP](https://www.fao.org/fishery/static/Data/FI_Employment_2026.1.0.zip), `META_EMPLOY_EN.pdf`, code lists and `EMPLOY_NUMBER.csv`; also the [September 2026 release notice](https://www.fao.org/statistics/events/events-detail/global-employment-in-fisheries-and-aquaculture.-september-2026-update/en). The CSV has 42,135 rows spanning 1995–2024, with country, work domain, working-time category, gender, measure, period, value and status. Measure `Q_no_1` is number of people. The shared work-domain code list includes Processing and Subsistence, but the release metadata says those domains are not published because coverage is limited; a code-list item alone is not evidence that observations are available.

FAO's [collection methodology page](https://www.fao.org/statistics/data-collection/fishery-and-aquaculture/en) also discusses fishery fleet, disposition and other statistical activities. Their existence does not establish a corresponding downloadable FishStatJ workspace in the current manifest. They should not be presented as connected collections without separate verification and implementation.

## Local scripts and Markdown supplied by the project

The likely script/Markdown pair mentioned by the user is **`../README_seafood_charts.md` and `../fishstatj_extraction/`**. The Markdown maps six locally installed FishStatJ workspaces and describes a SQL/JDBC extraction pipeline. The audit read `build_production.py` and `build_trade.py` and the pipeline descriptions for `aggregate_production.py` and `aggregate_trade.py`.

Useful lessons for the MCP:

- Preserve stable reference codes. The existing notes document a failed species-name join caused by a changed Alaska pollock display name; use ASFIS/FAO codes to connect labels to observations.
- Trade commodities, trade flows and production species are different dimensions. `build_trade.py` reads both `TSD_TRADE_VALUE` and `TSD_TRADE_QUANTITY`; trade value cannot be treated as aquaculture production value.
- The local scripts target particular charts. `build_production.py` excludes aquatic mammals and plants, and its output drops the fishing-area field. That export is not the full production database and does not establish the MCP's desired data coverage.
- The local aggregation scripts deflate money, group countries/products and calculate ratios. Those are analysis steps and are outside this MCP's current find/describe/download scope.
- Local workspace identifiers, Derby/JVM paths and SQL table names are installation-specific. Users of the public CSV connectors do not need FishStatJ, Java, JDBC or the author's directory layout.
- Preserve source dimensions, years, measures and flags. Do not reuse a teaching-specific species or country exclusion as a default database filter.

Additional relevant material:

- `../secondary_data_workshop/build_fishstatj_practice_csv.py` and `../secondary_data_workshop/05_fishstatj_practice_notes.md` document a deliberately restricted four-country, 2014–2024 teaching extract. They distinguish source area/environment dimensions and explain why zero stored with missing/suppressed flags is not a real zero. Their country and taxonomic restrictions belong to that exercise.
- `../mcp_aprendizaje/README.md`, `fishstat_mcp.py` and `verificar_fishstat.py` are earlier MCP-learning materials. They establish the progression from a simple example to FishStat access; they do not enumerate the provider's complete current inventory.

For missing-value interpretation, distinguish `L`, `M`, `O`, and `Q` from a reported zero. `N` is a positive amount below the source's reporting threshold and can be encoded as zero. Keep the original flag and measure unit; a quantity threshold cannot be assumed to be the same numeric scale as a monetary threshold.

## Discovery behavior

Recommend a connected dataset with its actual tool name and the supported output. Describe other verified FishStat collections as **known to the catalogue, not yet downloadable through this MCP**. State that outside-provider suggestions are external, not connected data access. For the Norway salmon question, Global Aquaculture can supply national annual quantity and production value; weekly farm lice observations from BarentsWatch have a different observational unit and do not become a national annual causal series merely by downloading both sources.
