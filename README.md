# Fisheries Data MCP

A local [Model Context Protocol](https://modelcontextprotocol.io/) server to **find, describe and download fisheries and marine data through natural-language requests**. Install it on your computer and connect it to an MCP-compatible AI client. The server delivers data files with source information and explains their structure so you can use them in your own research.

Its scope is data access and preparation: selecting records, downloading bounded subsets, and producing documented country totals where supported. Statistical analysis, modelling, scientific interpretation and joins between sources are outside the server's scope.

**New to GitHub or MCP?** Follow the [four-step installation guide](INSTALL.md): install Python, clone or download, fill in `.env`, and connect your AI client. It covers Codex in VS Code, Claude Desktop Chat, and the current limits for Cowork and browser chats. The [beginner FAQ](FAQ.md) covers updates and troubleshooting.

## Current coverage

| Source | Available queries | Access |
| --- | --- | --- |
| [FAO FishStat Global Production](https://www.fao.org/fishery/static/Data/) | Search aquatic species; annual production tonnes by country, including oysters | The pinned 2026.1.0 ZIP is downloaded and cached on first use, or read from `FISHSTAT_ZIP` |
| [BarentsWatch Fish Health](https://developer.barentswatch.no/docs/fishhealth/) | Weekly mean adult female salmon lice for a Norwegian aquaculture locality and year | Your own registered API client ID and secret |
| [Copernicus Marine](https://help.marine.copernicus.eu/en/articles/7949409-copernicus-marine-toolbox-introduction) | Search the live marine catalogue, describe variables and units, then download a bounded subset by variable, area and dates | Your own Copernicus Marine account |

The sources describe different quantities and spatial scales, and each download retains its source and units. Current BarentsWatch coverage requires a locality ID; searching locality names is not yet provided. Comtrade is planned and is not yet connected.

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

The `fishstat_production_by_country` tool returns all matching country rows and writes a CSV plus a metadata JSON file. FishStat and BarentsWatch CSV exports list the actual columns and row count, with descriptions for their standard fields, units, missing values and data preparation. Copernicus returns dataset metadata; file structure depends on the dataset and format. `list_data_sources` describes available output structures before a download. By default, exports go to `~/fisheries-data-mcp/exports`; set `FISHERIES_MCP_OUTPUT_DIR` to choose another local directory. The server never requires an AI service account itself; a natural-language prompt requires an MCP-compatible AI client.

## Credentials

The installer creates `.env` in the repository folder. Open it in a text editor and fill in the credentials for BarentsWatch and/or Copernicus Marine. On Windows:

**Windows PowerShell**

```powershell
notepad .env
```

Fill in only the credentials you use; leave other lines empty. Save the file and restart your AI client. The server finds this `.env` next to the project's `.venv` even when the client starts it from another folder. No credential entries are needed in the Codex or Claude Desktop MCP configuration. Existing operating-system environment variables take precedence over `.env` values.

If you installed manually, copy `.env.example` to `.env` once, only if `.env` does not already exist.

`.env` is ignored by Git but stores secrets as plain text. Keep it private. If your repository is in a synced folder such as OneDrive, the file may sync too; use a local, unsynced clone for credentials or point `FISHERIES_MCP_ENV_FILE` to an absolute path outside the synced folder.

**FishStat:** no account or `.env` entries are needed. On first use, the server downloads the pinned [FAO Global Production 2026.1.0 ZIP](https://www.fao.org/fishery/static/Data/GlobalProduction_2026.1.0.zip). To use an already downloaded copy or work offline, set `FISHSTAT_ZIP` to its absolute path before launching your AI client.

### BarentsWatch

1. Create a user at [BarentsWatch MyPage](https://www.barentswatch.no/minside/), then register a **BarentsWatch API** client (not an AIS client) under developer access. Save the complete client ID and client secret. See the [official registration guide](https://developer.barentswatch.no/docs/appreg/).
2. Add your credentials to the `.env` file shown above:

   ```dotenv
   BARENTSWATCH_CLIENT_ID=your_full_client_id
   BARENTSWATCH_CLIENT_SECRET=your_client_secret
   ```

   Restart your AI client. The server requests OAuth tokens automatically; you do not need to add the secret to your AI prompt or MCP client configuration.
3. Ask for a **locality ID and year**, for example: “Use BarentsWatch to retrieve weekly adult female salmon lice for locality 35657 in 2022; export the CSV and cite the source.” The [official tutorial](https://developer.barentswatch.no/docs/tutorial/) uses this example ID. The current server does not search locality names; consult the [Fish Health API documentation](https://developer.barentswatch.no/docs/fishhealth/) or BarentsWatch site to identify an ID.

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

- FishStat production is annual tonnes: animals are reported in live weight and aquatic plants in wet weight. Country tables sum the selected records across species and areas; `source=all` combines capture and aquaculture. The server records this preparation, the release, selected species, source, and FAO quality flags. A suppressed or missing value is never interpreted as a real zero.
- BarentsWatch Fish Health provides raw reported data, which may contain errors. Missing weeks are not filled. Credit BarentsWatch and the original data owner. [API terms](https://www.barentswatch.no/en/articles/api-terms-and-conditions/).
- Copernicus Marine results include the dataset ID and available product citation information. Cite the [product DOI](https://help.marine.copernicus.eu/en/articles/4444611-citing-copernicus-marine-products-and-services) and record the dataset version and query parameters.
- The MIT license in this repository applies to the code. FAO data, BarentsWatch data, and Copernicus Marine products retain their own terms and attribution requirements. [FAO terms](https://www.fao.org/contact-us/terms/db-terms-of-use/en/).

## Verify the installation

Run the included checks from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

On macOS/Linux, use `.venv/bin/python -m unittest discover -s tests`.

The checks use small fixtures or mocked API responses. The FishStat oyster example can additionally be verified against the official ZIP by setting `FISHSTAT_ZIP` and calling the tool through an MCP client.

## Development scope

This is an early read-only release. It currently offers one BarentsWatch Fish Health measure and one Copernicus subset workflow. The server will need updates when source schemas or API routes change; MCP tool discovery does not repair upstream changes automatically.

New sources should follow the same local setup and data-access scope: document coverage and fields, expose search/description/download tools as appropriate, preserve source units and quality flags, and return a local file with provenance. Optional credentials belong in `.env.example` and the loader's allowed credential names; existing sources must work without accounts for the new source. Comtrade is the next planned source.
