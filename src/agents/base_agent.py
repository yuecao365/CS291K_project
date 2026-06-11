"""Guidance interception layer (no tau2 import -> unit-testable).

Confirmed tau2 facts this is built on:
  * The agent's turn method is `generate_next_message(message, state) -> (AssistantMessage, state)`.
  * An assistant turn is user-directed iff it has text `content` and is NOT a tool call.
  * The orchestrator type-checks the agent (HalfDuplexAgent), so we must NOT replace the
    agent object -- we patch its bound method in place, preserving identity/type.

`install_guidance_hook` is the integration entry point used with tau2. `GuidedAgent`
is a generic wrapper kept for unit tests / non-tau2 use.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable

# Hook signature: (message_text, transcript) -> (final_text, record)
GuidanceHook = Callable[[str, str], tuple[str, Any]]


def is_user_directed(msg: Any) -> bool:
    """True iff `msg` is a natural-language reply to the user (no tool calls).
    Mirrors tau2's AssistantMessage.is_tool_call() (tool_calls is not None)."""
    content = getattr(msg, "content", None)
    is_tool = msg.is_tool_call() if hasattr(msg, "is_tool_call") else bool(getattr(msg, "tool_calls", None))
    return bool(content) and not is_tool


def _msg_line(m: Any) -> str | None:
    role = getattr(m, "role", None) or type(m).__name__
    tool_messages = getattr(m, "tool_messages", None)
    if tool_messages:
        lines = [_msg_line(tm) for tm in tool_messages]
        return "\n".join(ln for ln in lines if ln)
    content = getattr(m, "content", None)
    tcs = getattr(m, "tool_calls", None)
    if content:
        requestor = getattr(m, "requestor", None)
        tag = f"{role}[{requestor}]" if requestor else role
        return f"{tag}: {content}"
    if tcs:
        names = ", ".join(
            f"{getattr(tc, 'name', '?')}({getattr(tc, 'requestor', '?')})"
            for tc in tcs
        )
        return f"{role} -> tool_call({names})"
    return None


def render_transcript(messages: Iterable[Any], max_chars: int = 6000) -> str:
    lines = [ln for ln in (_msg_line(m) for m in (messages or [])) if ln]
    text = "\n".join(lines)
    return text[-max_chars:] if len(text) > max_chars else text


def _assistant_of(ret: Any) -> Any:
    """generate_next_message returns (AssistantMessage, state); tolerate a bare message."""
    return ret[0] if isinstance(ret, tuple) and ret else ret


def _normalize_action(out: Any):
    """Accept either a HookAction-like object (has `.kind`) or the legacy (text, record)
    tuple, and return (kind, text, feedback, record)."""
    if hasattr(out, "kind"):
        return out.kind, getattr(out, "text", None), getattr(out, "feedback", None), getattr(out, "record", None)
    if isinstance(out, tuple) and len(out) == 2:           # legacy (final_text, record)
        return "replace", out[0], None, out[1]
    return "keep", None, None, None


def _revise(orig, feedback: str, state: Any):
    """One self-revision round (Reflexion/SABER-style): inject the verifier critique as a
    SYSTEM/reflection turn -- NOT as a fake user message -- and let the BASE agent regenerate.
    Impersonating the user (the previous implementation) caused role confusion and a
    'ask the user to re-confirm' derail; a system-attributed reflection is the faithful form.
    Returns the new generate_next_message return value, or None on failure (fail-open: keep the
    draft). Runs inside one orchestrator turn -> no step inflation."""
    if not feedback or state is None:
        return None
    try:
        from tau2.data_model.message import SystemMessage
        return orig(SystemMessage(role="system", content=feedback), state)
    except Exception:                                       # noqa: BLE001 -- never break the episode
        return None


def install_guidance_hook(agent: Any, hook: GuidanceHook | None, *, max_revisions: int = 3) -> list:
    """Patch `agent.generate_next_message` in place so user-directed messages pass through
    `hook` before the orchestrator routes them to the user. Returns a list that fills with
    one record per intercepted guidance turn (for the violation decomposition).

    No-op (returns []) when `hook` is None -> use for the `vanilla`/`action_verifier` arms.

    Self-revision is bounded per EPISODE to prevent reflection livelock: each rule is nagged
    at most once, and at most `max_revisions` revisions fire in total. Without this, a verifier
    that re-flags the same rule every turn drives the agent into a MAX_STEPS loop."""
    records: list = []
    if hook is None:
        return records
    convo: list = []
    revised_rules: set = set()         # rule ids already nagged this episode
    budget = [max_revisions]           # remaining revisions this episode (list = mutable closure)
    orig = agent.generate_next_message  # bound method

    def patched(*args, **kwargs):
        incoming = args[0] if args else kwargs.get("message")
        if incoming is not None:
            convo.append(incoming)
        ret = orig(*args, **kwargs)
        msg = _assistant_of(ret)
        if is_user_directed(msg):
            kind, text, feedback, record = _normalize_action(hook(msg.content, render_transcript(convo)))
            if kind == "replace" and text is not None:
                msg.content = text
            elif kind == "revise":
                v = getattr(record, "verdict", None)
                rids = set(getattr(v, "violated_rule_ids", []) or [])
                already = bool(rids) and rids <= revised_rules
                if budget[0] > 0 and not already:
                    state = kwargs.get("state", args[1] if len(args) > 1 else None)
                    new_ret = _revise(orig, feedback, state)
                    if new_ret is not None:                # adopt the regenerated message
                        ret = new_ret
                        msg = _assistant_of(ret)
                        budget[0] -= 1
                        revised_rules.update(rids)         # in-place: don't rebind the closure var
                    elif record is not None:               # regeneration failed -> kept draft
                        record.revised = False; record.action = "revise_failed"
                elif record is not None:                   # suppressed: budget spent / rule repeated
                    record.revised = False; record.action = "revise_suppressed"
            if record is not None:
                records.append(record)
        convo.append(msg)
        return ret

    agent.generate_next_message = patched  # instance attr shadows the class method
    return records


# --- generic wrapper kept for tests / non-tau2 use --------------------------

GENERATE_METHOD_NAMES = ("generate_next_message", "get_response", "respond", "step", "act")


class GuidedAgent:
    """Transparent wrapper applying `guidance_hook` to user-directed messages. Prefer
    `install_guidance_hook` with tau2 (preserves the agent's type for orchestrator checks)."""

    def __init__(self, inner: Any, guidance_hook: GuidanceHook | None,
                 generate_method_names: tuple[str, ...] = GENERATE_METHOD_NAMES):
        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "_hook", guidance_hook)
        object.__setattr__(self, "_gen_names", generate_method_names)
        object.__setattr__(self, "records", [])

    def __getattr__(self, name: str):
        attr = getattr(self._inner, name)
        if self._hook is not None and name in self._gen_names and callable(attr):
            def wrapped(*args, **kwargs):
                ret = attr(*args, **kwargs)
                msg = _assistant_of(ret)
                if is_user_directed(msg):
                    history = next((a for a in list(args) + list(kwargs.values()) if isinstance(a, list)), [])
                    kind, text, _feedback, record = _normalize_action(
                        self._hook(msg.content, render_transcript(history)))
                    if kind == "replace" and text is not None:   # this wrapper cannot regenerate
                        msg.content = text
                    if record is not None:
                        self.records.append(record)
                return ret
            return wrapped
        return attr

    def __setattr__(self, name, value):
        setattr(self._inner, name, value)
