"""The 5 experimental conditions, expressed as guidance hooks.

A guidance hook is `(message, transcript) -> (final_message, record)` where `record`
carries the verdict + whether a repair happened, for logging. The base agent calls
the hook right before delivering a user-directed message. All methods share the same
base agent; they differ ONLY here -- that's what keeps the ablation clean.

`action_verifier` is intentionally a no-op on the guidance channel: it represents the
prior-art paradigm (verify the agent's own tool calls), so on the agent->user channel
it leaves guidance untouched -- demonstrating it cannot address guidance-induced
failures. (Its tool-call checks, if implemented, live in the agent loop, not here.)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .verifier.guidance_verifier import (
    VerifierVerdict, verify_and_repair, verify_guidance, build_revise_feedback,
)

METHODS = ("vanilla", "self_verify", "action_verifier", "guidance_verify",
           "guidance_verify_repair", "guidance_verify_selfrevise", "placebo_revise",
           "epistemic_repair")


@dataclass
class HookRecord:
    verdict: VerifierVerdict | None = None
    repaired: bool = False
    revised: bool = False
    action: str = "keep"


@dataclass
class HookAction:
    """What the installer should do with the audited message.

    kind="keep"    -> deliver the message unchanged.
    kind="replace" -> deliver `text` instead (legacy external repair rewrite).
    kind="revise"  -> have the BASE agent regenerate, given `feedback` (self-revision).
    """
    kind: str = "keep"
    text: str | None = None
    feedback: str | None = None
    record: HookRecord = field(default_factory=HookRecord)


def make_hook(method: str, rubric, verifier_call):
    """Build the guidance hook for `method`. `verifier_call` is the (API) llm_call
    used by the verifier/repair; `rubric` is the cached GuidanceRule list."""
    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}; choose from {METHODS}")

    def identity(message, transcript):
        return HookAction("keep", record=HookRecord(action="keep"))

    if method in ("vanilla", "action_verifier"):
        return identity

    if method == "epistemic_repair":
        return _make_epistemic_repair_hook()

    # detect-only arms (optionally with the legacy external-repair rewrite)
    if method in ("self_verify", "guidance_verify", "guidance_verify_repair"):
        grounded = method != "self_verify"
        enable_repair = method == "guidance_verify_repair"

        def hook(message, transcript):
            final, verdict, repaired = verify_and_repair(
                message, transcript, rubric, verifier_call,
                grounded=grounded, enable_repair=enable_repair,
            )
            if repaired:
                return HookAction("replace", text=final,
                                  record=HookRecord(verdict=verdict, repaired=True, action="replace"))
            return HookAction("keep", record=HookRecord(verdict=verdict, action="keep"))

        return hook

    # self-revision arms: verify (procedure-grounded), and on a violation hand the verdict
    # back to the BASE agent to regenerate. placebo_revise fires on the SAME trigger but with
    # content-free feedback, isolating the resampling effect from the verifier's signal.
    placebo = method == "placebo_revise"

    def hook(message, transcript):
        verdict = verify_guidance(message, transcript, rubric, verifier_call,
                                  grounded=True, prompt_mode="procedural")
        if verdict.ok:
            return HookAction("keep", record=HookRecord(verdict=verdict, action="keep"))
        feedback = ("Please rephrase your previous message to the user."
                    if placebo else build_revise_feedback(verdict, rubric))
        return HookAction("revise", feedback=feedback,
                          record=HookRecord(verdict=verdict, revised=True, action="revise"))

    return hook


@dataclass(frozen=True)
class EpistemicRule:
    id: str
    action: str
    triggers: tuple[str, ...]
    evidence: tuple[str, ...]
    diagnostic: str
    diagnostic_goal: str


_EPISTEMIC_RULES = (
    EpistemicRule(
        id="E_SIM",
        action="reseat the SIM card",
        triggers=(
            r"\breseat_sim_card\b",
            r"\bre-?seat\b.{0,80}\bsim\b",
            r"\bremove\b.{0,80}\bsim\b.{0,80}\breinsert\b",
            r"\breinsert\b.{0,80}\bsim\b",
        ),
        evidence=(r"\bcheck_sim_status\b", r"\bno sim card detected\b", r"\bsim card status:\s*missing\b"),
        diagnostic="check_sim_status",
        diagnostic_goal="confirm whether the SIM is actually missing or inactive",
    ),
    EpistemicRule(
        id="E_AIRPLANE",
        action="toggle airplane mode",
        triggers=(
            r"\btoggle_airplane_mode\b",
            r"\bturn (?:off|on)\b.{0,30}\bairplane mode\b",
            r"\bairplane mode\b.{0,30}\b(?:off|on)\b",
        ),
        evidence=(r"\bcheck_network_status\b", r"\bcheck_status_bar\b", r"\bairplane mode:\s*(?:on|off)\b"),
        diagnostic="check_network_status",
        diagnostic_goal="confirm the current airplane-mode and cellular state",
    ),
    EpistemicRule(
        id="E_DATA",
        action="toggle mobile data",
        triggers=(
            r"\btoggle_data\b",
            r"\bturn (?:off|on)\b.{0,30}\bmobile data\b",
            r"\b(?:enable|disable)\b.{0,30}\bmobile data\b",
        ),
        evidence=(r"\bcheck_network_status\b", r"\bmobile data enabled:\s*(?:yes|no)\b", r"\bdata disabled\b"),
        diagnostic="check_network_status",
        diagnostic_goal="confirm whether mobile data is currently enabled",
    ),
    EpistemicRule(
        id="E_ROAMING",
        action="toggle data roaming on the phone",
        triggers=(
            r"\btoggle_roaming\b",
            r"\b(?:turn|toggle|switch)\b.{0,30}\b(?:data )?roaming\b",
            r"\b(?:enable|disable)\b.{0,30}\b(?:data )?roaming\b.{0,40}\b(?:phone|device)\b",
        ),
        evidence=(r"\bcheck_network_status\b", r"\bdata roaming enabled:\s*(?:yes|no)\b", r"\broaming_enabled\b"),
        diagnostic="check_network_status",
        diagnostic_goal="confirm current device roaming status",
    ),
    EpistemicRule(
        id="E_DATA_SAVER",
        action="toggle data saver mode",
        triggers=(
            r"\btoggle_data_saver_mode\b",
            r"\bturn (?:off|on)\b.{0,30}\bdata saver\b",
            r"\b(?:enable|disable)\b.{0,30}\bdata saver\b",
        ),
        evidence=(r"\bcheck_data_restriction_status\b", r"\bdata saver\b.{0,40}\b(?:on|off|enabled|disabled)\b"),
        diagnostic="check_data_restriction_status",
        diagnostic_goal="confirm whether data saver or a data restriction is active",
    ),
    EpistemicRule(
        id="E_NETWORK_MODE",
        action="change the network mode preference",
        triggers=(
            r"\bset_network_mode_preference\b",
            r"\bchange\b.{0,40}\bnetwork mode\b",
            r"\bset\b.{0,40}\bnetwork mode\b",
        ),
        evidence=(r"\bcheck_network_mode_preference\b", r"\bnetwork mode preference\b"),
        diagnostic="check_network_mode_preference",
        diagnostic_goal="confirm the current network mode preference",
    ),
    EpistemicRule(
        id="E_APN",
        action="reset or change APN settings",
        triggers=(
            r"\breset_apn_settings\b",
            r"\bset_apn_settings\b",
            r"\breset\b.{0,40}\bapn\b",
            r"\bchange\b.{0,40}\bapn\b",
        ),
        evidence=(r"\bcheck_apn_settings\b", r"\bmmsc\b", r"\bapn settings\b.{0,80}\b(?:missing|incorrect|wrong|empty)\b"),
        diagnostic="check_apn_settings",
        diagnostic_goal="confirm the current APN and MMSC configuration",
    ),
    EpistemicRule(
        id="E_WIFI_CALLING",
        action="toggle Wi-Fi Calling",
        triggers=(
            r"\btoggle_wifi_calling\b",
            r"\bset_wifi_calling\b",
            r"\bturn (?:off|on)\b.{0,30}\bwi-?fi calling\b",
            r"\b(?:enable|disable)\b.{0,30}\bwi-?fi calling\b",
        ),
        evidence=(r"\bcheck_wifi_calling_status\b", r"\bwi-?fi calling is currently\b", r"\bwi-?fi calling\b.{0,30}\b(?:on|off)\b"),
        diagnostic="check_wifi_calling_status",
        diagnostic_goal="confirm whether Wi-Fi Calling is currently enabled",
    ),
    EpistemicRule(
        id="E_PERMISSION",
        action="grant app permissions",
        triggers=(
            r"\bgrant_app_permission\b",
            r"\bgrant\b.{0,50}\bpermission",
            r"\benable\b.{0,50}\bpermission",
            r"\ballow\b.{0,50}\bpermission",
        ),
        evidence=(r"\bcheck_app_permissions\b", r"\bpermissions?\b.{0,80}\b(?:granted|denied|not granted|missing)\b"),
        diagnostic="check_app_permissions",
        diagnostic_goal="confirm the app's current permissions",
    ),
    EpistemicRule(
        id="E_REBOOT",
        action="reboot the device",
        triggers=(r"\breboot_device\b", r"\breboot\b.{0,30}\b(?:device|phone)\b", r"\brestart\b.{0,30}\b(?:device|phone)\b"),
        evidence=(r"\breset_apn_settings\b", r"\bapn settings will reset at reboot\b", r"\breboot required\b"),
        diagnostic="check_network_status",
        diagnostic_goal="confirm the current device state before rebooting",
    ),
)


def _has_any(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) for pattern in patterns)


def _epistemic_verdict(message: str, transcript: str) -> tuple[VerifierVerdict, str | None]:
    """Check only epistemic readiness for state-changing user actions.

    This verifier does not infer hidden telecom state and does not decide whether an
    action is globally correct. It only asks whether the conversation already contains
    explicit diagnostic evidence for the state-changing user action being requested.
    """
    for rule in _EPISTEMIC_RULES:
        if not _has_any(rule.triggers, message):
            continue
        if _has_any(rule.evidence, transcript):
            return VerifierVerdict(ok=True, rationale=f"{rule.id}: prerequisite evidence found"), None
        rationale = (
            f"{rule.id}: message asks the user to {rule.action}, but the transcript "
            f"does not show evidence to {rule.diagnostic_goal}."
        )
        feedback = (
            f"Before changing settings, please run the {rule.diagnostic} diagnostic and "
            "tell me the result. This will confirm the current state before we decide on "
            f"the next action."
        )
        return VerifierVerdict(ok=False, violated_rule_ids=[rule.id], rationale=rationale), feedback
    return VerifierVerdict(ok=True, rationale="No state-changing user action detected"), None


def _make_epistemic_repair_hook():
    def hook(message, transcript):
        verdict, replacement = _epistemic_verdict(message, transcript)
        if verdict.ok or replacement is None:
            return HookAction("keep", record=HookRecord(verdict=verdict, action="keep"))
        return HookAction("replace", text=replacement,
                          record=HookRecord(verdict=verdict, repaired=True, action="replace"))

    return hook


# --- mutation-gating (precision fix) ---------------------------------------
# Empirically gtrepair over-triggers: it repairs harmless messages (confirmations,
# diagnostic reads, explanations) and damages already-correct guidance. A cheap LLM
# gate runs the full verify+repair ONLY on messages that instruct a state-CHANGING
# device action -- the causally critical turns (cf. SABER's mutation-gating).

_GATE_PROMPT = """You gate a telecom customer-service agent's message to a user.

