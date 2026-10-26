"""ResolveKit's capability layer for DaVinci Resolve — shared by the MCP server,
the terminal agent, and the Electron panel backend. Every handler takes a
ResolveBridge first (renderkit convention) and returns a plain status string.

Four capability groups: plan & script, edit suggestions, generate media,
generate effects — plus read/context helpers.
"""
from __future__ import annotations

import json

from config import OUTPUT_DIR
from core.bridge import ResolveBridge, BridgeError
from core.providers import get_provider

# Standard Resolve marker/flag colors.
MARKER_COLORS = ["Blue", "Cyan", "Green", "Yellow", "Red", "Pink", "Purple",
                 "Fuchsia", "Rose", "Lavender", "Sky", "Mint", "Lemon", "Sand",
                 "Cocoa", "Cream"]


def _color(c: str | None, default: str = "Blue") -> str:
    if not c:
        return default
    for m in MARKER_COLORS:
        if m.lower() == c.lower():
            return m
    return default


def _guard(fn):
    """Uniform error handling to a friendly string (mirrors dispatch, but lets
    helpers compose)."""
    try:
        return fn()
    except BridgeError as e:
        return str(e)
    except Exception as e:  # pragma: no cover - defensive
        return f"Resolve API error: {e}"


# --------------------------------------------------------------------------- #
# Read / context
# --------------------------------------------------------------------------- #
def get_project_info(bridge: ResolveBridge) -> str:
    def go():
        p = bridge.project
        tl = p.GetCurrentTimeline()
        info = {
            "project": p.GetName(),
            "timelines": p.GetTimelineCount(),
            "current_timeline": tl.GetName() if tl else None,
            "fps": bridge.fps(),
            "page": bridge.resolve.GetCurrentPage(),
        }
        return json.dumps(info, indent=2)
    return _guard(go)


def get_timeline_info(bridge: ResolveBridge) -> str:
    """Tracks, clips, and markers of the current timeline — the input Claude
    reads to reason about edits."""
    def go():
        tl = bridge.current_timeline()
        out: dict = {"name": tl.GetName(), "start": tl.GetStartFrame(),
                     "end": tl.GetEndFrame(), "video_tracks": {}, "markers": []}
        for i in range(1, tl.GetTrackCount("video") + 1):
            items = tl.GetItemListInTrack("video", i) or []
            out["video_tracks"][i] = [
                {"name": it.GetName(), "start": it.GetStart(),
                 "end": it.GetEnd(), "duration": it.GetDuration()}
                for it in items]
        for frame, m in (tl.GetMarkers() or {}).items():
            out["markers"].append({"frame": frame, "color": m.get("color"),
                                   "name": m.get("name"), "note": m.get("note")})
        return json.dumps(out, indent=2)
    return _guard(go)


def list_media(bridge: ResolveBridge) -> str:
    def go():
        folder = bridge.media_pool.GetRootFolder()
        clips = folder.GetClipList() or []
        names = [c.GetName() for c in clips]
        return json.dumps({"folder": folder.GetName(), "clips": names}, indent=2)
    return _guard(go)


