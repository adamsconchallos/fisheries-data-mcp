# Fisheries Data MCP

A local [Model Context Protocol](https://modelcontextprotocol.io/) server that connects your AI client to fisheries and marine data sources. Ask a research question, find relevant datasets, and download files with their units, structure and source information. Statistical analysis and joining datasets remain part of your research workflow.

**[How to install](#how-to-install)** · [Update Codex (Windows)](#update-the-mcp-in-codex-windows) · [Data coverage](#current-coverage) · [FAQ](FAQ.md) · [Technical reference](docs/REFERENCE.md)

## Current coverage

| Source | What you can retrieve | Access |
| --- | --- | --- |
| FAO FishStat | Capture and aquaculture production quantities; aquaculture production values | No account required |
| BarentsWatch | Norwegian aquaculture sites, lice, temperature, treatments, diseases, escapes, permitted capacity and site details | BarentsWatch API client ID and secret |
| Copernicus Marine | Ocean datasets selected by variable, geographic area and dates | Copernicus Marine account for downloads |
| UN Comtrade | Annual or monthly goods trade by country, partner, HS product and flow | Free API subscription key required for downloads |

The catalogue also describes collections whose downloads are not implemented. These are marked `catalogue_only`; entries with download tools are marked `downloadable`. Availability still depends on the requested species, place, period and your access.

## How to install

These steps use **Windows PowerShell**, with Codex or Claude Code already installed and signed in. You do not need a GitHub account or the FishStat desktop application.

### 1. Install Python

If you do not have Python 3.11 or newer, run:

```powershell
winget install --id Python.Python.3.13 -e
```

Close and reopen PowerShell. If WinGet is unavailable, use the [Python Windows installer](https://www.python.org/downloads/windows/).

### 2. Download or clone the repository

**Without Git:** select **Code → Download ZIP** on the [repository page](https://github.com/adamsconchallos/fisheries-data-mcp), extract the ZIP, and open PowerShell in the extracted folder containing `install.py`.

**With Git:**

```powershell
git clone https://github.com/adamsconchallos/fisheries-data-mcp.git
cd fisheries-data-mcp
```

### 3. Install the MCP server

From that folder, run:

```powershell
py -3 install.py
```

The installer prepares the server, creates `.env` and `mcp-config.json`, and prints the **absolute executable path**. Existing credentials are preserved.

### 4. Connect your AI client

**[Codex in VS Code](https://learn.chatgpt.com/docs/extend/mcp#configure-in-the-ide-extension):** open **⚙️ → MCP servers → Add server**, enter the following and save:

- Name: `fisheries-data`
- Type: **STDIO**
- Command: the executable path printed by the installer
- Arguments: leave empty

**[Claude Code](https://code.claude.com/docs/en/mcp):** run from the repository folder:

```powershell
$mcpExe = (Resolve-Path ".venv\Scripts\fisheries-data-mcp.exe").Path
claude mcp add --scope user --transport stdio fisheries-data -- "$mcpExe"
```

**Cowork:** this repository does not yet provide its required plugin or remote connection. Use one of the clients above or [Claude Desktop Chat](INSTALL.md#claude-desktop-chat-including-users-who-downloaded-claude-for-cowork).

### 5. Add your credentials

In the repository folder, open:

```powershell
notepad .env
```

Fill in the sources you will use and leave the others blank:

```dotenv
BARENTSWATCH_CLIENT_ID=your_client_id
BARENTSWATCH_CLIENT_SECRET=your_client_secret
COPERNICUSMARINE_SERVICE_USERNAME=your_username
COPERNICUSMARINE_SERVICE_PASSWORD=your_password
UN_COMTRADE_API_KEY=your_subscription_key
```

Save `.env` **beside `install.py`**. FishStat needs no credentials. UN Comtrade downloads require each user's own [free API subscription key](https://uncomtrade.org/docs/api-subscription-keys/); reference-code searches remain public. Obtain the other credentials by [registering a BarentsWatch API client](https://developer.barentswatch.no/docs/appreg/) or [creating a Copernicus Marine account](https://help.marine.copernicus.eu/en/articles/4220332-how-to-register-for-copernicus-marine-service).

### 6. Restart and ask

Restart the Codex extension or close and reopen Claude Code. Start a conversation:

> Use Fisheries Data MCP. I want to study salmon production, production value and sea lice in Norway. Which datasets could help? Explain their periods, units and observation levels, and tell me which ones you can download.

Downloads are saved by default to `~/fisheries-data-mcp/exports` with source metadata.

For macOS/Linux, other clients and configuration options, see the [detailed installation guide](INSTALL.md).

## Update the MCP in Codex (Windows)

These steps update the existing installation in `C:\Users\adams\research\fisheries-data-mcp`, which Codex already uses. If you cloned the repository elsewhere, change the path in the first command.

1. Close VS Code and Codex to release the MCP executable. Open a separate PowerShell window.
2. Run these commands in order:

   ```powershell
   Set-Location 'C:\Users\adams\research\fisheries-data-mcp'
   git pull --ff-only
   py -3 install.py
   ```

3. Open the credentials file with `notepad .env`. Add this line with your UN Comtrade key, then save the file:

   ```dotenv
   UN_COMTRADE_API_KEY=your_key
   ```

   If the variable already exists, update its value instead of adding a duplicate.
4. Reopen VS Code and Codex. The `search_comtrade_reference` and `comtrade_trade_records` tools should appear.

The installer preserves `.env` and your existing keys. You do not need to change the MCP configuration because Codex still uses the executable in the same folder.

## Documentation

- [FAQ](FAQ.md): example requests, GitHub basics, updates and troubleshooting.
- [Technical reference](docs/REFERENCE.md): tools, output formats, units, limitations and developer checks.
- [FAO inventory notes](docs/FAO_DISCOVERY_NOTES.md) and [BarentsWatch inventory notes](docs/BARENTSWATCH_DISCOVERY_NOTES.md): catalogue coverage and verification evidence.
