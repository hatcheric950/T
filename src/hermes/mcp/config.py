from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from ..config import mcp_config_paths


_INPUT_RE = re.compile(r"\$\{input:([a-zA-Z0-9_\-]+)\}")
_input_cache: dict[str, str] = {}


@dataclass
class McpInput:
    id: str
    description: str = ""
    type: str = "promptString"


@dataclass
class McpServerConfig:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    type: str = "stdio"


@dataclass
class McpConfig:
    servers: dict[str, McpServerConfig] = field(default_factory=dict)
    inputs: list[McpInput] = field(default_factory=list)


def load_mcp_config(paths: list[Path] | None = None) -> McpConfig:
    """Load mcp.json from the first existing path. Repo-local wins."""
    paths = paths if paths is not None else mcp_config_paths()
    for p in paths:
        if p.exists():
            return _parse(json.loads(p.read_text()))
    return McpConfig()


def _parse(raw: dict) -> McpConfig:
    inputs = [McpInput(**{k: v for k, v in i.items() if k in {"id", "description", "type"}})
              for i in raw.get("inputs", [])]
    servers: dict[str, McpServerConfig] = {}
    for name, spec in (raw.get("servers") or {}).items():
        servers[name] = McpServerConfig(
            name=name,
            command=spec["command"],
            args=list(spec.get("args", [])),
            env=dict(spec.get("env", {})),
            type=spec.get("type", "stdio"),
        )
    return McpConfig(servers=servers, inputs=inputs)


def resolve_inputs(server: McpServerConfig, inputs: list[McpInput],
                   interactive: bool | None = None) -> McpServerConfig:
    """Return a new server config with ${input:id} placeholders resolved in env+args."""
    by_id = {i.id: i for i in inputs}

    def sub(s: str) -> str:
        def repl(m: re.Match) -> str:
            iid = m.group(1)
            return _resolve_input(iid, by_id.get(iid), interactive)
        return _INPUT_RE.sub(repl, s)

    return McpServerConfig(
        name=server.name,
        command=server.command,
        args=[sub(a) for a in server.args],
        env={k: sub(v) for k, v in server.env.items()},
        type=server.type,
    )


def _resolve_input(iid: str, spec: McpInput | None, interactive: bool | None) -> str:
    if iid in _input_cache:
        return _input_cache[iid]
    env_key = f"HERMES_INPUT_{iid.upper().replace('-', '_')}"
    if env_key in os.environ:
        _input_cache[iid] = os.environ[env_key]
        return _input_cache[iid]
    is_tty = interactive if interactive is not None else sys.stdin.isatty()
    if not is_tty:
        raise RuntimeError(
            f"MCP input '{iid}' is required. Set {env_key} or run interactively."
        )
    prompt = (spec.description if spec and spec.description else f"Enter {iid}") + ": "
    try:
        import getpass
        value = getpass.getpass(prompt)
    except Exception:
        value = input(prompt)
    _input_cache[iid] = value
    return value