Answer YES only if the message INSTRUCTS THE USER TO CHANGE A SETTING or perform a
state-changing action on their device, e.g.: turn on/off airplane mode; toggle mobile
data / roaming / wi-fi / wi-fi calling / data saver; re-seat or insert the SIM; change
or reset APN settings; change the network mode; change an app's permissions.

Answer NO if the message only asks the user to CHECK / READ / REPORT something, asks a
question, explains, confirms, acknowledges, or is small talk.

Message:
\"\"\"{message}\"\"\"

Answer with exactly one word: YES or NO."""


def make_mutation_gate(gate_call):
    """Return `is_mutating(message)->bool`. `gate_call` is a cheap llm_call(prompt)->str
    (e.g. verifier client with max_tokens=5)."""
    def is_mutating(message: str) -> bool:
        out = (gate_call(_GATE_PROMPT.format(message=message)) or "").strip().upper()
        return out.startswith("YES") or "YES" in out[:6]
    return is_mutating


def make_gated_hook(inner_hook, gate_call):
    """Wrap a verify+repair hook so it fires ONLY on mutating-instruction messages;
    everything else passes through untouched (precision fix). The gate's own tokens are
    billed through `gate_call`'s client, so total verifier cost stays honest."""
    gate = make_mutation_gate(gate_call)

    def hook(message, transcript):
        if not gate(message):
            return message, HookRecord()        # skip: pass through unchanged
        return inner_hook(message, transcript)

    return hook
