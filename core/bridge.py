"""Bridge to a running DaVinci Resolve (Studio) via its Python scripting API.

Unlike renderkit's socket bridge, Resolve exposes an in-process module
(`DaVinciResolveScript`, backed by fusionscript.dll). This bridge injects the
required env vars, imports that module, calls scriptapp("Resolve"), and caches
the project/mediaPool/timeline handles. Every tool handler in core.tools takes a
ResolveBridge as its first argument (same convention as renderkit).

Resolve must be running, be the STUDIO edition, and have external scripting
enabled (Preferences -> System -> General -> External scripting using: Local).
"""
from __future__ import annotations

import importlib.util
import os
import sys

from config import RESOLVE_SCRIPT_API, RESOLVE_SCRIPT_LIB


class BridgeError(RuntimeError):
    """Resolve unreachable, wrong edition, or an API call failed."""


_HELP = (
    "Could not connect to DaVinci Resolve. Checklist: (1) Resolve STUDIO is "
    "running with a project open, (2) Preferences -> System -> General -> "
    "'External scripting using' is set to Local, (3) it is the Studio edition "
    "(scripting is Studio-only)."
)


def _load_module():
    """Import DaVinciResolveScript, configuring env + sys.path first."""
    os.environ.setdefault("RESOLVE_SCRIPT_API", RESOLVE_SCRIPT_API)
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", RESOLVE_SCRIPT_LIB)
    modules_dir = os.path.join(RESOLVE_SCRIPT_API, "Modules")
    if modules_dir not in sys.path:
        sys.path.append(modules_dir)
    try:
        import DaVinciResolveScript as bmd  # type: ignore
        return bmd
    except ImportError:
        path = os.path.join(modules_dir, "DaVinciResolveScript.py")
        if not os.path.exists(path):
            raise BridgeError(
                f"Resolve scripting module not found at {path}. Is DaVinci "
                "Resolve Studio installed? Override RESOLVE_SCRIPT_API in .env.")
        spec = importlib.util.spec_from_file_location("DaVinciResolveScript", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["DaVinciResolveScript"] = module
        spec.loader.exec_module(module)
        return module


class ResolveBridge:
    def __init__(self):
        self._resolve = None

    # -- connection -------------------------------------------------------
    @property
    def resolve(self):
        if self._resolve is None:
            bmd = _load_module()
            self._resolve = bmd.scriptapp("Resolve")
            if self._resolve is None:
                raise BridgeError(_HELP)
        return self._resolve

    @property
    def project_manager(self):
        return self.resolve.GetProjectManager()

    @property
    def project(self):
        proj = self.project_manager.GetCurrentProject()
        if proj is None:
            raise BridgeError("No project is open in Resolve — open or create one.")
        return proj

    @property
    def media_pool(self):
        return self.project.GetMediaPool()

    # -- helpers ----------------------------------------------------------
    def current_timeline(self, create_if_missing: bool = False, name: str = "ResolveKit"):
        tl = self.project.GetCurrentTimeline()
        if tl is None and create_if_missing:
            tl = self.new_timeline(name)
        if tl is None:
            raise BridgeError(
                "No timeline is open. Create one first (new_timeline) or open one.")
        return tl

    def new_timeline(self, name: str):
        tl = self.media_pool.CreateEmptyTimeline(name)
        if tl is None:
            raise BridgeError(f"Could not create timeline {name!r} (name taken?).")
        self.project.SetCurrentTimeline(tl)
        return tl

    def ensure_page(self, page: str) -> None:
        """page in media|cut|edit|fusion|color|fairlight|deliver."""
        if self.resolve.GetCurrentPage() != page:
            self.resolve.OpenPage(page)

    def import_media(self, paths: list[str]):
        items = self.media_pool.ImportMedia(paths)
        if not items:
            raise BridgeError(f"Resolve imported nothing from {paths!r}.")
        return items

    def append_clips(self, media_items):
        return self.media_pool.AppendToTimeline(media_items)

    def fps(self) -> float:
        try:
            return float(self.project.GetSetting("timelineFrameRate") or 24)
        except Exception:
            return 24.0
