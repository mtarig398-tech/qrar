"""High-level Power BI operations built on top of the MCP stdio client."""
from __future__ import annotations

import json

import config

from .mcp_client import MCPClient


class PowerBIConnector:
    def __init__(self):
        self._client = MCPClient(config.POWERBI_MCP_PATH)
        self._started = False

    def ensure_started(self) -> None:
        if not self._started:
            self._client.start()
            self._started = True

    def get_schema(self) -> dict:
        self.ensure_started()
        raw = self._client.call_tool(
            config.MCP_SCHEMA_TOOL, {}, timeout=config.MCP_REQUEST_TIMEOUT
        )
        return _safe_json(raw)

    def execute_dax(self, dax_query: str) -> dict:
        self.ensure_started()
        raw = self._client.call_tool(
            config.MCP_DAX_TOOL,
            {"query": dax_query},
            timeout=config.MCP_REQUEST_TIMEOUT,
        )
        return _safe_json(raw)

    def list_available_tools(self) -> list[dict]:
        self.ensure_started()
        return self._client.list_tools()

    def close(self) -> None:
        self._client.stop()
        self._started = False


def _safe_json(raw) -> dict:
    """MCP tool results usually arrive as text; tolerate both str and dict."""
    if isinstance(raw, dict):
        return raw
    if raw is None:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"raw": raw}
