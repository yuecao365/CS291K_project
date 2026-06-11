"""Offline tests for the tau2-independent interception layer (base_agent.py).

Uses fake message/agent objects shaped like tau2's (content + tool_calls), so we
verify GuidedAgent rewrites ONLY user-directed messages and leaves tool-call turns
and delegation untouched -- no tau2 install needed.

Run:  python tests/test_agent_offline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents.base_agent import GuidedAgent, is_user_directed, render_transcript


class Msg:
    def __init__(self, role, content=None, tool_calls=None):
        self.role, self.content, self.tool_calls = role, content, tool_calls


class ToolCall:
    def __init__(self, name, arguments):
        self.name, self.arguments = name, arguments


class FakeAgent:
    """Returns a scripted sequence of assistant messages; also has an unrelated
    attribute/method to confirm transparent delegation."""
    def __init__(self, outbox):
        self.outbox = list(outbox)
        self.calls = 0

    def generate_next_message(self, history):   # name in GENERATE_METHOD_NAMES
        self.calls += 1
        return self.outbox.pop(0)

    def reset(self):
        return "reset-ok"


UPPER = lambda text, transcript: (text.upper(), ("REC", transcript))  # noqa: E731


def test_is_user_directed():
    assert is_user_directed(Msg("assistant", "hello"))
    assert not is_user_directed(Msg("assistant", None, [ToolCall("get_x", "{}")]))
    assert not is_user_directed(Msg("assistant", "", None))


def test_render_transcript_includes_roles_and_tools():
    msgs = [Msg("user", "hi"), Msg("assistant", None, [ToolCall("lookup", "{'q':1}")])]
    t = render_transcript(msgs)
    assert "user: hi" in t and "tool_call" in t and "lookup" in t


def test_guidedagent_rewrites_only_user_directed():
    agent = FakeAgent([Msg("assistant", "do a factory reset"),          # user-directed -> hooked
                       Msg("assistant", None, [ToolCall("get_plan", "{}")])])  # tool call -> untouched
    g = GuidedAgent(agent, UPPER)
    m1 = g.generate_next_message([Msg("user", "help")])
    assert m1.content == "DO A FACTORY RESET"          # rewritten
    m2 = g.generate_next_message([Msg("user", "ok")])
    assert m2.content is None and m2.tool_calls         # tool call left alone
    assert len(g.records) == 1                          # only one interception


def test_guidedagent_delegates_other_attrs():
    agent = FakeAgent([Msg("assistant", "x")])
    g = GuidedAgent(agent, UPPER)
    assert g.reset() == "reset-ok"                      # passthrough method
    g.generate_next_message([])
    assert agent.calls == 1                             # inner agent really invoked


def test_guidedagent_none_hook_is_passthrough():
    agent = FakeAgent([Msg("assistant", "leave me")])
    g = GuidedAgent(agent, None)
    assert g.generate_next_message([]).content == "leave me"
    assert g.records == []


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all agent offline tests passed")
