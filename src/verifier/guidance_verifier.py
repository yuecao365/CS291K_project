"""Online guidance verifier + repair loop (the core contribution).

Hook point: just BEFORE an agent message that contains user-directed guidance is
delivered to the user simulator. We score that message against the cached
GuidanceRules (+ the observable transcript), and if a hard rule is predicted to be
violated we run one bounded repair round. There is no "block": the user will act, so
the only lever is replacing the guidance with a corrected version.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from ..utils.json_parse import parse_json
from .rubric_extractor import GuidanceRule, render_rubric

VERIFY_PROMPT = """You are auditing ONE message a customer-service AGENT is about to send the USER.
Flag it ONLY if it clearly and concretely causes the user to VIOLATE a specific rule below.

Be conservative. Do NOT flag a message when:
- it only states facts, confirms status, asks which line/number, or reports findings (no instruction to act);
- the rule's "applies when" condition is NOT actually true in this conversation;
- the concern is stylistic, "could be more thorough", or a missing nicety.
A rule is violated only if the message INSTRUCTS the user to do the prohibited thing AND that rule's
trigger condition genuinely holds here. When in doubt, return ok=true.

RULES (each: [id][severity] rule (applies when: ...)):
{rubric}

CONVERSATION SO FAR:
{transcript}

AGENT MESSAGE TO AUDIT:
{message}

Return ONLY JSON: {{"ok": bool, "violated_rule_ids": [<ids of rules ACTUALLY violated>], "rationale": "..."}}.
If violated_rule_ids would be empty, you MUST return ok=true.
"""

# ITEM #2: "is the (conservative) VERIFY PROMPT the constraint on improvement?"
# High-recall variant: flips the default's precision bias toward catching more. Selected at
# runtime with env var VERIFY_MODE=hirecall (default = the conservative VERIFY_PROMPT above).
# If pass@1 does NOT rise under this prompt, the conservative prompt was not the bottleneck.
VERIFY_PROMPT_HIRECALL = """You are auditing ONE message a customer-service AGENT is about to send the USER.
Your job is to CATCH any message that could lead the user to violate a rule below or to act on an
unconfirmed precondition. Err on the side of flagging.

Flag the message if ANY of the following hold:
- it instructs the user to do something a rule prohibits, OR
- it instructs the user to act WITHOUT first confirming a precondition the rule requires, OR
- the relevant rule's "applies when" condition plausibly holds and the message does not respect it.
Only return ok=true when you are confident no listed rule is at risk.

RULES (each: [id][severity] rule (applies when: ...)):
{rubric}

CONVERSATION SO FAR:
{transcript}

AGENT MESSAGE TO AUDIT:
{message}

Return ONLY JSON: {{"ok": bool, "violated_rule_ids": [<ids of rules at risk>], "rationale": "..."}}.
"""

# PROCEDURE-grounded variant (the "choice A" verifier). Instead of judging whether a hidden
# world fact holds (outcome), it judges whether the agent followed the required ORDER that is
# fully observable in the transcript: a remediation/action must be preceded by the diagnostic
# or confirmation step the rule names. This needs NO world state -> no grounding gap.
VERIFY_PROMPT_PROCEDURAL = """You are auditing ONE message a customer-service AGENT is about to send the USER.
Each rule below requires a diagnostic/confirmation step to happen BEFORE a given action. Judge
ONLY from the conversation whether the order was followed.

Flag the message ONLY if BOTH hold:
- it INSTRUCTS the user to perform the action a rule governs (not merely asks a question,
  states a fact, confirms status, or reports a finding), AND
- the CONVERSATION SO FAR does NOT show the required prior step (the diagnostic check or
  confirmation that rule names) was already performed.
If the required prior step already appears earlier in the conversation, do NOT flag it.
When in doubt, return ok=true.

RULES (each: [id][severity] required-order rule (applies when: ...)):
{rubric}

CONVERSATION SO FAR:
{transcript}

AGENT MESSAGE TO AUDIT:
{message}

Return ONLY JSON: {{"ok": bool, "violated_rule_ids": [<ids whose required prior step is missing>], "rationale": "..."}}.
If violated_rule_ids would be empty, you MUST return ok=true.
"""

# Ablation baseline: same shape, but NO policy checklist (isolates policy grounding).
SELF_VERIFY_PROMPT = """A customer-service AGENT is about to tell the USER to do something.
Judge whether this instruction is correct and safe given the conversation.

CONVERSATION SO FAR:
{transcript}

AGENT MESSAGE TO VERIFY:
{message}

Return ONLY JSON: {{"ok": bool, "violated_rule_ids": [], "rationale": "..."}}.
"""

REPAIR_PROMPT = """Your previous instruction to the user would violate policy.
Violated rules:
{violations}

Rewrite ONLY the instruction so it complies (e.g. add the missing precondition/step or change
what you ask the user to do). Keep it natural and minimal. Do not mention this correction.

