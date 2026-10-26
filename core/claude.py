"""Claude-backed agent loop for the Electron panel (server.py).

Uses the official Anthropic SDK. The zero-arg client resolves credentials from
the environment or an `ant auth login` profile, so no API key needs to live in
the kit ("via your existing setup"). core.tools.TOOLS is already in Anthropic
`input_schema` shape, so it drops straight into the Messages tool-use loop —
no conversion (unlike core.llm, which targets OpenRouter's OpenAI shape).
"""
from __future__ import annotations

from typing import Callable

MODEL = "claude-opus-4-8"


def make_client():
    import anthropic  # local import: only the panel backend needs it
    return anthropic.Anthropic()


def run_claude_loop(client, tools: list, dispatch_fn: Callable[[str, dict], str],
                    system: str, messages: list, log: Callable[[str], None],
                    max_tokens: int = 16000) -> None:
    """Drive Claude until it stops calling tools. `messages` is mutated in place
    so multi-turn history (including thinking blocks) carries across calls.
    `log(text)` receives assistant prose and one-line tool traces."""
    while True:
        resp = client.messages.create(
            model=MODEL, max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            system=system, tools=tools, messages=messages)
        # Preserve full content (incl. thinking blocks) for correct replay.
        messages.append({"role": "assistant", "content": resp.content})
        for block in resp.content:
            if block.type == "text" and block.text.strip():
                log(block.text.strip())
        if resp.stop_reason != "tool_use":
            return
        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                out = dispatch_fn(block.name, block.input or {})
                log(f"  · {block.name} -> {str(out)[:160]}")
                tool_results.append({"type": "tool_result",
                                     "tool_use_id": block.id,
                                     "content": str(out)})
        messages.append({"role": "user", "content": tool_results})
