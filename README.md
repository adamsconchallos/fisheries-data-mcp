# Fisheries Data MCP

A local [Model Context Protocol](https://modelcontextprotocol.io/) server to **find, describe and download fisheries and marine data through natural-language requests**. Install it on your computer and connect it to an MCP-compatible AI client. The server delivers data files with source information and explains their structure so you can use them in your own research.

Its scope is data access and preparation: selecting records, downloading bounded subsets, and producing documented country totals where supported. Statistical analysis, modelling, scientific interpretation and joins between sources are outside the server's scope.

## Start with a research question

You do not need to know a dataset name or API route before asking for data. The AI client can search the server's documented catalogue, identify relevant datasets, explain their coverage and limitations, and use the connected download tools once the required filters are clear.

For example:

> I want to study salmon production growth, production value and salmon lice in Norway by year. First identify which available datasets could help. Explain the variables, units, observation level and period; distinguish data this MCP can download from catalogue entries that require another access route. Then help me choose the species, years and locations before downloading. Do not calculate growth rates or combine sources.

For this question, FAO Global Aquaculture provides annual production quantities and monetary production values. BarentsWatch Fish Health provides weekly observations for Norwegian aquaculture localities. A national annual production series and weekly locality reports have different observation levels: selecting and documenting the inputs is supported, while defining a national annual lice indicator and relating it to production belong in the subsequent analysis.

### Data-discovery tools

- `list_datasets(provider="all")` lists the documented datasets and services, including entries whose downloads are not yet connected.
- `search_data_catalogue(query, provider="all", limit=10)` finds catalogue entries relevant to a question or topic.
- `describe_data_dataset(dataset_id)` returns the documented variables, coverage, observation level, access requirements, limitations and source references for one entry.

Catalogue descriptions and connected downloads are separate capabilities. An entry can describe a useful source without a download tool being implemented. Entries marked `downloadable` identify their `download_tools`; entries marked `catalogue_only` require another access route. `downloadable` describes the implemented capability, not a check of your credentials or the existence of every requested observation. The AI client should name the actual tool when a download is supported and clearly identify entries that require an external access route. Suggestions outside this catalogue must also be labelled as external; they are not data retrieved by this MCP.

The catalogue guides discovery; it does not guarantee that every country, species, locality or year has an observation. Check the provider's records before promising a particular table. Copernicus also has a live catalogue search through `search_copernicus_datasets`.

**New to GitHub or MCP?** Follow the [four-step installation guide](INSTALL.md): install Python, clone or download, fill in `.env`, and connect your AI client. It covers Codex in VS Code, Claude Desktop Chat, and the current limits for Cowork and browser chats. The [beginner FAQ](FAQ.md) covers updates and troubleshooting.

## Current coverage

| Source | Connected download workflow | Access |
| --- | --- | --- |
| [FAO FishStat Global Production](https://www.fao.org/fishery/static/Data/GlobalProduction_2026.1.0.zip) | Search aquatic species; annual production tonnes by country, including oysters; select capture, aquaculture or both | The pinned 2026.1.0 ZIP is downloaded and cached on first use, or read from `FISHSTAT_ZIP` |
| [FAO FishStat Global Aquaculture](https://www.fao.org/fishery/static/Data/Aquaculture_2026.1.0.zip) | Download aquaculture quantity and production-value records for a year range, preserving species, country, area, culture environment, measures, units and flags | A separate pinned 2026.1.0 ZIP is downloaded and cached on first use, or read from `FISHSTAT_AQUACULTURE_ZIP` |
| [BarentsWatch Fish Health](https://developer.barentswatch.no/docs/fishhealth/) | Find locality IDs; download lice stages, sea temperature, treatments, disease cases, escapes or permitted capacity for a locality and year; retrieve a site snapshot for an ISO week | Your own registered API client ID and secret |
| [Copernicus Marine](https://help.marine.copernicus.eu/en/articles/7949409-copernicus-marine-toolbox-introduction) | Search the live marine catalogue, describe variables and units, then download a bounded subset by variable, area and dates | Your own Copernicus Marine account |

The sources describe different quantities and spatial scales, and each download retains its source and units. BarentsWatch locality search resolves names or IDs; it does not search municipality names. Comtrade is planned and is not yet connected.

**FishStat contains multiple collections.** The discovery catalogue describes a broader set of collections than the download tools currently support. Direct downloads connect Global Production quantities and Global Aquaculture quantities and production values. Other catalogue entries include source references and access limitations. The production values in Global Aquaculture describe aquaculture production; they are not export values.

The reviewed FishStat inventory includes global production, aquaculture, capture, trade with all partners combined, bilateral trade, processed production, food balances, regional capture, import notifications and employment. Regional capture includes CECAF, GFCM, Southeast Atlantic and RECOFI. Each description records its source references and review date; periods and available variables differ across collections. The [FAO inventory notes](docs/FAO_DISCOVERY_NOTES.md) explain the reviewed workspace families and evidence.

### FishStat query tools

- `search_fishstat_countries(query, limit=20)` finds FAO countries/areas by an English or Spanish name, UN code or ISO code. Use its exact FAO UN `country_code` to filter aquaculture records. Species searches are available through `search_fishstat_species`.
- `fishstat_production_by_country(query, year, source="all", species_code="")` downloads a table of production quantities grouped by country for one year. This tool sums the selected source records and does not return production values.
- `fishstat_aquaculture_records(query, start_year, end_year, country_code="", species_code="", measure="both")` downloads the selected aquaculture records for an inclusive year range. Each row retains the source dimensions and identifies its measure and unit. Quantity and production value are separate records, rather than a joined or aggregated table.

The download tools return local files with provenance and a description of the table. The aquaculture CSV contains all matching rows; the tool response includes only the first 20 rows as a preview. The aquaculture tool preserves the source observations without calculating averages, growth rates or joins between measures or sources.

In the pinned Global Aquaculture release, quantities (`Q_tlw`) cover 1950–2024 and are reported in tonnes: live weight for animals and wet weight for aquatic plants. Production values (`V_USD_1000`) cover 1984–2024 and are reported in **thousands of nominal US dollars**. The download preserves these units without converting values to dollars or adjusting for inflation. Coverage for an individual country or species can be narrower.

### BarentsWatch query tools

- `barentswatch_search_localities(query="", limit=50)` finds current locality names and IDs. Use the returned `localityNo` as `locality_id`. The directory can include non-salmonid sites and does not prove that a site operated or reported lice in a historical year.
- `barentswatch_get_locality_data(locality_id, year, dataset="lice_stages")` downloads one site-year to CSV with metadata. Supported datasets are `lice_stages`, `sea_temperature`, `treatments`, `diseases`, `escapes` and `capacity`. The complete records go into the file; the response previews up to 20 rows.
- `barentswatch_get_locality_details(locality_id, year, week)` downloads the provider's nested JSON snapshot for an ISO week, including licenses, authorized species, capacity, location and fish-health reports. Authorized species and capacity are not observations of actual production or biomass.
- `barentswatch_lice_by_locality(locality_id, year)` remains available for the older adult-female-lice series. For new research requests, prefer `barentswatch_get_locality_data` with `lice_stages`, which preserves reporting flags and all three lice stages.

Lice counts with `hasReportedLice=false` must not be treated as reported zeroes. Temperature reports have a similar `hasReported` flag. Treatments and escapes can contain nested event lists, stored as JSON within CSV cells. Disease cases can span years, and permitted capacity is an administrative limit whose unit must be checked in the site details. These tools preserve provider records; they do not construct national annual indicators.

The catalogue also documents other Fish Health and AquaInfo datasets, municipal statistics, vessel and fisheries services, and environmental observations or forecasts. Many of these are catalogue-only entries. The [BarentsWatch inventory notes](docs/BARENTSWATCH_DISCOVERY_NOTES.md) distinguish the reviewed services and API operations from the retrievals implemented and verified here.

## Install locally

Requires Python 3.11 or newer. Download or clone this repository, open a terminal in its folder, and run one command:

The [installation guide](INSTALL.md#1-install-python-if-needed) provides the Python installation command and both GitHub download routes.

**Windows PowerShell**

```powershell
py -3 install.py
```

**macOS/Linux**

```bash
python3 install.py
```

The installer creates or reuses `.venv`, installs the server, creates an empty `.env` template if needed, and generates `mcp-config.json` with the correct absolute executable path. Rerunning it updates the package and preserves your existing `.env`.

Connect a client that supports local **stdio** MCP servers. If the client uses `mcpServers` JSON, copy the `fisheries-data` entry from the generated `mcp-config.json` into its configuration. If it asks for an executable, use the path printed by the installer. Configuration locations vary by client; the [FAQ](FAQ.md) explains the steps. Restart the client after adding the server.

If you use **Codex in VS Code**, follow its [extension setup](INSTALL.md#codex-in-vs-code); a separate CLI installation is optional.

For **Codex CLI**, the [official MCP setup](https://developers.openai.com/learn/docs-mcp) uses `codex mcp add`. From the repository folder on Windows:

```powershell
$server = (Resolve-Path .\.venv\Scripts\fisheries-data-mcp.exe).Path
codex mcp add fisheries-data -- $server
codex mcp list
```

For **Claude Desktop Chat**, add the entry from `mcp-config.json` to `claude_desktop_config.json` and restart the app. Preserve other entries if the file already exists. The [MCP Python SDK guide](https://py.sdk.modelcontextprotocol.io/get-started/real-host/) gives the configuration file locations for Windows and macOS. This JSON configuration does not connect the server to Claude Cowork; see the [FAQ](FAQ.md#does-the-same-setup-work-in-claude-cowork).

Try this prompt (Spanish or English):

> ¿Qué países produjeron ostras en 2024 y cuántas toneladas produjo cada uno? Usa FishStat, incluye captura y acuicultura, exporta un CSV y cita la fuente y la definición de «ostras».

For aquaculture quantities and production values, try:

> Use FAO Global Aquaculture to download Norway's Atlantic salmon records for 2012–2024, including quantities and production values. Preserve the source records, units and flags, export a CSV, and explain what each row and column represents. Do not calculate averages or growth rates.

The `fishstat_production_by_country` tool exports all matching country rows; `fishstat_aquaculture_records` exports all selected source records and returns a short preview. Both write a CSV plus a metadata JSON file. FishStat and BarentsWatch CSV exports list the actual columns and row count, with descriptions for their standard fields, units, missing values and data preparation. Copernicus returns dataset metadata; file structure depends on the dataset and format. `list_data_sources` describes available output structures before a download. By default, exports go to `~/fisheries-data-mcp/exports`; set `FISHERIES_MCP_OUTPUT_DIR` to choose another local directory. The server never requires an AI service account itself; a natural-language prompt requires an MCP-compatible AI client.

## Credentials

The installer creates `.env` in the repository folder. Open it in a text editor and fill in the credentials for BarentsWatch and/or Copernicus Marine. On Windows:

**Windows PowerShell**

```powershell
notepad .env
```

Fill in only the credentials you use; leave other lines empty. Save the file and restart your AI client. The server finds this `.env` next to the project's `.venv` even when the client starts it from another folder. No credential entries are needed in the Codex or Claude Desktop MCP configuration. Existing operating-system environment variables take precedence over `.env` values.

If you installed manually, copy `.env.example` to `.env` once, only if `.env` does not already exist.

`.env` is ignored by Git but stores secrets as plain text. Keep it private. If your repository is in a synced folder such as OneDrive, the file may sync too; use a local, unsynced clone for credentials or point `FISHERIES_MCP_ENV_FILE` to an absolute path outside the synced folder.

**FishStat:** no account or credentials are needed. Each collection is downloaded and cached separately when first requested:

| Collection | Pinned archive | Optional local-file environment variable |
| --- | --- | --- |
| Global Production quantities | [GlobalProduction_2026.1.0.zip](https://www.fao.org/fishery/static/Data/GlobalProduction_2026.1.0.zip) | `FISHSTAT_ZIP` |
| Global Aquaculture quantities and production values | [Aquaculture_2026.1.0.zip](https://www.fao.org/fishery/static/Data/Aquaculture_2026.1.0.zip) | `FISHSTAT_AQUACULTURE_ZIP` |

To use a downloaded copy or work offline, set the corresponding environment variable to its absolute path before launching your AI client. `FISHSTAT_ZIP` applies only to Global Production; it does not select the Aquaculture archive. These optional file paths are operating-system environment variables, not credential fields loaded from `.env`. The FishStat desktop application is not required.

### BarentsWatch

1. Create a user at [BarentsWatch MyPage](https://www.barentswatch.no/minside/), then register a **BarentsWatch API** client (not an AIS client) under developer access. Save the complete client ID and client secret. See the [official registration guide](https://developer.barentswatch.no/docs/appreg/).
2. Add your credentials to the `.env` file shown above:

   ```dotenv
   BARENTSWATCH_CLIENT_ID=your_full_client_id
   BARENTSWATCH_CLIENT_SECRET=your_client_secret
   ```

   Restart your AI client. The server requests OAuth tokens automatically; you do not need to add the secret to your AI prompt or MCP client configuration.
3. Ask the AI client to find a locality by name or ID, then choose a year and dataset. For example: “Use BarentsWatch to find locality 35657, then download its weekly lice stages and reporting flags for 2022. Export a CSV and explain missing reports.” The [official tutorial](https://developer.barentswatch.no/docs/tutorial/) uses this example ID. Locality search returns current directory entries; verify historical reports before assuming that a site was active in a requested year.

### Copernicus Marine

1. [Create a free account](https://help.marine.copernicus.eu/en/articles/4220332-how-to-register-for-copernicus-marine-service), confirm your email, and set a password. Existing Copernicus Data Space Ecosystem credentials can also be used.
2. Add your Copernicus Marine account details to the same `.env` file:

   ```dotenv
   COPERNICUSMARINE_SERVICE_USERNAME=your_username_or_email
   COPERNICUSMARINE_SERVICE_PASSWORD=your_password
   ```

   Restart your AI client. The [official Toolbox](https://help.marine.copernicus.eu/en/articles/8630590-copernicus-marine-toolbox-faq) reads these environment variables. If you have already run `copernicusmarine login` and saved credentials under your user account, leave these two `.env` lines empty instead. Catalogue searches do not require login; downloads do.
3. Ask the AI client to search for a dataset, describe its exact variables and units, then download a bounded subset. For example: “Search Copernicus Marine for sea temperature datasets. Describe a suitable dataset and show me its variable codes; then download the selected variable for 10–15°E, 68–72°N, 1–7 July 2024 as NetCDF.” Give a specific area and date range, and check the selected dataset before downloading.

Copernicus Marine subsets are saved to `~/fisheries-data-mcp/exports` (or `FISHERIES_MCP_OUTPUT_DIR`) with a provenance JSON file. This server caps each request at an estimated 200 MB output file and 500 MB transfer; these are server safeguards, not Copernicus quotas. CSV output requires a Toolbox version that supports it; NetCDF and Zarr work with version 2.0.1 or newer. The current MCP downloads data but does not calculate averages from NetCDF/Zarr files or select a depth level.

## Scientific use

- FishStat Global Production quantities are annual tonnes: animals are reported in live weight and aquatic plants in wet weight. Country tables sum the selected records across species and areas; `source=all` combines capture and aquaculture. The server records this preparation, the release, selected species, source, and FAO quality flags. A suppressed or missing value is never interpreted as a real zero.
- FishStat Global Aquaculture exports preserve quantity and production-value observations, their units and flags, and the species, country, area, culture environment and year. Production values are in thousands of nominal US dollars. The export leaves `O` (missing) and `Q` (suppressed) values empty and retains their flags, even when the source stores a numeric zero; `N` (non-significant) values retain the reported zero. Production value must not be interpreted as export value, and the server does not calculate a price by dividing value by quantity.
- BarentsWatch Fish Health provides raw reported data, which may contain errors. Missing weeks are not filled, and reporting flags must be checked before interpreting zeroes. The older adult-female-lice endpoint can omit that distinction; prefer the lice-stage dataset for new work. Cleaner-fish treatment data are not included after week 16 of 2018; empty lists after that date do not establish no use. Credit BarentsWatch and the original data owner. [API terms](https://www.barentswatch.no/en/articles/api-terms-and-conditions/).
- Copernicus Marine results include the dataset ID and available product citation information. Cite the [product DOI](https://help.marine.copernicus.eu/en/articles/4444611-citing-copernicus-marine-products-and-services) and record the dataset version and query parameters.
- The MIT license in this repository applies to the code. FAO data, BarentsWatch data, and Copernicus Marine products retain their own terms and attribution requirements. [FAO terms](https://www.fao.org/contact-us/terms/db-terms-of-use/en/).

## Verify the installation

Run the included checks from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

On macOS/Linux, use `.venv/bin/python -m unittest discover -s tests`.

The default checks use small fixtures or mocked API responses. Optional tests use official FAO archives when `FISHSTAT_ZIP` and `FISHSTAT_AQUACULTURE_ZIP` are set. Setting `FISHERIES_MCP_LIVE_BARENTSWATCH=1` enables a sequential authenticated test of locality search, lice CSV export and a weekly JSON snapshot, using your local credentials. These tests preserve reporting flags and verify exported files through an MCP client.

## Development scope

This is an early read-only release. Its reviewed catalogue covers more datasets and services than its connected download tools. The server will need updates when source metadata, schemas or API routes change; MCP tool discovery does not repair upstream changes automatically.

New sources should follow the same local setup and data-access scope: document coverage and fields, expose search/description/download tools as appropriate, preserve source units and quality flags, and return a local file with provenance. Optional credentials belong in `.env.example` and the loader's allowed credential names; existing sources must work without accounts for the new source. Comtrade is the next planned source.