Original instruction:
{message}
"""


@dataclass
class VerifierVerdict:
    ok: bool
    violated_rule_ids: list[str] = field(default_factory=list)
    rationale: str = ""


def _parse_verdict(raw: str) -> VerifierVerdict:
    """Parse the verifier's JSON verdict. DEFENSIVE: a verifier that emits malformed JSON
    must never crash the base episode -- on any parse failure we fail OPEN (ok=True, no
    repair), i.e. behave as if no violation was found, and record the raw text for debugging."""
    try:
        data = parse_json(raw)
    except (ValueError, Exception):                # noqa: BLE001
        return VerifierVerdict(ok=True, rationale=f"[unparseable verdict] {raw[:200]}")
    if not isinstance(data, dict):
        return VerifierVerdict(ok=True, rationale=f"[non-dict verdict] {str(data)[:200]}")
    ids = [str(x).strip().strip("[]") for x in (data.get("violated_rule_ids") or [])]
    ids = [x for x in ids if x]
    ok = bool(data.get("ok", True))
    # Precision guard: "not ok" with NO concrete rule id == repairing on vibes. Treat as ok.
    if not ids:
        ok = True
    return VerifierVerdict(ok=ok, violated_rule_ids=ids, rationale=str(data.get("rationale", "")))


def verify_guidance(message, transcript, rubric, llm_call, *, grounded=True,
                    prompt_mode=None) -> VerifierVerdict:
    """Score one agent->user message. `grounded=False` runs the SETS-style ablation
    with no policy checklist. `prompt_mode="procedural"` uses the order-checking prompt
    (choice A: judge whether the required prior step appears in the transcript).

    Only HARD rules can trigger a violation: soft rules (R10-R17) are "allowed but
    suboptimal", so flagging them just churns the guidance with no compliance gain
    (a major source of the false-positive storm in the first run)."""
    if grounded:
        if prompt_mode == "procedural":
            template = VERIFY_PROMPT_PROCEDURAL
        elif os.environ.get("VERIFY_MODE") == "hirecall":
            template = VERIFY_PROMPT_HIRECALL
        else:
            template = VERIFY_PROMPT
        prompt = template.format(rubric=render_rubric(rubric, hard_only=True),
                                 transcript=transcript, message=message)
    else:
        prompt = SELF_VERIFY_PROMPT.format(transcript=transcript, message=message)
    verdict = _parse_verdict(llm_call(prompt))
    if grounded:                                   # drop any soft/unknown ids the model invented
        hard_ids = {r.id for r in rubric if r.severity == "hard"}
        verdict.violated_rule_ids = [i for i in verdict.violated_rule_ids if i in hard_ids]
        if not verdict.violated_rule_ids:
            verdict.ok = True
    return verdict


def repair_guidance(message, verdict, rubric, llm_call) -> str:
    """One bounded repair round; returns the corrected instruction to deliver instead."""
    by_id = {r.id: r for r in rubric}
    lines = [f"- {by_id[rid].text}" if rid in by_id else f"- {rid}" for rid in verdict.violated_rule_ids]
    violations = "\n".join(lines) or f"- {verdict.rationale}"
    return llm_call(REPAIR_PROMPT.format(violations=violations, message=message)).strip()


def build_revise_feedback(verdict, rubric) -> str:
    """Turn a failed verdict into a short, rule-cited critique handed back to the BASE agent
    (self-revision). Unlike `repair_guidance`, this does NOT rewrite the message -- the agent,
    which holds the full policy, regenerates the instruction itself."""
    by_id = {r.id: r for r in rubric}
    lines = []
    for rid in verdict.violated_rule_ids:
        r = by_id.get(rid)
        lines.append(f"- [{rid}] {r.text}" if r is not None else f"- {rid}")
    rules = "\n".join(lines) or f"- {verdict.rationale}"
    return ("[Policy reflection — not from the user] Your previous message instructs the user "
            "to act before the required diagnostic step was performed:\n" + rules +
            "\nResend a single corrected message that FIRST directs the user to run the relevant "
            "non-mutating diagnostic read (e.g. check the current APN settings / app permissions / "
            "roaming status), rather than asking them to confirm or to act blindly. "
            "Do not mention this reflection to the user.")


def verify_and_repair(message, transcript, rubric, llm_call, *, grounded=True, enable_repair=True):
    """Verify; if not ok and repair enabled, repair once. Returns
    (final_message, verdict, repaired: bool). The verdict is always kept for analysis,
    even when we fall back to the original message."""
    verdict = verify_guidance(message, transcript, rubric, llm_call, grounded=grounded)
    if verdict.ok or not enable_repair:
        return message, verdict, False
    fixed = repair_guidance(message, verdict, rubric, llm_call)
    return (fixed or message), verdict, bool(fixed)
