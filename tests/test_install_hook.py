"""Offline test for install_guidance_hook (the tau2 integration entry point).

Simulates tau2's stateful agent: generate_next_message(message, state) -> (msg, state).
Confirms (a) only user-directed turns are rewritten, (b) the agent OBJECT is unchanged
(same identity/type -> orchestrator type-checks still pass), (c) records accumulate.

Run:  python tests/test_install_hook.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents.base_agent import install_guidance_hook


class Msg:
    def __init__(self, role, content=None, tool_calls=None):
        self.role, self.content, self.tool_calls = role, content, tool_calls

    def is_tool_call(self):
        return self.tool_calls is not None


class StatefulAgent:
    """Shaped like tau2's LLMAgent: (message, state) -> (AssistantMessage, state)."""
    def __init__(self, outbox):
        self.outbox = list(outbox)

    def generate_next_message(self, message, state):
        return self.outbox.pop(0), state


def hook(text, transcript):
    return f"[FIXED] {text}", type("R", (), {"verdict": type("V", (), {"ok": False})()})()


def test_install_hook_rewrites_and_preserves_identity():
    agent = StatefulAgent([Msg("assistant", "do factory reset"),
                           Msg("assistant", None, [object()])])   # tool call
    before_type = type(agent)
    records = install_guidance_hook(agent, hook)

    m1, _ = agent.generate_next_message(Msg("user", "help"), state={})
    assert m1.content == "[FIXED] do factory reset"
    m2, _ = agent.generate_next_message(Msg("user", "ok"), state={})
    assert m2.content is None                          # tool call untouched
    assert len(records) == 1
    assert type(agent) is before_type                  # same object/type preserved


def test_install_hook_none_is_noop():
    agent = StatefulAgent([Msg("assistant", "leave me")])
    records = install_guidance_hook(agent, None)
    m, _ = agent.generate_next_message(Msg("user", "x"), state={})
    assert m.content == "leave me" and records == []


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all install-hook tests passed")
