from __future__ import annotations

import asyncio
import os
import threading
from concurrent.futures import Future
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .config import McpServerConfig


@dataclass
class McpTool:
    name: str
    description: str
    input_schema: dict


class _Loop:
    """A background asyncio loop shared by all MCP clients in the process."""

    _instance: "_Loop | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, name="hermes-mcp-loop", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    @classmethod
    def get(cls) -> "_Loop":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def submit(self, coro) -> Future:
        return asyncio.run_coroutine_threadsafe(coro, self.loop)


class StdioMcpClient:
    """Spawns one MCP server over stdio and exposes sync list_tools / call_tool."""

    def __init__(self, cfg: McpServerConfig) -> None:
        self.cfg = cfg
        self._loop = _Loop.get()
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._loop.submit(self._start_async()).result()
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        try:
            self._loop.submit(self._stop_async()).result(timeout=5)
        except Exception:
            pass
        self._started = False

    def list_tools(self) -> list[McpTool]:
        self.start()
        return self._loop.submit(self._list_tools_async()).result()

    def call_tool(self, name: str, arguments: dict | None) -> str:
        self.start()
        return self._loop.submit(self._call_tool_async(name, arguments or {})).result()

    async def _start_async(self) -> None:
        self._stack = AsyncExitStack()
        env = {**os.environ, **self.cfg.env}
        params = StdioServerParameters(command=self.cfg.command, args=self.cfg.args, env=env)
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()

    async def _stop_async(self) -> None:
        if self._stack:
            await self._stack.aclose()
        self._stack = None
        self._session = None

    async def _list_tools_async(self) -> list[McpTool]:
        assert self._session
        result = await self._session.list_tools()
        return [
            McpTool(name=t.name, description=t.description or "",
                    input_schema=t.inputSchema or {"type": "object", "properties": {}})
            for t in result.tools
        ]

    async def _call_tool_async(self, name: str, arguments: dict) -> str:
        assert self._session
        result = await self._session.call_tool(name, arguments)
        chunks: list[str] = []
        for block in result.content:
            text = getattr(block, "text", None)
            if text is not None:
                chunks.append(text)
            else:
                chunks.append(str(block))
        out = "\n".join(chunks)
        if result.isError:
            out = f"[tool error] {out}"
        return out
