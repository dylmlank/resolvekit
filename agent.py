r"""ResolveKit standalone terminal agent — describe a video and let a model plan,
script, and build it in a running DaVinci Resolve project. Orchestrates the same
tools the MCP server exposes.

    # in E:\resolvekit\.env (or the environment):
    #   OPENROUTER_API_KEY=sk-or-v1-...
    #   RESOLVEKIT_MODEL=openai/gpt-oss-120b:free   (any tool-capable OpenRouter model)
    python agent.py "plan a 60s upbeat explainer about cold brew coffee and lay the beats on a new timeline"

The MCP server (Claude Desktop/Code) and the Electron panel drive Claude directly
and need no key; this terminal path uses OpenRouter (core.llm) for convenience.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _load_env() -> None:
    env = Path(__file__).parent / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()

from core import TOOLS, ResolveBridge, dispatch  # noqa: E402
from core.llm import make_client, run_loop  # noqa: E402
from core.prompt import SYSTEM  # noqa: E402


def main() -> int:
    client = make_client()
    bridge = ResolveBridge()
    history: list = []

    def drive(text: str) -> None:
        history.append({"role": "user", "content": text})
        run_loop(client, TOOLS, lambda n, a: dispatch(bridge, n, a),
                 SYSTEM, history, print, max_tokens=8192)

    if len(sys.argv) > 1:
        drive(" ".join(sys.argv[1:]))
        return 0
    print("ResolveKit agent — describe the video (Ctrl+C to quit).")
    try:
        while True:
            text = input("\n> ").strip()
            if text:
                drive(text)
    except (KeyboardInterrupt, EOFError):
        print("\nbye")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
