"""Policy document -> guidance rubric (one-time, per domain, cached).

We do NOT verify free-form policy text at runtime. Instead, once per domain we
distill the policy doc into a checklist of *guidance-relevant* rules: things the
agent must (not) tell the user to do, and the preconditions/order required before
a user action. The runtime verifier checks the agent's guidance against this
small, stable checklist.

Analogue of DeepVerifier's rubric, but sourced from the domain policy (not a failure
taxonomy) and scoped to the agent->user channel.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ..utils.json_parse import parse_json


@dataclass
class GuidanceRule:
    id: str
    text: str                 # human-readable rule
    applies_when: str         # natural-language trigger condition
    severity: str = "hard"    # "hard" (policy violation) | "soft" (suboptimal)


RUBRIC_EXTRACTION_PROMPT = """You are converting a customer-service POLICY document into a
checklist of rules that constrain what an AGENT may INSTRUCT a USER to do (the user, not the
agent, performs some actions). Output only rules that are checkable against a transcript.

For each rule give: a short id, the rule text, the condition under which it applies, and
severity ("hard" = instructing the user this way violates policy; "soft" = allowed but
suboptimal). Ignore rules about the agent's own tool calls.

POLICY:
{policy_text}

Return ONLY JSON: a list of objects {{"id","text","applies_when","severity"}}.
"""


def extract_rubric(policy_text: str, llm_call) -> list[GuidanceRule]:
    """Call an LLM once to turn `policy_text` into GuidanceRules.

    `llm_call(prompt:str) -> str` is injected so this stays provider-agnostic and
    testable. The result SHOULD be spot-checked by hand (cheap, removes a confound),
    then cached with `save_rubric`.
    """
    raw = llm_call(RUBRIC_EXTRACTION_PROMPT.format(policy_text=policy_text))
    data = parse_json(raw)
    if isinstance(data, dict):                      # tolerate {"rules": [...]}
        data = data.get("rules", next((v for v in data.values() if isinstance(v, list)), []))
    rules: list[GuidanceRule] = []
    for item in data:
        rules.append(GuidanceRule(
            id=str(item.get("id", f"r{len(rules)}")),
            text=str(item.get("text", "")).strip(),
            applies_when=str(item.get("applies_when", "")).strip(),
            severity=str(item.get("severity", "hard")).strip().lower() or "hard",
        ))
    if not rules:
        raise ValueError("Rubric extraction produced no rules; check the policy text / model output.")
    return rules


def save_rubric(rules: list[GuidanceRule], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(r) for r in rules], indent=2, ensure_ascii=False), encoding="utf-8")


def load_rubric(path: str | Path) -> list[GuidanceRule]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [GuidanceRule(**item) for item in data]


def render_rubric(rules: list[GuidanceRule], hard_only: bool = False) -> str:
    """Compact bullet list for prompting the verifier."""
    out = []
    for r in rules:
        if hard_only and r.severity != "hard":
            continue
        out.append(f"- [{r.id}][{r.severity}] {r.text} (applies when: {r.applies_when})")
    return "\n".join(out)
