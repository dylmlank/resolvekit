"""Shared settings for ResolveKit."""
from __future__ import annotations

import os
from pathlib import Path

OUTPUT_DIR = Path(os.environ.get("RESOLVEKIT_OUTPUT", Path(__file__).parent / "output"))

# --- DaVinci Resolve scripting API location (Windows defaults; override via env) ---
# The bridge injects these into the environment before importing DaVinciResolveScript,
# so no external shell setup is needed.
_PROGRAMDATA = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
RESOLVE_SCRIPT_API = os.environ.get(
    "RESOLVE_SCRIPT_API",
    rf"{_PROGRAMDATA}\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting",
)
RESOLVE_SCRIPT_LIB = os.environ.get(
    "RESOLVE_SCRIPT_LIB",
    r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll",
)

# --- Local WebSocket backend for the Electron panel ---
HOST = os.environ.get("RESOLVEKIT_HOST", "127.0.0.1")
PORT = int(os.environ.get("RESOLVEKIT_PORT", "8765"))

# --- Optional OpenRouter agent path (terminal agent.py). MCP/panel use Claude directly. ---
BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
MODEL = os.environ.get("RESOLVEKIT_MODEL", "")
