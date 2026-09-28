# Beginner FAQ and quick start

For the complete sequence, use the [four-step installation guide](INSTALL.md): install Python, clone or download the repository, fill in `.env`, and connect your AI client. It includes Windows commands and the differences between Codex in VS Code, Claude Chat, Cowork and browser chats.

This guide is for researchers who want to ask questions through an AI client and receive source-backed fisheries data and CSV files. The server runs on **your computer**. The AI client starts it and discovers its tools.

The server finds, describes and downloads data. It explains columns, units and data preparation; statistical analyses and scientific interpretation belong in your subsequent research workflow.

## What do I need?

| Item | Needed? |
| --- | --- |
| A GitHub account | No. This is a public repository. An account is useful only if you want to report an issue, fork it, or contribute. |
| VS Code | No. A terminal (PowerShell on Windows, Terminal on macOS/Linux) is enough. |
| Git | Only if you choose to clone the repository. You can download a ZIP instead. |
| Python | Yes, version 3.11 or newer, to install and run the server. |
| An AI client | Yes, for natural-language questions. It must support **local stdio MCP servers**. Codex in VS Code, Codex CLI and Claude Desktop Chat are documented below. The server itself does not require an AI account. |

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

Install [Python 3.11 or newer](https://www.python.org/downloads/) first; the [installation guide](INSTALL.md#1-install-python-if-needed) provides the Windows installation command. In the repository folder, run one command for your system:

**Windows PowerShell**

```powershell
py -3 install.py
```

**macOS/Linux**

```sh
python3 install.py
```

The installer prepares the `.venv` environment and downloads Python dependencies. It also creates `.env` for optional credentials and `mcp-config.json` with your server's absolute path. Existing `.env` credentials are preserved when you rerun it. The first FishStat query downloads and caches the FAO data ZIP. You do **not** need the FishStat desktop `.exe`.

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

The FishStat tool writes a CSV and a metadata JSON file, by default under `~/fisheries-data-mcp/exports`. You can set `FISHERIES_MCP_OUTPUT_DIR` to choose another folder. The [README](README.md#current-coverage) lists the current tools and the extra credentials needed for BarentsWatch and Copernicus Marine.

You can also ask: "Before downloading, explain what each row and column represents, the units and the available years." FishStat and BarentsWatch CSV exports list the actual columns and row count, with descriptions for their standard fields. FishStat's country table groups and sums the selected source records; BarentsWatch preserves the provider's reported weekly means. Copernicus downloads a subset without calculating averages and returns dataset metadata; its file structure varies by dataset and format.

## Will adding more sources require a new installation for each one?

New sources will be added to this same server. Updating the project will make their tools available through your existing connection. Fill in any optional credentials for the sources you want to use; an account for every provider is not required. Comtrade is planned but is not yet available.

## How do I update it or fix a missing tool?

If you cloned the repository, run `git pull` from its folder, then rerun `py -3 install.py` on Windows or `python3 install.py` on macOS/Linux. Your existing `.env` is preserved. If a new source needs extra credentials, copy its new field names from `.env.example` into `.env` and fill them in only if needed.

If you downloaded a ZIP, download the latest ZIP and install from its extracted folder; transfer your private `.env` to that folder if you want to retain your credentials. After moving the folder, update the executable path in your MCP client using the newly generated `mcp-config.json`. If a tool is missing, verify that the executable exists in `.venv`, that the client points to its **absolute path**, and that you restarted the client. The first FishStat query may take longer while the FAO ZIP downloads.
