"""Central configuration and filesystem paths for Qrar.

All paths are resolved relative to this file's location, so the app finds
chats/, assets/ and the Power BI MCP executable correctly regardless of the
directory the user launches `streamlit run` from.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

CHATS_DIR = BASE_DIR / "chats"
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "logo.png"

CHATS_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# --- Power BI MCP server ---
POWERBI_MCP_PATH = os.environ.get(
    "POWERBI_MCP_PATH",
    str(BASE_DIR / "bin" / "powerbi-modeling-mcp.exe"),
)
MCP_REQUEST_TIMEOUT = float(os.environ.get("MCP_REQUEST_TIMEOUT", "60"))

# Arguments passed when launching powerbi-modeling-mcp.exe. --readonly is
# important for a read/query-only app: without it the server allows the AI
# to modify the semantic model (add/remove tables, measures, etc).
MCP_LAUNCH_ARGS = [
    a.strip()
    for a in os.environ.get("MCP_LAUNCH_ARGS", "--start,--readonly").split(",")
    if a.strip()
]

# Real tool name confirmed from the official microsoft/powerbi-modeling-mcp
# README (see: https://github.com/microsoft/powerbi-modeling-mcp).
MCP_DAX_TOOL = os.environ.get("MCP_DAX_TOOL", "dax_query_operations")
# __DAX_QUERY__ is replaced with the JSON-escaped DAX string before parsing,
# so the DAX text can safely contain quotes/newlines. The exact argument
# shape (key names) is NOT documented publicly at the time this was written
# -- use the "list MCP tools" debug panel in the app to inspect this tool's
# real inputSchema and adjust this template if the call fails.
MCP_DAX_ARGUMENTS_TEMPLATE = os.environ.get(
    "MCP_DAX_ARGUMENTS_TEMPLATE", '{"operation": "run", "query": __DAX_QUERY__}'
)

# There is no single documented "get schema" tool; model_operations is the
# best-guess entry point for model/table/column metadata. Confirm and
# adjust via the same debug panel.
MCP_SCHEMA_TOOL = os.environ.get("MCP_SCHEMA_TOOL", "model_operations")
MCP_SCHEMA_ARGUMENTS = os.environ.get("MCP_SCHEMA_ARGUMENTS", '{"operation": "list"}')

# --- AI providers ---
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")

# Order in which providers are tried. The first is primary, the rest are the
# Smart Fallback chain.
PROVIDER_ORDER = [
    p.strip()
    for p in os.environ.get("PROVIDER_ORDER", "ollama,openai,gemini").split(",")
    if p.strip()
]

AI_REQUEST_TIMEOUT = float(os.environ.get("AI_REQUEST_TIMEOUT", "45"))
