# ResolveKit

Claude-powered **DaVinci Resolve** assistant — plan and script videos from a topic + mood, get edit suggestions, and generate media and effects, by talking to Claude. Same MCP-server + agent design as the other kits (editkit, renderkit, studiokit), with an in-app **Workflow Integration panel** as the primary surface.

## What it does

- **Plan & script** — turn a topic + mood into an outline/beat-sheet/script, save the doc, spin up a timeline, and lay the beats on it as markers + title cards.
- **Edit suggestions** — read the timeline (auto-transcribe first if needed), propose cuts/pacing as colored marker notes; apply an edit only when you accept it.
- **Generate media** — voiceover via Resolve's built-in TTS; images / b-roll / music via a **pluggable provider** (a labeled-placeholder stub ships today — drop in a real provider later with no tool changes).
- **Generate effects** — insert titles, Fusion titles/compositions, OFX + Fusion generators.

## Architecture

```
Resolve → Workspace → Workflow Integrations → ResolveKit   (Electron panel, UI only)
      │  WS ws://127.0.0.1:8765
      ▼
server.py  ──► core/claude.py (Anthropic SDK, claude-opus-4-8, your existing creds)
      │
      ▼
core/tools.py  ──►  core/bridge.py  ResolveBridge  ──►  DaVinci Resolve (Python API)
```

One Python tool layer (`core/tools.py`), three front-ends onto it:
- **Electron panel** (primary) → `server.py` backend.
- **MCP server** (`mcp_server.py`) → Claude Desktop / Claude Code.
- **Terminal agent** (`agent.py`) → OpenRouter (optional).

The panel never touches Resolve directly — it relays to the backend, which owns every Resolve call.

## Prerequisites

- **DaVinci Resolve Studio** running, with a project open.
- `Preferences → System → General → External scripting using: Local`.
- Some tools (voiceover, transcription) need Resolve's AI models installed.
- Python 3.12 via [`uv`](https://docs.astral.sh/uv/); Node.js (for the panel).

Install deps: `uv run --with-requirements requirements.txt` (or `pip install -r requirements.txt`).

## Setup

### 1. Electron panel (primary)
Copy `resolve_panel/` into Resolve's plugin folder and start the backend:

```
copy  E:\resolvekit\resolve_panel  →  %PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Workflow Integration Plugins\com.dylan.resolvekit
cd resolve_panel && npm install
python server.py            # ws://127.0.0.1:8765
```
Then in Resolve: **Workspace → Workflow Integrations → ResolveKit**. The status pill reads **online** once the backend is up. Reasoning uses your existing Claude credentials (`ant auth login` profile or `ANTHROPIC_API_KEY`) — no key lives in the kit.

### 2. MCP server (Claude Desktop / Claude Code)
```json
"resolvekit": {
  "command": "C:\\Users\\dylan\\.local\\bin\\uv.exe",
  "args": ["run", "--python", "3.12", "--with", "mcp", "--with", "Pillow",
           "python", "E:\\resolvekit\\mcp_server.py"]
}
```

### 3. Terminal agent (optional)
Set `OPENROUTER_API_KEY` + `RESOLVEKIT_MODEL` in `.env`, then:
```
python agent.py "plan a 60s upbeat explainer about cold brew and lay the beats on a new timeline"
```

## Tools (18)

`get_project_info`, `get_timeline_info`, `list_media` · `save_script`, `create_timeline`, `add_marker`, `add_beats` · `transcribe_media`, `add_suggestion_markers`, `delete_timeline_item` · `generate_voiceover`, `generate_image_clip`, `generate_music_clip`, `import_media`, `find_stock` · `insert_title`, `insert_generator`, `insert_fusion_composition`.

## Media providers

`core/providers.py` defines a `MediaProvider` protocol; `StubProvider` writes labeled placeholders (mood-colored image card / silent audio) so the generate → import → timeline pipeline works end-to-end today. Swap in a real image / stock / music provider behind the same interface — `core/tools.py` is unchanged.

Generated docs and media land in `./output/` (override with `RESOLVEKIT_OUTPUT`).
