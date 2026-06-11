"""Offline tests: everything that does NOT need the live benchmark or a real model.

Run:  python -m pytest tests/ -q     (or: python tests/test_offline.py)

Uses a scripted FakeLLM so the verifier/rubric pipeline is exercised end-to-end
with zero network calls. This is the green-before-AutoDL safety net.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.json_parse import parse_json
from src.verifier.rubric_extractor import extract_rubric, render_rubric, save_rubric, load_rubric
from src.verifier.guidance_verifier import verify_guidance, verify_and_repair
from src.methods import make_hook, METHODS
from src.eval.metrics import TrialResult, summarize, pass_hat_k


class FakeLLM:
    """Returns scripted responses by matching a substring of the prompt."""
    def __init__(self, rules):
        self.rules = rules

    def __call__(self, prompt: str) -> str:
        if "converting a customer-service POLICY" in prompt:
            return "```json\n" + _rules_json + "\n```"          # rubric extraction
        if "Rewrite ONLY the instruction" in prompt:
            return "First, please back up your data; once that's done, perform a factory reset."
        # verification: flag a violation only when the risky phrase appears AND the policy
        # checklist is present. Grounded verify prompts embed the rubric -> "applies when:"
        # appears; the ungrounded SELF_VERIFY prompt does not, so it never flags.
        if "factory reset" in prompt.lower() and "applies when:" in prompt:
            return '{"ok": false, "violated_rule_ids": ["r0"], "rationale": "no backup confirmed"}'
        return '{"ok": true, "violated_rule_ids": [], "rationale": "looks fine"}'


_rules_json = (
    '[{"id":"r0","text":"Confirm data backup before instructing a factory reset",'
    '"applies_when":"about to instruct a factory reset","severity":"hard"},'
    '{"id":"r1","text":"Never instruct the user to share their password",'
    '"applies_when":"any","severity":"hard"}]'
)


def test_json_parse_tolerates_fences_and_prose():
    assert parse_json("here you go:\n```json\n{\"ok\": true}\n``` thanks")["ok"] is True
    assert parse_json('[1, 2, 3,]') == [1, 2, 3]            # trailing comma


def test_rubric_extract_and_roundtrip(tmp_path=None):
    llm = FakeLLM(None)
    rules = extract_rubric("dummy policy", llm)
    assert {r.id for r in rules} == {"r0", "r1"}
    assert "factory reset" in render_rubric(rules).lower()
    out = Path("results/_test_rubric.json")
    save_rubric(rules, out)
    assert [r.id for r in load_rubric(out)] == ["r0", "r1"]
    out.unlink()


def test_verify_flags_and_repairs():
    llm = FakeLLM(None)
    rules = extract_rubric("dummy", llm)
    bad = "Go ahead and do a factory reset now."
    v = verify_guidance(bad, "transcript", rules, llm, grounded=True)
    assert v.ok is False and "r0" in v.violated_rule_ids
    fixed, verdict, repaired = verify_and_repair(bad, "t", rules, llm, grounded=True, enable_repair=True)
    assert repaired and "back up" in fixed.lower()


def test_self_verify_ablation_is_ungrounded():
    llm = FakeLLM(None)
    rules = extract_rubric("dummy", llm)
    # without the checklist the FakeLLM cannot see CHECKLIST -> returns ok=true
    v = verify_guidance("Go ahead and do a factory reset now.", "t", rules, llm, grounded=False)
    assert v.ok is True


def test_all_methods_build_hooks():
    llm = FakeLLM(None)
    rules = extract_rubric("dummy", llm)
    msg = "Go ahead and do a factory reset now."
    for m in METHODS:
        hook = make_hook(m, rules, llm)
        action = hook(msg, "transcript")
        assert action.kind in ("keep", "replace", "revise")
        rec = action.record
        if m == "guidance_verify_repair":
            assert action.kind == "replace" and action.text != msg and rec.repaired
        elif m in ("vanilla", "action_verifier"):
            assert action.kind == "keep" and rec.verdict is None
        elif m == "guidance_verify":
            assert action.kind == "keep" and rec.verdict is not None  # detect, no change
        elif m == "self_verify":
            assert action.kind == "keep"                              # ungrounded -> no flag
        elif m == "guidance_verify_selfrevise":
            assert action.kind == "revise" and rec.verdict is not None and action.feedback
        elif m == "placebo_revise":
            assert action.kind == "revise" and action.feedback


def test_metrics_passhatk():
    trials = [TrialResult("t1", True, False, False, 100),
              TrialResult("t1", False, False, True, 90),
              TrialResult("t1", True, False, False, 110),
              TrialResult("t1", False, True, False, 95)]
    s = summarize(trials, k=2)
    assert abs(s["pass@1"] - 0.5) < 1e-9
    assert abs(s["pass^2"] - pass_hat_k(trials, 2)) < 1e-9


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all offline tests passed")
