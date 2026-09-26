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
# Names of the tools exposed by the MCP server, as reported by tools/list.
# Adjust these to match the actual server if they differ.
MCP_SCHEMA_TOOL = os.environ.get("MCP_SCHEMA_TOOL", "get_model_schema")
MCP_DAX_TOOL = os.environ.get("MCP_DAX_TOOL", "execute_dax_query")

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
