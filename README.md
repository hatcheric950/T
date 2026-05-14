# hermes

A multi-provider chat CLI agent.

## Install

```bash
pip install -e .
```

## Usage

```bash
# Start an interactive session (default)
hermes

# Single query mode (non-interactive)
hermes chat -q "Hello"

# With a specific model
hermes chat --model "anthropic/claude-sonnet-4-6"

# With a specific provider
hermes chat --provider nous        # Use Nous Portal
hermes chat --provider openrouter  # Force OpenRouter

# With specific toolsets
hermes chat --toolsets "web,terminal,skills"

# Start with one or more skills preloaded
hermes -s hermes-agent-dev,github-auth
hermes chat -s github-pr-workflow -q "open a draft PR"

# Resume previous sessions
hermes --continue             # Resume the most recent CLI session (-c)
hermes --resume <session_id>  # Resume a specific session by ID (-r)

# Verbose mode (debug output)
hermes chat --verbose

# Isolated git worktree (for running multiple agents in parallel)
hermes -w                         # Interactive mode in worktree
hermes -w -q "Fix issue #123"     # Single query in worktree
```

## Environment

- `ANTHROPIC_API_KEY` — Anthropic provider
- `OPENROUTER_API_KEY` — OpenRouter provider
- `NOUS_API_KEY` — Nous Portal provider
- `HERMES_HOME` — override config/sessions/skills root (default `~/.hermes`)

## Layout

- `~/.hermes/sessions/<id>.json` — persisted conversations
- `~/.hermes/skills/<name>.md` — local skill prompts loaded via `-s`
- `~/.hermes/mcp.json` (or repo-local `./.hermes/mcp.json`) — MCP server
  definitions exposed as `--toolsets <name>`

## MCP toolsets

Any server defined in `mcp.json` becomes available as a toolset. Example
(Hostinger):

```bash
mkdir -p ~/.hermes && cat > ~/.hermes/mcp.json <<'JSON'
{
  "inputs": [
    { "id": "api_token", "description": "Hostinger API token" }
  ],
  "servers": {
    "hostinger": {
      "type": "stdio",
      "command": "npx",
      "args": ["hostinger-api-mcp@latest"],
      "env": { "API_TOKEN": "${input:api_token}" }
    }
  }
}
JSON

export HERMES_INPUT_API_TOKEN=...   # skip the interactive prompt
hermes chat --toolsets hostinger -q "list my domains"
```

`${input:<id>}` placeholders resolve in this order:
1. env var `HERMES_INPUT_<ID>` (uppercased, `-` → `_`)
2. interactive prompt (TTY only; cached for the session)

Currently supported transport: `stdio`. Tool calls work with
`--provider anthropic` (default).
