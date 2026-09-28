# Install and connect Fisheries Data MCP

These instructions use **Windows PowerShell**. You need Python 3.11 or newer and an AI application that can run a local MCP server. The server finds, describes and downloads data; it supplies files for your subsequent analysis.

Client documentation checked on **28 September 2026**. For this repository's current local release:

| Your AI application | Connection route |
| --- | --- |
| Codex in VS Code | Add a local STDIO server in the Codex extension. |
| Codex CLI | Register the executable with `codex mcp add`; see the [FAQ](FAQ.md#how-do-i-use-it-with-codex). |
| Claude Desktop Chat | Add the generated entry to `claude_desktop_config.json`. |
| Claude Cowork | Requires a compatible plugin or a remote deployment; neither is packaged by this repository yet. Use Desktop Chat for the current local setup. |
| ChatGPT desktop app | Add a local STDIO server in Settings, where available in your app/workspace. |
| ChatGPT or Claude in a browser | Cannot directly launch this repository's local executable. Use a desktop route below; a remote connection would need additional deployment or bridge setup. |

## 1. Install Python if needed

Open PowerShell and check:

```powershell
py -3 --version
```

If it reports Python 3.11 or newer, continue to step 2. If Python is missing, install Python 3.13, the version used in this project's Windows checks:

```powershell
winget install --id Python.Python.3.13 -e --source winget
```

Close and reopen PowerShell, then run `py -3 --version` again. Restart VS Code too if you are using its integrated terminal. If `winget` is unavailable, use the [Python Windows installer](https://www.python.org/downloads/windows/) and include the Python launcher. If Python is available only as `python`, verify `python --version` and use `python install.py` below.

References: [Python's Windows launcher](https://docs.python.org/3.13/using/windows.html#python-launcher-for-windows), [Microsoft's Python package manifest](https://github.com/microsoft/winget-pkgs/tree/master/manifests/p/Python/Python/3/13), [WinGet installation commands](https://learn.microsoft.com/en-us/windows/package-manager/winget/install).

## 2. Get the repository and install the server

Choose **one** of these routes. Neither requires a GitHub account.

### Route A: clone with Git

Check `git --version`. If Git is missing:

```powershell
winget install --id Git.Git -e --source winget
```

Close and reopen PowerShell after installing Git. Then run:

```powershell
cd $env:USERPROFILE
git clone https://github.com/adamsconchallos/fisheries-data-mcp.git
cd fisheries-data-mcp
py -3 install.py
```

This places the repository under your user profile. You can choose another local folder before cloning. [GitHub's cloning guide](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository).

### Route B: download a ZIP, without Git

On the [repository page](https://github.com/adamsconchallos/fisheries-data-mcp), select **Code → Download ZIP**, extract all files, and open PowerShell inside `fisheries-data-mcp-main`, the folder containing `install.py`. Run `py -3 install.py`.

Alternatively, download, extract and install entirely from PowerShell:

```powershell
cd $env:USERPROFILE
Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/adamsconchallos/fisheries-data-mcp/archive/refs/heads/main.zip" -OutFile "fisheries-data-mcp.zip"
Expand-Archive -LiteralPath "fisheries-data-mcp.zip" -DestinationPath "."
cd fisheries-data-mcp-main
py -3 install.py
```

These commands assume this is your first download into that folder. For later updates, see the [FAQ](FAQ.md#how-do-i-update-it-or-fix-a-missing-tool). [GitHub's ZIP guide](https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives).

The installer prepares `.venv`, installs the server and dependencies, creates `.env` if it is absent, and generates `mcp-config.json`. It prints the server's absolute executable path. You do not need the FishStat desktop program.

## 3. Fill in the local .env file

From the same repository folder:

```powershell
notepad .env
```

The installer already created this file. Keep it **beside `install.py`**, outside `.venv`:

```text
fisheries-data-mcp/        (fisheries-data-mcp-main/ for the ZIP route)
    install.py
    .env
    .venv/
    mcp-config.json
```

Fill in the credentials for the sources you want to use:

```dotenv
BARENTSWATCH_CLIENT_ID=your_full_client_id
BARENTSWATCH_CLIENT_SECRET=your_client_secret
COPERNICUSMARINE_SERVICE_USERNAME=your_username_or_email
COPERNICUSMARINE_SERVICE_PASSWORD=your_password
```

Leave unused fields empty. FishStat needs no credentials. Obtain the BarentsWatch ID and secret by [registering a BarentsWatch API client](https://developer.barentswatch.no/docs/appreg/); use your [Copernicus Marine account](https://help.marine.copernicus.eu/en/articles/4220332-how-to-register-for-copernicus-marine-service) for Copernicus downloads. An existing saved `copernicusmarine login` can be used with its two fields left empty. Comtrade is planned but not yet connected.

Save and close the file. The server reads it automatically, even if the AI client starts from a different folder. These are **data-provider credentials**; sign in to your AI service in its own app. Do not put the secrets in a chat. `.env` is excluded from Git but contains plain text; a folder synchronized with OneDrive can still synchronize it. The [FAQ](FAQ.md#how-do-data-source-credentials-reach-the-local-server) explains alternative file locations.

## 4. Connect your AI client and ask for data

Choose the route for the application you use. After configuration, the client starts the MCP process; you do not need to keep a PowerShell window running the server.

### Codex in VS Code

Use the local Codex extension session. From PowerShell in the repository, display the command path:

```powershell
(Resolve-Path .\.venv\Scripts\fisheries-data-mcp.exe).Path
```

In the Codex panel, open the gear menu and select **MCP servers → Add server**. Set the name to `fisheries-data`, choose **STDIO**, and paste the displayed path into the command field. Arguments and credential fields can remain empty. Save and select **Restart extension**. Check that the server is enabled. [OpenAI's extension setup](https://learn.chatgpt.com/docs/extend/mcp#configure-in-the-ide-extension).

The CLI is optional for this route. If your extension does not show the setup form, update it or edit `%USERPROFILE%\.codex\config.toml` with this entry, replacing the path with the one printed above:

```toml
[mcp_servers.fisheries-data]
command = 'C:\Users\YOUR_NAME\fisheries-data-mcp\.venv\Scripts\fisheries-data-mcp.exe'
```

Edit an existing entry of that name instead of duplicating it. Codex CLI and the extension share the same host configuration. These Windows paths assume Codex runs on Windows; a WSL or SSH session needs an installation and paths accessible in that environment. [OpenAI's configuration example](https://developers.openai.com/learn/docs-mcp).

### Claude Desktop Chat, including users who downloaded Claude for Cowork

Install [Claude Desktop](https://claude.com/download), sign in, and use **Chat** for this repository's current local configuration.

Open **Settings → Developer → Edit Config**. On Windows the file is:

```text
%APPDATA%\Claude\claude_desktop_config.json
```

Open the generated `mcp-config.json` from the repository. If the Claude configuration file is new, paste its contents. Otherwise, add just the `fisheries-data` entry inside the existing `mcpServers` object, preserving the other settings. Save, fully quit Claude Desktop, and reopen it. Check the available tools under **+ → Connectors**. [Local MCP setup](https://modelcontextprotocol.io/docs/develop/connect-local-servers), [Anthropic's Desktop guide](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop).

**Cowork uses a different installation route.** Anthropic supports local MCP tools packaged in plugins for local Cowork sessions, but this repository does not yet provide that plugin. The `claude_desktop_config.json` entry above is not available in Cowork. [Desktop and web connectors](https://support.claude.com/en/articles/11725091-when-to-use-desktop-and-web-connectors), [custom connector requirements](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp).

### ChatGPT desktop app, without VS Code

In a current desktop app with MCP settings available, open **Settings → MCP servers → Add server**. Enter `fisheries-data`, choose **STDIO**, and supply the same executable path shown by `Resolve-Path` above. Save and restart the server using the app's control. The `.env` remains in the repository folder. [OpenAI's desktop MCP instructions](https://learn.chatgpt.com/docs/extend/mcp).

### Only ChatGPT or Claude in a web browser

The browser chat cannot directly start this local executable or use a Windows path as a remote connector URL. For this release, install a compatible desktop client and follow its route above; VS Code is optional.

Direct browser use needs an MCP connection reachable by the service, such as a remote deployment or an appropriate bridge/tunnel. This repository currently supplies neither a hosted endpoint nor a configured bridge. A GitHub URL is a source-code download location, not an MCP endpoint. See [ChatGPT web MCP plugins](https://learn.chatgpt.com/docs/extend/mcp), [OpenAI's remote MCP quickstart](https://developers.openai.com/plugins/build/app-quickstart), and [Claude remote connectors](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp).

### First request and downloaded files

Start a new conversation in your configured local client and ask:

> Use Fisheries Data MCP to list the available sources. Then retrieve FishStat oyster production by country in 2024, including capture and aquaculture. Download a CSV, explain the columns and units, and give me the source and file location. Do not run a statistical analysis.

Check that the client calls a server tool and returns a file path. The first FishStat request downloads and caches the FAO ZIP and can take longer. By default, files are saved under:

```text
C:\Users\YOUR_NAME\fisheries-data-mcp\exports
```

This default output folder is based on your Windows user profile, independently of where you installed the repository. Keep the accompanying `.metadata.json` with the data file. Restart the client after changing `.env`; you do not need to repeat installation for each conversation.

For macOS/Linux, use Python 3.11 or newer and run `python3 install.py`. The server executable is `.venv/bin/fisheries-data-mcp`; the [FAQ](FAQ.md) lists the macOS Claude configuration path and CLI setup.
