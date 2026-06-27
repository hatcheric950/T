# T

## Webull OpenAPI MCP server

This repo is configured with the [Webull OpenAPI](https://developer.webull.com/)
MCP server so that an MCP-aware client (e.g. Claude Code) can access Webull market
data and account tooling.

### Files

| File | Purpose |
| --- | --- |
| `.mcp.json` | Project-scoped MCP server definition. Credentials are read from environment variables, not hardcoded. |
| `.env.example` | Template for the required credentials. Copy to `.env` and fill in real values. |

### Setup

1. **Install the runner.** The server is launched with [`uvx`](https://docs.astral.sh/uv/)
   (part of `uv`). Install `uv` if you don't have it:

   ```sh
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Create API credentials.** Generate an App Key / App Secret in the
   [Webull OpenAPI developer portal](https://developer.webull.com/).

3. **Provide the credentials.** Copy the example file and fill it in:

   ```sh
   cp .env.example .env
   # edit .env and set WEBULL_APP_KEY / WEBULL_APP_SECRET
   ```

   `.env` is gitignored, so your secrets are never committed. Export the values
   into your shell (or have your MCP client load the `.env`) before starting the
   client so the `${WEBULL_APP_KEY}` style references in `.mcp.json` resolve:

   ```sh
   set -a && . ./.env && set +a
   ```

4. **Start your MCP client** in this directory. It will read `.mcp.json` and
   launch the `webull` server via `uvx webull-openapi-mcp serve`.

### Configuration reference

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `WEBULL_APP_KEY` | yes | — | App Key from the Webull developer portal. |
| `WEBULL_APP_SECRET` | yes | — | App Secret from the Webull developer portal. |
| `WEBULL_REGION_ID` | no | `us` | Region: `us`, `hk`, `jp`. |
| `WEBULL_ENVIRONMENT` | no | `prod` | `prod` or `uat`. |

> **Security note:** Never commit real API keys. Keep them in `.env` (gitignored)
> and rotate them in the developer portal if they are ever exposed.
