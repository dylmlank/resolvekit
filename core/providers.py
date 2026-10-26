"""Pluggable media-generation providers.

Provides three levels:
1. StubProvider: labeled placeholders (no external deps)
2. LocalProvider: PIL images + WAV audio (pillow+numpy only)
3. Real providers: Replicate, RunwayML, stock APIs (drop in behind this interface)
"""
from __future__ import annotations

import wave
from pathlib import Path
from typing import Protocol

from config import OUTPUT_DIR

_MOOD_RGB = {
    "upbeat": (255, 196, 0), "energetic": (255, 90, 40), "calm": (90, 150, 200),
    "serene": (120, 190, 180), "dark": (30, 30, 40), "moody": (60, 50, 90),
    "warm": (220, 140, 90), "cool": (80, 130, 190), "epic": (150, 40, 60),
    "playful": (255, 120, 190), "neutral": (120, 120, 120),
}

_MOOD_TONE = {  # hertz for simple tone generation
    "upbeat": 800, "energetic": 600, "calm": 300,
    "serene": 250, "dark": 40, "moody": 100,
    "warm": 400, "cool": 600, "epic": 80,
    "playful": 900, "neutral": 440,
}


def _mood_color(mood: str) -> tuple[int, int, int]:
    return _MOOD_RGB.get((mood or "neutral").lower().strip(), (120, 120, 120))


def _mood_freq(mood: str) -> int:
    return _MOOD_TONE.get((mood or "neutral").lower().strip(), 440)


def _slug(text: str, n: int = 40) -> str:
    keep = "".join(c if c.isalnum() or c in " -_" else "" for c in text)
    return (keep.strip().replace(" ", "_")[:n] or "media").lower()


class MediaProvider(Protocol):
    def generate_image(self, prompt: str, mood: str = "neutral") -> str: ...
    def generate_music(self, prompt: str, seconds: float = 10.0,
                       mood: str = "neutral") -> str: ...
    def find_stock(self, query: str, kind: str = "video") -> str: ...


class StubProvider:
    """Writes labeled placeholders (no external APIs)."""

    name = "stub"

    def __init__(self, out_dir: Path = OUTPUT_DIR):
        self.out = Path(out_dir)
        self.out.mkdir(parents=True, exist_ok=True)

    def generate_image(self, prompt: str, mood: str = "neutral") -> str:
        try:
            from PIL import Image, ImageDraw
            path = self.out / f"stub_img_{_slug(prompt)}.png"
            img = Image.new("RGB", (1920, 1080), _mood_color(mood))
            d = ImageDraw.Draw(img)
            d.text((60, 60), f"[{mood}] {prompt}"[:120], fill=(255, 255, 255))
            d.text((60, 1000), "PLACEHOLDER — swap in a real image provider",
                    fill=(230, 230, 230))
            img.save(path)
            return str(path)
        except ImportError:
            # Fallback: write a text file as a placeholder
            path = self.out / f"stub_img_{_slug(prompt)}.txt"
            path.write_text(f"[{mood}] {prompt}\n\nPLACEHOLDER — PIL not installed")
            return f"[error] PIL not installed; placeholder created at {path}"

    def generate_music(self, prompt: str, seconds: float = 10.0,
                       mood: str = "neutral") -> str:
        path = self.out / f"stub_music_{_slug(prompt)}.wav"
        rate = 44100
        frames = int(rate * max(0.5, seconds))
        with wave.open(str(path), "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(b"\x00\x00" * frames)
        return str(path)

    def find_stock(self, query: str, kind: str = "video") -> str:
        return (f"[stub] No stock provider configured. Would search {kind} for "
                f"{query!r}. Wire a real provider in core/providers.py.")


class LocalProvider:
    """PIL images + WAV audio. Requires: pillow, numpy."""

    name = "local"

    def __init__(self, out_dir: Path = OUTPUT_DIR):
        self.out = Path(out_dir)
        self.out.mkdir(parents=True, exist_ok=True)

    def generate_image(self, prompt: str, mood: str = "neutral") -> str:
        """Create a gradient image with text overlay matching the mood."""
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            return "[error] PIL not installed; install pillow for image generation"

        path = self.out / f"img_{_slug(prompt)}.png"
        rgb = _mood_color(mood)

        # Create a gradient from mood color to black
        img = Image.new("RGB", (1920, 1080), rgb)
        pixels = img.load()
        for y in range(1080):
            fade = 1.0 - (y / 1080.0)
            r = int(rgb[0] * fade)
            g = int(rgb[1] * fade)
            b = int(rgb[2] * fade)
            for x in range(1920):
                pixels[x, y] = (r, g, b)

        # Add text
        d = ImageDraw.Draw(img)
        d.text((100, 400), f"{prompt[:60]}", fill=(255, 255, 255))
        d.text((100, 500), f"Mood: {mood}", fill=(200, 200, 200))

        img.save(path)
        return str(path)

    def generate_music(self, prompt: str, seconds: float = 10.0,
                       mood: str = "neutral") -> str:
        """Generate a simple tone-based WAV file."""
        try:
            import numpy as np
        except ImportError:
            return "[error] numpy not installed; install numpy for audio generation"

        path = self.out / f"music_{_slug(prompt)}.wav"
        rate = 44100
        duration = max(0.5, min(60, seconds))  # clamp 0.5-60s
        frames = int(rate * duration)

        # Generate a sine wave at the mood frequency
        freq = _mood_freq(mood)
        t = np.linspace(0, duration, frames, dtype=np.float32)
        wave_data = (np.sin(2 * np.pi * freq * t) * 0.3).astype(np.int16)

        with wave.open(str(path), "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(wave_data.tobytes())

        return str(path)

    def find_stock(self, query: str, kind: str = "video") -> str:
        """Return a placeholder; upgrade to Pexels/Pixabay API later."""
        return (f"[local] Stock footage not yet implemented. "
                f"Would search {kind} for: {query!r}")


def get_provider() -> MediaProvider:
    """Single place to swap the active provider.

    Set RESOLVEKIT_PROVIDER=local|stub in .env to choose.
    Default: local (PIL+numpy if available, else stub).
    """
    import os
    choice = os.environ.get("RESOLVEKIT_PROVIDER", "local").lower()
    try:
        if choice == "local":
            return LocalProvider()
    except ImportError:
        pass  # fall through to stub
    return StubProvider()
