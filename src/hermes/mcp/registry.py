from __future__ import annotations

from dataclasses import dataclass

from ..config import BUILTIN_TOOLSETS
from .client import McpTool, StdioMcpClient
from .config import McpConfig, resolve_inputs


SEP = "__"


@dataclass
class ToolSpec:
    qualified_name: str  # "<server>__<tool>"
    server: str
    tool: str
    description: str
    input_schema: dict


class ToolRegistry:
    """Manages MCP clients for the enabled toolsets and routes tool calls."""

    def __init__(self, mcp_config: McpConfig, enabled: list[str]) -> None:
        self._mcp_config = mcp_config
        self._clients: dict[str, StdioMcpClient] = {}
        self._tools: dict[str, ToolSpec] = {}
        self._missing: list[str] = []
        for name in enabled:
            if name in BUILTIN_TOOLSETS:
                continue
            cfg = mcp_config.servers.get(name)
            if not cfg:
                self._missing.append(name)
                continue
            resolved = resolve_inputs(cfg, mcp_config.inputs)
            self._clients[name] = StdioMcpClient(resolved)

    @property
    def missing(self) -> list[str]:
        return list(self._missing)

    def server_names(self) -> list[str]:
        return list(self._clients.keys())

    def discover(self) -> list[ToolSpec]:
        if self._tools:
            return list(self._tools.values())
        for server, client in self._clients.items():
            for t in client.list_tools():
                qn = f"{server}{SEP}{t.name}"
                self._tools[qn] = ToolSpec(
                    qualified_name=qn,
                    server=server,
                    tool=t.name,
                    description=t.description,
                    input_schema=t.input_schema,
                )
        return list(self._tools.values())

    def call(self, qualified_name: str, arguments: dict | None) -> str:
        if not self._tools:
            self.discover()
        spec = self._tools.get(qualified_name)
        if not spec:
            raise KeyError(f"Unknown tool: {qualified_name}")
        return self._clients[spec.server].call_tool(spec.tool, arguments)

    def close(self) -> None:
        for c in self._clients.values():
            c.stop()