# --------------------------------------------------------------------------- #
# Plan & script
# --------------------------------------------------------------------------- #
def save_script(bridge: ResolveBridge, title: str, content: str) -> str:
    """Persist a generated outline/script as markdown in the output dir."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = "".join(c if c.isalnum() or c in " -_" else "" for c in title).strip()
    path = OUTPUT_DIR / f"{(slug or 'script').replace(' ', '_')}.md"
    path.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
    return f"Script saved -> {path}"


def create_timeline(bridge: ResolveBridge, name: str) -> str:
    def go():
        tl = bridge.new_timeline(name)
        bridge.ensure_page("edit")
        return f"Created and opened timeline '{tl.GetName()}'."
    return _guard(go)


def add_marker(bridge: ResolveBridge, frame: int, name: str, note: str = "",
               color: str = "Blue", duration: int = 1) -> str:
    def go():
        tl = bridge.current_timeline()
        start, end = tl.GetStartFrame(), tl.GetEndFrame()
        f = int(frame)
        # AddMarker frameId is an offset from timeline start (0-based).
        pos = max(0, min(f, max(0, end - start - 1)))
        ok = tl.AddMarker(pos, _color(color), name, note or "", int(duration), "")
        return (f"Marker '{name}' ({_color(color)}) at frame {pos}."
                if ok else f"Resolve rejected marker at frame {pos} "
                           "(timeline may be empty — add clips first).")
    return _guard(go)


def add_beats(bridge: ResolveBridge, beats: list, color: str = "Green") -> str:
    """Place a marker per script beat, evenly spaced across the timeline. Each
    beat is {"name": str, "note": str, "color"?: str, "frame"?: int}."""
    def go():
        tl = bridge.current_timeline()
        start, end = tl.GetStartFrame(), tl.GetEndFrame()
        span = max(1, end - start)
        n = max(1, len(beats))
        placed, failed = 0, 0
        for i, b in enumerate(beats):
            frame = b.get("frame")
            if frame is None:
                frame = int(span * i / n)
            frame = max(0, min(int(frame), span - 1))
            ok = tl.AddMarker(frame, _color(b.get("color"), color),
                              b.get("name", f"Beat {i + 1}"), b.get("note", ""),
                              1, "")
            placed += 1 if ok else 0
            failed += 0 if ok else 1
        msg = f"Placed {placed}/{len(beats)} beat markers."
        if failed:
            msg += " Some failed — timeline may be too short/empty for markers."
        return msg
    return _guard(go)


# --------------------------------------------------------------------------- #
# Edit suggestions
# --------------------------------------------------------------------------- #
def transcribe_media(bridge: ResolveBridge, speaker_detection: bool = True) -> str:
    """Transcribe every clip in the current media-pool folder (Studio AI)."""
    def go():
        folder = bridge.media_pool.GetCurrentFolder()
        ok = folder.TranscribeAudio(speaker_detection)
        return ("Transcription complete (view/edit as subtitles)."
                if ok else "Transcription failed — is the AI Speech model "
                           "installed and are there audio clips in this folder?")
    return _guard(go)


def add_suggestion_markers(bridge: ResolveBridge, suggestions: list) -> str:
    """Write Claude's edit suggestions to the timeline as Yellow marker notes.
    Each suggestion is {"frame": int, "name": str, "note": str, "color"?: str}."""
    return add_beats(bridge, suggestions, color="Yellow")


def delete_timeline_item(bridge: ResolveBridge, track_index: int,
                         item_index: int, ripple: bool = True) -> str:
    """Apply an edit: delete one clip on a video track (opt-in, from a suggestion)."""
    def go():
        tl = bridge.current_timeline()
        items = tl.GetItemListInTrack("video", int(track_index)) or []
        if not (0 <= int(item_index) < len(items)):
            return f"No item at video track {track_index} index {item_index}."
        target = items[int(item_index)]
        ok = tl.DeleteClips([target], bool(ripple))
        return (f"Deleted '{target.GetName()}' ({'ripple' if ripple else 'lift'})."
                if ok else "Delete failed.")
    return _guard(go)


# --------------------------------------------------------------------------- #
# Generate media
# --------------------------------------------------------------------------- #
def generate_voiceover(bridge: ResolveBridge, text: str, voice: str = "Female 1",
                       audio_track: int = 1, add_to_timeline: bool = True,
                       timecode: str = "01:00:00:00") -> str:
    """Resolve built-in Text-to-Speech (Studio AI). Max 350 chars per call."""
    def go():
        settings = {"TextInput": text[:350], "VoiceModel": voice,
                    "AddToTimeline": bool(add_to_timeline), "AudioTrack": int(audio_track)}
        item = bridge.project.GenerateSpeech(settings, timecode)
        if item is None:
            return ("Voiceover generation failed — the AI Speech Generator must "
                    "be installed (DaVinci Resolve > Install AI models).")
        return f"Voiceover generated: '{item.GetName()}' ({voice})."
    return _guard(go)


def generate_image_clip(bridge: ResolveBridge, prompt: str, mood: str = "neutral",
                        add_to_timeline: bool = False) -> str:
    """Generate an image via the active provider (stub by default), import it,
    optionally append it to the timeline."""
    def go():
        path = get_provider().generate_image(prompt, mood)
        items = bridge.import_media([path])
        msg = f"Generated + imported image -> {path}"
        if add_to_timeline:
            bridge.append_clips(items)
            msg += " (appended to timeline)"
        return msg
    return _guard(go)


def generate_music_clip(bridge: ResolveBridge, prompt: str, seconds: float = 10.0,
                        mood: str = "neutral", add_to_timeline: bool = False) -> str:
    def go():
        path = get_provider().generate_music(prompt, seconds, mood)
        items = bridge.import_media([path])
        msg = f"Generated + imported music -> {path}"
        if add_to_timeline:
            bridge.append_clips(items)
            msg += " (appended to timeline)"
        return msg
    return _guard(go)


def import_media(bridge: ResolveBridge, paths: list) -> str:
    def go():
        items = bridge.import_media(list(paths))
        return f"Imported {len(items)} item(s): " + ", ".join(i.GetName() for i in items)
    return _guard(go)


def find_stock(bridge: ResolveBridge, query: str, kind: str = "video") -> str:
    return get_provider().find_stock(query, kind)


# --------------------------------------------------------------------------- #
# Generate effects
# --------------------------------------------------------------------------- #
def insert_title(bridge: ResolveBridge, title_name: str = "Text",
                 fusion: bool = False) -> str:
    """Insert a title generator at the playhead. fusion=True uses a Fusion title
    (e.g. 'Text+'). Set the text in the Inspector afterwards."""
    def go():
        tl = bridge.current_timeline()
        item = (tl.InsertFusionTitleIntoTimeline(title_name) if fusion
                else tl.InsertTitleIntoTimeline(title_name))
        return (f"Inserted {'Fusion ' if fusion else ''}title '{title_name}'."
                if item else f"Could not insert title '{title_name}' "
                             "(check the exact title name).")
    return _guard(go)


def insert_generator(bridge: ResolveBridge, generator_name: str,
                     kind: str = "standard") -> str:
    """Insert a generator: kind = standard | ofx | fusion."""
    def go():
        tl = bridge.current_timeline()
        k = kind.lower()
        if k == "ofx":
            item = tl.InsertOFXGeneratorIntoTimeline(generator_name)
        elif k == "fusion":
            item = tl.InsertFusionGeneratorIntoTimeline(generator_name)
        else:
            item = tl.InsertGeneratorIntoTimeline(generator_name)
        return (f"Inserted {k} generator '{generator_name}'."
                if item else f"Could not insert generator '{generator_name}'.")
    return _guard(go)


def insert_fusion_composition(bridge: ResolveBridge) -> str:
    """Insert an empty Fusion composition (for custom motion graphics/effects)."""
    def go():
        tl = bridge.current_timeline()
        item = tl.InsertFusionCompositionIntoTimeline()
        return ("Inserted Fusion composition (edit it on the Fusion page)."
                if item else "Could not insert Fusion composition.")
    return _guard(go)


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
_HANDLERS = {
    "get_project_info": get_project_info, "get_timeline_info": get_timeline_info,
    "list_media": list_media,
    "save_script": save_script, "create_timeline": create_timeline,
    "add_marker": add_marker, "add_beats": add_beats,
    "transcribe_media": transcribe_media,
    "add_suggestion_markers": add_suggestion_markers,
    "delete_timeline_item": delete_timeline_item,
    "generate_voiceover": generate_voiceover,
    "generate_image_clip": generate_image_clip,
    "generate_music_clip": generate_music_clip,
    "import_media": import_media, "find_stock": find_stock,
    "insert_title": insert_title, "insert_generator": insert_generator,
    "insert_fusion_composition": insert_fusion_composition,
}

_BEAT = {"type": "array", "items": {"type": "object", "properties": {
    "name": {"type": "string"}, "note": {"type": "string"},
    "color": {"type": "string"}, "frame": {"type": "integer"}}}}

TOOLS = [
    {"name": "get_project_info",
     "description": "Current Resolve project: name, timeline count, current timeline, fps, page.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "get_timeline_info",
     "description": "Current timeline's video tracks, clips (name/start/end/duration), and markers. Read this before proposing edits.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "list_media",
     "description": "List clips in the media pool root folder.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "save_script",
     "description": "Save a generated outline/beat-sheet/script as markdown to the output folder.",
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string"}, "content": {"type": "string"}},
      "required": ["title", "content"]}},
    {"name": "create_timeline",
     "description": "Create a new empty timeline and open it on the Edit page.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}},
                      "required": ["name"]}},
    {"name": "add_marker",
     "description": "Add one colored marker (with a note) at a frame offset on the current timeline.",
     "input_schema": {"type": "object", "properties": {
         "frame": {"type": "integer"}, "name": {"type": "string"},
         "note": {"type": "string"}, "color": {"type": "string"},
         "duration": {"type": "integer"}}, "required": ["frame", "name"]}},
    {"name": "add_beats",
     "description": "Place one marker per script beat, evenly spaced across the timeline (or at each beat's optional 'frame'). Use to lay a plan onto the timeline.",
     "input_schema": {"type": "object", "properties": {
         "beats": _BEAT, "color": {"type": "string"}}, "required": ["beats"]}},
    {"name": "transcribe_media",
     "description": "Transcribe all clips in the current media-pool folder using Resolve's AI (Studio). Needed before transcript-based edit suggestions.",
     "input_schema": {"type": "object", "properties": {
         "speaker_detection": {"type": "boolean"}}, "required": []}},
    {"name": "add_suggestion_markers",
     "description": "Write edit suggestions to the timeline as Yellow marker notes. Each item: {frame, name, note, color?}.",
     "input_schema": {"type": "object", "properties": {"suggestions": _BEAT},
                      "required": ["suggestions"]}},
    {"name": "delete_timeline_item",
     "description": "Apply an edit: delete one clip on a video track (ripple by default). Use only when the user accepts a suggestion.",
     "input_schema": {"type": "object", "properties": {
         "track_index": {"type": "integer"}, "item_index": {"type": "integer"},
         "ripple": {"type": "boolean"}}, "required": ["track_index", "item_index"]}},
    {"name": "generate_voiceover",
     "description": "Generate voiceover with Resolve's built-in Text-to-Speech (Studio AI). Max 350 chars. VoiceModel e.g. 'Female 1','Male 1'.",
     "input_schema": {"type": "object", "properties": {
         "text": {"type": "string"}, "voice": {"type": "string"},
         "audio_track": {"type": "integer"}, "add_to_timeline": {"type": "boolean"},
         "timecode": {"type": "string"}}, "required": ["text"]}},
    {"name": "generate_image_clip",
     "description": "Generate an image (via the active media provider — stub placeholder by default), import it, optionally append to the timeline.",
     "input_schema": {"type": "object", "properties": {
         "prompt": {"type": "string"}, "mood": {"type": "string"},
         "add_to_timeline": {"type": "boolean"}}, "required": ["prompt"]}},
    {"name": "generate_music_clip",
     "description": "Generate a music/audio bed (via provider — silent stub by default), import, optionally append.",
     "input_schema": {"type": "object", "properties": {
         "prompt": {"type": "string"}, "seconds": {"type": "number"},
         "mood": {"type": "string"}, "add_to_timeline": {"type": "boolean"}},
      "required": ["prompt"]}},
    {"name": "import_media",
     "description": "Import file paths into the current media-pool folder.",
     "input_schema": {"type": "object", "properties": {
         "paths": {"type": "array", "items": {"type": "string"}}}, "required": ["paths"]}},
    {"name": "find_stock",
     "description": "Find stock footage/music via the active provider (stub by default). kind = video|image|music.",
     "input_schema": {"type": "object", "properties": {
         "query": {"type": "string"}, "kind": {"type": "string"}}, "required": ["query"]}},
    {"name": "insert_title",
     "description": "Insert a title generator at the playhead. fusion=True for a Fusion title (e.g. 'Text+'). Set the text in the Inspector after.",
     "input_schema": {"type": "object", "properties": {
         "title_name": {"type": "string"}, "fusion": {"type": "boolean"}}, "required": []}},
    {"name": "insert_generator",
     "description": "Insert a generator at the playhead. kind = standard|ofx|fusion (e.g. solid color, noise, gradients).",
     "input_schema": {"type": "object", "properties": {
         "generator_name": {"type": "string"}, "kind": {"type": "string"}},
      "required": ["generator_name"]}},
    {"name": "insert_fusion_composition",
     "description": "Insert an empty Fusion composition for custom motion graphics/effects.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
]


def dispatch(bridge: ResolveBridge, name: str, arguments: dict) -> str:
    handler = _HANDLERS.get(name)
    if handler is None:
        return f"Unknown tool: {name}"
    try:
        return handler(bridge, **(arguments or {}))
    except Exception as e:
        return f"Error in {name}: {e}"
