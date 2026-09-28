# Beginner FAQ and quick start

Start with [How to install](README.md#how-to-install) for the six-step setup. The [detailed installation guide](INSTALL.md) includes additional options for Codex, Claude Code, Claude Desktop Chat, Cowork and browser chats.

This guide is for researchers who want to ask questions through an AI client and receive source-backed fisheries data and CSV files. The server runs on **your computer**. The AI client starts it and discovers its tools.

The server finds, describes and downloads data. It explains columns, units and data preparation; statistical analyses and scientific interpretation belong in your subsequent research workflow.

## Can I start with a research question instead of a dataset name?

Yes. For example:

> I want to study salmon production, production value and salmon lice in Norway by year. Which datasets available through this MCP could help? Explain their variables, units, years and observation levels. Distinguish connected downloads from sources that require another access route, and identify any missing information. Do not analyse the data yet.

The AI client can use `search_data_catalogue` and `describe_data_dataset` to find and explain relevant catalogue entries. `list_datasets` shows the documented inventory. Once species, periods, places and measures are clear, the client can call the applicable download tools and explain the files it retrieves.

In this example, FAO Global Aquaculture provides annual quantity and production-value observations; BarentsWatch provides weekly fish-health reports by locality. Turning the latter into a national yearly lice indicator requires decisions about aggregation and weighting. The server supplies the underlying data and explains this difference; it does not create that indicator or calculate production growth.

## Does a catalogue entry mean the MCP can download that data?

No. The catalogue records both connected datasets (`downloadable`) and useful provider datasets whose downloads are not yet implemented (`catalogue_only`). Check the entry's download tools and limitations. A connected provider may still need your credentials and an appropriate selection. The AI should clearly state which data can be downloaded through this server and which require the provider's site, API or another tool.

A relevant entry is also not proof of a complete time series for your selection. Available years can vary by species, country or locality. Missing observations are not zeros. If the AI suggests a source outside the catalogue, it should label that suggestion as external rather than implying this MCP retrieved or verified its data.

## What do I need?

| Item | Needed? |
| --- | --- |
| A GitHub account | No. This is a public repository. An account is useful only if you want to report an issue, fork it, or contribute. |
| VS Code | No. A terminal (PowerShell on Windows, Terminal on macOS/Linux) is enough. |
| Git | Only if you choose to clone the repository. You can download a ZIP instead. |
| Python | Yes, version 3.11 or newer, to install and run the server. |
| An AI client | Yes, for natural-language questions. It must support **local stdio MCP servers**. Codex in VS Code, Codex CLI and Claude Desktop Chat are documented below. The server itself does not require an AI account. |

FishStat needs no data-source account. UN Comtrade downloads require each user's own free API subscription key; its reference-code searches remain public. BarentsWatch and Copernicus Marine need their own credentials for the relevant tools; see the [credential setup](INSTALL.md#3-fill-in-the-local-env-file).

## Does the server provide all FishStat data?

The server's discovery catalogue describes multiple FishStat collections, with source references and access limitations. Its direct download tools currently connect two:

| Connected collection | What the server downloads |
| --- | --- |
| Global Production | Production quantities grouped by country for one year; choose capture, aquaculture or both. |
| Global Aquaculture | Quantity and production-value records for a year range, preserving species, country, area, culture environment, measure, unit and status. |

Other documented FishStat collections are catalogue entries without connected download tools. Global Production's country tool returns quantities only. Use `fishstat_aquaculture_records` when you need aquaculture production values, including a request for both quantities and values. These are production values, not the value of exports.

For the pinned Global Aquaculture release, quantities cover 1950–2024 in tonnes (live weight for animals; wet weight for aquatic plants). Production values cover 1984–2024 in **thousands of nominal US dollars**. Individual country/species series can have gaps or shorter coverage. The server preserves the units; it does not adjust for inflation or convert the value to a price. Missing (`O`) and suppressed (`Q`) values are exported as empty fields with their flags retained, even if their source field contains `0`. Non-significant (`N`) values keep the reported zero.

Both collections are available without credentials or the FishStat desktop application. The server downloads `GlobalProduction_2026.1.0.zip` and `Aquaculture_2026.1.0.zip` into separate cache files when you first request each collection. For an existing local copy, set `FISHSTAT_ZIP` for Global Production or `FISHSTAT_AQUACULTURE_ZIP` for Global Aquaculture to the corresponding archive's absolute path before starting the AI client. These optional paths are operating-system environment variables; the credential `.env` loader does not read them.

## How do I get the files?

**Option A: Clone with Git.** Install [Git](https://git-scm.com/downloads), open a terminal in the folder where you want the project, and run:

```sh
git clone https://github.com/adamsconchallos/fisheries-data-mcp.git
cd fisheries-data-mcp
```

Cloning does not require a GitHub account. It makes later updates easy with `git pull`.

**Option B: Download a ZIP.** On the [repository page](https://github.com/adamsconchallos/fisheries-data-mcp), choose **Code → Download ZIP**, extract it, and open a terminal inside the extracted folder (the folder containing `pyproject.toml`). A ZIP is a snapshot; to update it later, download and extract a new copy.

For GitHub basics, see [GitHub's cloning guide](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository) and its [ZIP download guide](https://docs.github.com/en/repositories/working-with-files/using-files/downloading-files-from-github). This [beginner video](https://www.youtube.com/watch?v=a9u2yZvsqHA) is an optional visual introduction to GitHub; follow the written commands here for this particular project.

## How do I install the server?

Install [Python 3.11 or newer](https://www.python.org/downloads/) first; the [installation guide](INSTALL.md#1-install-python-if-needed) provides the Windows installation command. In the repository folder, run one command for your system:

**Windows PowerShell**

```powershell
py -3 install.py
```

**macOS/Linux**

```sh
python3 install.py
```

The installer prepares the `.venv` environment and downloads Python dependencies. It also creates `.env` for optional credentials and `mcp-config.json` with your server's absolute path. Existing `.env` credentials are preserved when you rerun it. The first query for each connected FishStat collection downloads and caches its FAO data ZIP separately. You do **not** need the FishStat desktop `.exe`.

## How do I use it with Codex in VS Code?

Configure the server inside the Codex extension; the CLI is optional. Follow the [VS Code walkthrough](INSTALL.md#codex-in-vs-code), including how to obtain the executable path and the fallback `config.toml` entry. The configuration belongs to the Codex host where the server will run. [Official Codex documentation](https://developers.openai.com/learn/docs-mcp).

## How do I use it with Codex?

Install and sign in to [Codex CLI](https://learn.chatgpt.com/docs/codex/cli). It runs in a terminal, so VS Code is optional. From the repository folder, register the installed server:

**Windows PowerShell**

```powershell
$server = (Resolve-Path .\.venv\Scripts\fisheries-data-mcp.exe).Path
codex mcp add fisheries-data -- $server
codex mcp list
```

**macOS/Linux**

```sh
server="$(pwd)/.venv/bin/fisheries-data-mcp"
codex mcp add fisheries-data -- "$server"
codex mcp list
```

`codex mcp list` confirms registration. Start Codex and enter `/mcp` to check that the server's tools are available. Then try the question below. This CLI configuration also applies to the Codex IDE extension on the same host. See [OpenAI's MCP guide](https://developers.openai.com/learn/docs-mcp).

## How do I use it with Claude Desktop Chat?

Install and open [Claude Desktop](https://claude.com/download) once. Edit its `claude_desktop_config.json` file:

| System | Configuration file |
| --- | --- |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |

Open the generated `mcp-config.json` in the repository folder. It already contains the correct absolute path, including JSON escaping on Windows. If `claude_desktop_config.json` does not exist, create it with that content. If it already exists, add only the `fisheries-data` entry inside its existing `mcpServers` object and preserve the other settings.

Fully quit and reopen Claude Desktop, then check the available connectors/tools in **Chat**. The [MCP Python SDK guide](https://py.sdk.modelcontextprotocol.io/get-started/real-host/) explains these configuration paths and restart behavior. The installer generates the entry but does not register it in your AI client automatically.

## How do data-source credentials reach the local server?

The MCP server reads a `.env` file from this repository when your AI client starts it. You do not need to put credentials in Codex's `config.toml`, Claude Desktop's JSON, or an AI prompt. FishStat needs no credentials.

The installer has already created `.env` in the repository folder, beside `install.py` and outside `.venv`. Keep it there and open it in a text editor. On Windows:

**Windows PowerShell**

```powershell
notepad .env
```

Fill in only the sources you want to use; the empty lines are ignored:

```dotenv
BARENTSWATCH_CLIENT_ID=your_full_client_id
BARENTSWATCH_CLIENT_SECRET=your_client_secret
COPERNICUSMARINE_SERVICE_USERNAME=your_username_or_email
COPERNICUSMARINE_SERVICE_PASSWORD=your_password
```

Register a [BarentsWatch API client](https://developer.barentswatch.no/docs/appreg/) to obtain its ID and secret. Create a [Copernicus Marine account](https://help.marine.copernicus.eu/en/articles/4220332-how-to-register-for-copernicus-marine-service) for its username and password. You can leave either pair empty until you need that source. If the official Copernicus Toolbox has already saved your credentials through `copernicusmarine login`, leave its `.env` lines empty. Catalogue searches and dataset descriptions do not need a Copernicus login; downloads do.

Save `.env` and fully restart Codex or Claude Desktop Chat. The server locates the file next to the project's `.venv`, regardless of the AI client's working directory. Existing operating-system environment variables take precedence. The `.env` file is ignored by Git but contains plain-text secrets; keep it private. If the repository is in OneDrive or another synced folder, `.env` may sync too. You can keep credentials in a local, unsynced clone, or set `FISHERIES_MCP_ENV_FILE` to the absolute path of a private `.env` elsewhere.

For a manual installation, copy `.env.example` to `.env` once if `.env` does not already exist.

## Does the same setup work in Claude Cowork?

**Not yet.** The `claude_desktop_config.json` entry above connects to Claude Desktop **Chat**, but [Anthropic says it is unavailable in Cowork](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp). Cowork can use local MCP servers packaged in plugins for local sessions, or remote connectors. This repository does not yet supply either route. If you downloaded Claude for Cowork, use its **Chat** interface with the local configuration above. [Desktop and web connectors](https://support.claude.com/en/articles/11725091-when-to-use-desktop-and-web-connectors).

## What if I only use ChatGPT or Claude in a browser?

This repository's local executable cannot be launched directly by those browser chats. Use a compatible desktop client with the [connection steps](INSTALL.md#4-connect-your-ai-client-and-ask-for-data). VS Code is optional. Direct browser access would need a remote deployment or bridge, which this repository does not currently provide. [OpenAI remote MCP setup](https://developers.openai.com/plugins/build/app-quickstart), [Claude remote connector requirements](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp).

The [ChatGPT desktop route](INSTALL.md#chatgpt-desktop-app-without-vs-code) is also documented for installations with local MCP settings available.

## What can I ask?

For a first query, ask your connected AI client:

> Use FishStat to find oyster production by country in 2024. Include capture and aquaculture, report tonnes, export the results to CSV, and cite the data release and species definition.

For aquaculture quantities and production values, ask:

> Use FAO Global Aquaculture to download Norway's Atlantic salmon records for 2012–2024. Include both quantities and production values, preserve the source records and flags, and export a CSV with the source and units. Explain the table structure without calculating averages or growth rates.

The AI client can call `fishstat_aquaculture_records(query, start_year, end_year, country_code="", species_code="", measure="both")` to fulfill this request. It can first look up the exact country code using `search_fishstat_countries(query, limit=20)`, which accepts English or Spanish country names and UN or ISO codes. Its long-format table keeps quantities and production values as separate rows, with their source dimensions, measure and unit. The CSV contains all matching rows, while the tool response previews the first 20. It does not join the two measures or calculate a price.

For BarentsWatch, you can ask:

> Find BarentsWatch locality 35657, then download its weekly lice stages and sea temperatures for 2022 as separate CSV files. Preserve reporting flags, explain the fields and cite the source. Do not calculate annual averages or merge the files.

The client can use `barentswatch_search_localities` to resolve a name or ID and `barentswatch_get_locality_data` for the selected site-year. Other supported selections include treatments, disease cases, escapes and permitted capacity. `barentswatch_get_locality_details` retrieves a nested JSON site snapshot for a specific ISO week. Locality search is a current directory, not a historical list of operating salmon farms. Check `hasReportedLice` and `hasReported`: a zero associated with no report is not evidence of a measured zero.

The FishStat and UN Comtrade tools write a CSV and a metadata JSON file, by default under `~/fisheries-data-mcp/exports`. You can set `FISHERIES_MCP_OUTPUT_DIR` to choose another folder. The [technical reference](docs/REFERENCE.md) lists the current tools and output details.

You can also ask: "Before downloading, explain what each row and column represents, the units and the available years." FishStat and BarentsWatch CSV exports list the actual columns and row count, with descriptions for their standard fields. FishStat's Global Production country table groups and sums the selected source records; its Global Aquaculture table preserves the selected observations. BarentsWatch preserves provider records and flags, including reported weekly means and event details where applicable. Copernicus downloads a subset without calculating averages and returns dataset metadata; its file structure varies by dataset and format.

## Will adding more sources require a new installation for each one?

New sources are added to this same server. Updating the project makes their tools available through your existing connection. Fill in the credentials for each source you want to use; UN Comtrade downloads specifically require a free API subscription key. It reports country-product trade, not individual producer or buyer firms.

## How do I update it or fix a missing tool?

If you cloned the repository, run `git pull` from its folder, then rerun `py -3 install.py` on Windows or `python3 install.py` on macOS/Linux. Your existing `.env` is preserved. If a new source needs extra credentials, copy its new field names from `.env.example` into `.env` and fill them in only if needed. For the existing Codex installation on Windows, follow the [step-by-step update instructions](README.md#update-the-mcp-in-codex-windows).

If you downloaded a ZIP, download the latest ZIP and install from its extracted folder; transfer your private `.env` to that folder if you want to retain your credentials. After moving the folder, update the executable path in your MCP client using the newly generated `mcp-config.json`. If a tool is missing, verify that the executable exists in `.venv`, that the client points to its **absolute path**, and that you restarted the client. The first query for each FishStat collection may take longer while its FAO ZIP downloads.
