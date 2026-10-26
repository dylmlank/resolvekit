r"""ResolveKit MCP server — plan/script, edit, and generate media+effects in
DaVinci Resolve as MCP tools for Claude Desktop / Claude Code. Each tool wraps a
core.tools handler (shared with agent.py and the Electron panel backend).

Resolve Studio must be running with External scripting enabled.

claude_desktop_config.json:

    "resolvekit": {
      "command": "C:\\Users\\dylan\\.local\\bin\\uv.exe",
      "args": ["run", "--python", "3.12", "--with", "mcp", "--with", "Pillow",
               "python", "E:\\resolvekit\\mcp_server.py"]
    }
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from core import ResolveBridge
import core.tools as T

mcp = FastMCP("resolvekit")
bridge = ResolveBridge()


def _kw(**kw):
    return {k: v for k, v in kw.items() if v is not None}


# --- read / context ---------------------------------------------------------
@mcp.tool()
def get_project_info() -> str:
    """Current Resolve project: name, timeline count, current timeline, fps, page."""
    return T.get_project_info(bridge)


@mcp.tool()
def get_timeline_info() -> str:
    """Current timeline's video tracks, clips, and markers. Read before proposing edits."""
    return T.get_timeline_info(bridge)


@mcp.tool()
def list_media() -> str:
    """List clips in the media pool root folder."""
    return T.list_media(bridge)


# --- plan & script ----------------------------------------------------------
@mcp.tool()
def save_script(title: str, content: str) -> str:
    """Save a generated outline/beat-sheet/script as markdown to the output folder."""
    return T.save_script(bridge, title, content)


@mcp.tool()
def create_timeline(name: str) -> str:
    """Create a new empty timeline and open it on the Edit page."""
    return T.create_timeline(bridge, name)


@mcp.tool()
def add_marker(frame: int, name: str, note: str = "", color: str = "Blue",
               duration: int = 1) -> str:
    """Add one colored marker (with a note) at a frame offset on the current timeline."""
    return T.add_marker(bridge, frame, name, note=note, color=color, duration=duration)


@mcp.tool()
def add_beats(beats: list, color: str = "Green") -> str:
    """Place one marker per script beat, evenly spaced across the timeline (or at
    each beat's optional 'frame'). Each beat: {name, note, color?, frame?}."""
    return T.add_beats(bridge, beats, color=color)


# --- edit suggestions -------------------------------------------------------
@mcp.tool()
def transcribe_media(speaker_detection: bool = True) -> str:
    """Transcribe all clips in the current media-pool folder (Studio AI)."""
    return T.transcribe_media(bridge, speaker_detection)


@mcp.tool()
def add_suggestion_markers(suggestions: list) -> str:
    """Write edit suggestions to the timeline as Yellow marker notes.
    Each item: {frame, name, note, color?}."""
    return T.add_suggestion_markers(bridge, suggestions)


@mcp.tool()
def delete_timeline_item(track_index: int, item_index: int, ripple: bool = True) -> str:
    """Apply an edit: delete one clip on a video track (ripple by default)."""
    return T.delete_timeline_item(bridge, track_index, item_index, ripple)


# --- generate media ---------------------------------------------------------
@mcp.tool()
def generate_voiceover(text: str, voice: str = "Female 1", audio_track: int = 1,
                       add_to_timeline: bool = True,
                       timecode: str = "01:00:00:00") -> str:
    """Generate voiceover with Resolve's built-in TTS (Studio AI). Max 350 chars."""
    return T.generate_voiceover(bridge, text, voice=voice, audio_track=audio_track,
                                add_to_timeline=add_to_timeline, timecode=timecode)


@mcp.tool()
def generate_image_clip(prompt: str, mood: str = "neutral",
                        add_to_timeline: bool = False) -> str:
    """Generate an image via the active media provider (stub by default), import it,
    optionally append to the timeline."""
    return T.generate_image_clip(bridge, prompt, mood=mood, add_to_timeline=add_to_timeline)


@mcp.tool()
def generate_music_clip(prompt: str, seconds: float = 10.0, mood: str = "neutral",
                        add_to_timeline: bool = False) -> str:
    """Generate a music/audio bed via provider (silent stub by default), import,
    optionally append."""
    return T.generate_music_clip(bridge, prompt, seconds=seconds, mood=mood,
                                 add_to_timeline=add_to_timeline)


@mcp.tool()
def import_media(paths: list) -> str:
    """Import file paths into the current media-pool folder."""
    return T.import_media(bridge, paths)


@mcp.tool()
def find_stock(query: str, kind: str = "video") -> str:
    """Find stock footage/music via the active provider (stub by default)."""
    return T.find_stock(bridge, query, kind)


# --- generate effects -------------------------------------------------------
@mcp.tool()
def insert_title(title_name: str = "Text", fusion: bool = False) -> str:
    """Insert a title generator at the playhead. fusion=True for a Fusion title (e.g. 'Text+')."""
    return T.insert_title(bridge, title_name, fusion)


@mcp.tool()
def insert_generator(generator_name: str, kind: str = "standard") -> str:
    """Insert a generator at the playhead. kind = standard|ofx|fusion."""
    return T.insert_generator(bridge, generator_name, kind)


@mcp.tool()
def insert_fusion_composition() -> str:
    """Insert an empty Fusion composition for custom motion graphics/effects."""
    return T.insert_fusion_composition(bridge)


if __name__ == "__main__":
    mcp.run()
