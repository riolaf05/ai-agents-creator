"""Integrazione con server MCP (Model Context Protocol).

Uso tipico:

```python
from ai_agents_creator.mcp import MCPServerConfig, load_mcp_tools

servers = [
    MCPServerConfig(
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "./data"],
    ),
]
tools = load_mcp_tools(servers)          # lista di Tool già pronti per un Agent
agent = Agent(name="fs_agent", ..., tools=tools)
```

Nota: questo modulo usa l'SDK ufficiale ``mcp`` (stdio transport). Ogni
chiamata a tool apre una sessione breve, esegue la call e la chiude; è
semplice ma sufficiente per i tool di lettura/scrittura tipici. Per carichi
più alti si può tenere una sessione persistente.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from ..core.tools import Tool

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None


def load_mcp_tools(servers: list[MCPServerConfig]) -> list[Tool]:
    """Scopre tutti i tool esposti dai server MCP indicati e li wrappa in ``Tool``."""
    all_tools: list[Tool] = []
    for srv in servers:
        try:
            descriptors = asyncio.run(_list_tools(srv))
        except Exception as exc:  # noqa: BLE001
            logger.warning("MCP server '%s' non disponibile: %s", srv.name, exc)
            continue
        for desc in descriptors:
            all_tools.append(_wrap_mcp_tool(srv, desc))
    return all_tools


async def _list_tools(server: MCPServerConfig) -> list[dict[str, Any]]:
    # Import lazy per non esplodere se il pacchetto mcp non è installato.
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=server.command, args=server.args, env=server.env
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            resp = await session.list_tools()
            return [
                {
                    "name": t.name,
                    "description": t.description or t.name,
                    "input_schema": t.inputSchema or {"type": "object", "properties": {}},
                }
                for t in resp.tools
            ]


def _wrap_mcp_tool(server: MCPServerConfig, descriptor: dict[str, Any]) -> Tool:
    tool_name = f"{server.name}__{descriptor['name']}"

    def runner(**kwargs: Any) -> str:
        return asyncio.run(_call_tool(server, descriptor["name"], kwargs))

    return Tool(
        name=tool_name,
        description=f"[MCP:{server.name}] {descriptor['description']}",
        input_schema=descriptor["input_schema"],
        func=runner,
        metadata={"mcp_server": server.name, "mcp_tool": descriptor["name"]},
    )


async def _call_tool(server: MCPServerConfig, tool_name: str, arguments: dict[str, Any]) -> str:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=server.command, args=server.args, env=server.env
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)

    parts: list[str] = []
    for item in result.content:
        text = getattr(item, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts) if parts else "(no content)"
