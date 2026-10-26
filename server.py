r"""ResolveKit panel backend — a localhost WebSocket bridge between the Electron
Workflow Integration panel (resolve_panel/) and the Claude-driven agent loop.

The panel is UI only; every Resolve action happens here, through core.tools, so
there is a single source of truth. Reasoning runs via the Anthropic SDK
(core.claude) using your existing Claude credentials — no key lives in the kit.

    python server.py        # listens on ws://127.0.0.1:8765 (see config.py)

Protocol (JSON per WebSocket message):
    client -> server : {"type": "chat", "text": "..."}
    server -> client : {"type": "log", "text": "..."}   # assistant prose / tool trace
                       {"type": "error", "text": "..."}
                       {"type": "done"}                  # turn finished
"""
from __future__ import annotations

import asyncio
import json
import os
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

import websockets  # noqa: E402

from config import HOST, PORT  # noqa: E402
from core import TOOLS, ResolveBridge, dispatch  # noqa: E402
from core.claude import make_client, run_claude_loop  # noqa: E402
from core.prompt import SYSTEM  # noqa: E402


async def handle(ws) -> None:
    bridge = ResolveBridge()
    history: list = []
    client = {"c": None}  # boxed so the worker can lazily build + reuse it

    async for raw in ws:
        try:
            msg = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        if msg.get("type") != "chat":
            continue
        text = (msg.get("text") or "").strip()
        if not text:
            continue

        history.append({"role": "user", "content": text})
        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()

        def log(line: str) -> None:
            loop.call_soon_threadsafe(q.put_nowait, {"type": "log", "text": line})

        def work() -> None:
            try:
                if client["c"] is None:
                    client["c"] = make_client()
                run_claude_loop(client["c"], TOOLS,
                                lambda n, a: dispatch(bridge, n, a),
                                SYSTEM, history, log)
            except Exception as e:  # surface any failure to the panel
                loop.call_soon_threadsafe(
                    q.put_nowait, {"type": "error", "text": str(e)})
            finally:
                loop.call_soon_threadsafe(q.put_nowait, {"type": "done"})

        task = asyncio.create_task(asyncio.to_thread(work))
        while True:
            item = await q.get()
            await ws.send(json.dumps(item))
            if item["type"] == "done":
                break
        await task


async def main() -> None:
    print(f"ResolveKit backend listening on ws://{HOST}:{PORT}")
    async with websockets.serve(handle, HOST, PORT):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nbye")
