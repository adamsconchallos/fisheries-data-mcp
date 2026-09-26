# Fisheries Data MCP

A local [Model Context Protocol](https://modelcontextprotocol.io/) server for research queries across three marine data sources. Install it on your own computer, connect it to an MCP-compatible AI client, and ask questions in ordinary language. The server supplies data and provenance; your AI client writes the answer.

## Current coverage

| Source | Available queries | Access |
| --- | --- | --- |
| [FAO FishStat Global Production](https://www.fao.org/fishery/static/Data/) | Search aquatic species; annual production tonnes by country, including oysters | The pinned 2026.1.0 ZIP is downloaded and cached on first use, or read from `FISHSTAT_ZIP` |
| [BarentsWatch Fish Health](https://developer.barentswatch.no/docs/fishhealth/) | Weekly mean adult female salmon lice for a Norwegian aquaculture locality and year | Your own registered API client ID and secret |
| [Copernicus Marine](https://help.marine.copernicus.eu/en/articles/7949409-copernicus-marine-toolbox-introduction) | Search the live marine catalogue, describe variables and units, then download a bounded subset by variable, area and dates | Your own Copernicus Marine account |

The sources describe different quantities and spatial scales. Results are kept separate unless the researcher specifies a comparison method. Current BarentsWatch coverage requires a locality ID; searching locality names is not yet provided.

## Install locally

Requires Python 3.11 or newer. In a clone of this repository:

**Windows PowerShell**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
```

**macOS/Linux**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
```

Point an MCP client that supports local **stdio** servers at the installed executable. For clients that use `mcpServers` JSON, the entry is:

```json
{
  "mcpServers": {
    "fisheries-data": {
      "command": "ABSOLUTE_PATH_TO_VENV/fisheries-data-mcp"
    }
  }
}
```

On Windows, use the absolute path to `.venv\\Scripts\\fisheries-data-mcp.exe`, with doubled backslashes inside JSON. On macOS/Linux, use `.venv/bin/fisheries-data-mcp`. Configuration file location and field names vary by AI client. Restart the client after adding the server; it should discover the tools automatically.

For **Codex CLI**, the [official MCP setup](https://developers.openai.com/learn/docs-mcp) uses `codex mcp add`. Substitute the absolute path to your installed executable:

```powershell
codex mcp add fisheries-data -- "C:\full\path\to\fisheries_data_mcp\.venv\Scripts\fisheries-data-mcp.exe"
codex mcp list
```

For **Claude Desktop**, place the JSON entry above in `claude_desktop_config.json` and restart the app. The [MCP Python SDK guide](https://py.sdk.modelcontextprotocol.io/get-started/real-host/) gives the configuration file locations for Windows and macOS.

Try this prompt (Spanish or English):

> ¿Qué países produjeron ostras en 2024 y cuántas toneladas produjo cada uno? Usa FishStat, incluye captura y acuicultura, exporta un CSV y cita la fuente y la definición de «ostras».

The `fishstat_production_by_country` tool returns all matching country rows and writes a CSV plus a metadata JSON file. By default, exports go to `~/fisheries-data-mcp/exports`; set `FISHERIES_MCP_OUTPUT_DIR` to choose another local directory. The server never requires an AI service account itself; a natural-language prompt requires an MCP-compatible AI client.

## Credentials

**FishStat:** no account is needed. On first use, the server downloads the pinned [FAO Global Production 2026.1.0 ZIP](https://www.fao.org/fishery/static/Data/GlobalProduction_2026.1.0.zip). To use an already downloaded copy or work offline, set `FISHSTAT_ZIP` to its absolute path before launching your AI client.

**BarentsWatch:** [register an API client](https://developer.barentswatch.no/docs/appreg/) and set `BARENTSWATCH_CLIENT_ID` and `BARENTSWATCH_CLIENT_SECRET` in the environment inherited by your AI client. Open-data API calls still require OAuth authentication. Keep the secret out of Git and shared configuration files.

**Copernicus Marine:** [create a free account](https://help.marine.copernicus.eu/en/articles/4220332-how-to-register-for-copernicus-marine-service), then run `.venv/bin/copernicusmarine login` (macOS/Linux) or `.\.venv\Scripts\copernicusmarine.exe login` (Windows). The official Toolbox stores credentials locally; this server uses that Toolbox for catalogue and subset operations. Large gridded results should normally stay in NetCDF or Zarr rather than CSV.

Copernicus Marine downloads are limited to an estimated 200 MB output file and 500 MB transfer per request. CSV output requires a Toolbox version that supports it; NetCDF and Zarr work with version 2.0.1 or newer.

## Scientific use

- FishStat production is annual tonnes: animals are reported in live weight and aquatic plants in wet weight. The server records the release, selected species, source (capture/aquaculture), and FAO quality flags. A suppressed or missing value is never interpreted as a real zero.
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
