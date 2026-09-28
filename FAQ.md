# Beginner FAQ and quick start

This guide is for researchers who want to ask questions through an AI client and receive source-backed fisheries data and CSV files. The server runs on **your computer**. The AI client starts it and discovers its tools.

## What do I need?

| Item | Needed? |
| --- | --- |
| A GitHub account | No. This is a public repository. An account is useful only if you want to report an issue, fork it, or contribute. |
| VS Code | No. A terminal (PowerShell on Windows, Terminal on macOS/Linux) is enough. |
| Git | Only if you choose to clone the repository. You can download a ZIP instead. |
| Python | Yes, version 3.11 or newer, to install and run the server. |
| An AI client | Yes, for natural-language questions. It must support **local stdio MCP servers**. Codex CLI and Claude Desktop Chat are documented below. The server itself does not require an AI account. |

FishStat needs no data-source account. BarentsWatch and Copernicus Marine need their own credentials for the relevant tools; see the [README](README.md#credentials). You can start with FishStat and add those credentials later.

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

Install [Python 3.11 or newer](https://www.python.org/downloads/) first. In the repository folder, run the commands for your system:

**Windows PowerShell**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
```

**macOS/Linux**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
```

The final `.` means “install the project in this folder.” The installation downloads Python dependencies; the first FishStat query also downloads and caches the FAO data ZIP. You do **not** need the FishStat desktop `.exe`.

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

`codex mcp list` confirms registration. Start Codex and enter `/mcp` to check that the server's tools are available. Then try the question below. See [OpenAI's MCP guide](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) if your Codex interface differs. The ChatGPT desktop app also supports local stdio servers through **Settings → MCP servers**; a browser session does not read your local Codex configuration.

## How do I use it with Claude Desktop Chat?

Install and open [Claude Desktop](https://claude.com/download) once. Edit its `claude_desktop_config.json` file:

| System | Configuration file |
| --- | --- |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |

Add an `mcpServers` entry with the **absolute path** to the executable you installed. For example, on Windows:

```json
{
  "mcpServers": {
    "fisheries-data": {
      "command": "C:\\Users\\YOUR_NAME\\path\\to\\fisheries-data-mcp\\.venv\\Scripts\\fisheries-data-mcp.exe"
    }
  }
}
```

On macOS, the `command` is the absolute path ending in `/fisheries-data-mcp/.venv/bin/fisheries-data-mcp`. Replace the example path with your real path. If the file already has other servers, add this entry within its existing `mcpServers` object rather than replacing the file. Fully quit and reopen Claude Desktop, then check the available connectors/tools in **Chat**. The [MCP Python SDK guide](https://py.sdk.modelcontextprotocol.io/get-started/real-host/) explains these configuration paths and restart behavior.

## How do data-source credentials reach the local server?

The MCP server reads a `.env` file from this repository when your AI client starts it. You do not need to put credentials in Codex's `config.toml`, Claude Desktop's JSON, or an AI prompt. FishStat needs no credentials.

From the repository folder, make a private copy of the example file:

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
notepad .env
```

**macOS/Linux**

```sh
cp .env.example .env
```

Open `.env` in a text editor on macOS/Linux. Fill in only the sources you want to use; the empty lines are ignored:

```dotenv
BARENTSWATCH_CLIENT_ID=your_full_client_id
BARENTSWATCH_CLIENT_SECRET=your_client_secret
COPERNICUSMARINE_SERVICE_USERNAME=your_username_or_email
COPERNICUSMARINE_SERVICE_PASSWORD=your_password
```

Register a [BarentsWatch API client](https://developer.barentswatch.no/docs/appreg/) to obtain its ID and secret. Create a [Copernicus Marine account](https://help.marine.copernicus.eu/en/articles/4220332-how-to-register-for-copernicus-marine-service) for its username and password. You can leave either pair empty until you need that source. If the official Copernicus Toolbox has already saved your credentials through `copernicusmarine login`, leave its `.env` lines empty. Catalogue searches and dataset descriptions do not need a Copernicus login; downloads do.

Save `.env` and fully restart Codex or Claude Desktop Chat. The server locates the file next to the project's `.venv`, regardless of the AI client's working directory. Existing operating-system environment variables take precedence. The `.env` file is ignored by Git but contains plain-text secrets; keep it private. If the repository is in OneDrive or another synced folder, `.env` may sync too. You can keep credentials in a local, unsynced clone, or set `FISHERIES_MCP_ENV_FILE` to the absolute path of a private `.env` elsewhere.

## Does the same setup work in Claude Cowork?

**Not yet.** The `claude_desktop_config.json` entry above connects to Claude Desktop **Chat**, but [Anthropic says it is unavailable in Cowork](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp). Cowork needs a separately packaged plugin with a local MCP server in a compatible desktop session, or a hosted remote MCP server. This repository has not packaged or tested either Cowork route. See [Anthropic's plugin support guide](https://claude.com/docs/plugins/platform-support). If you want to use this repository now, use Codex CLI or Claude Desktop Chat.

## What can I ask?

For a first query, ask your connected AI client:

> Use FishStat to find oyster production by country in 2024. Include capture and aquaculture, report tonnes, export the results to CSV, and cite the data release and species definition.

The FishStat tool writes a CSV and a metadata JSON file, by default under `~/fisheries-data-mcp/exports`. You can set `FISHERIES_MCP_OUTPUT_DIR` to choose another folder. The [README](README.md#current-coverage) lists the current tools and the extra credentials needed for BarentsWatch and Copernicus Marine.

## How do I update it or fix a missing tool?

If you cloned the repository, run `git pull` from its folder, then repeat the platform-specific `pip install .` command above. If you downloaded a ZIP, download the latest ZIP and install from its extracted folder. After moving the folder, update the executable path in your MCP client. If a tool is missing, verify that the executable exists in `.venv`, that the client points to its **absolute path**, and that you restarted the client. The first FishStat query may take longer while the FAO ZIP downloads.
