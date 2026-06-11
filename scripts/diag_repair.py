r"""Error analysis for guidance_verify_repair: for each episode, capture EVERY repair the
verifier made (original guidance -> violated rules -> rewritten guidance), plus whether the
task ended up solved. Answers: is repair firing? on the right messages? changing them
sensibly? and does firing correlate with success or failure?

Cheap-ish: runs the repair method on a chosen task subset, 1 trial each (temp=0).

    $env:PYTHONUTF8="1"; python scripts/diag_repair.py 2>&1 | Select-String "EPISODE|REPAIR|VERDICT|ORIG|FIXED|OUTCOME|SUMMARY|no repairs"
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents import tau2_adapter as tau2
from src.llm import LLMClient
from src.verifier.guidance_verifier import verify_and_repair
from src.verifier.rubric_extractor import load_rubric

CFG = {"model": "gpt-4.1-mini", "temperature": 0.0}
MAX_STEPS = 100
RUBRIC = load_rubric("configs/rubrics/telecom.json")

# Focus on the tasks that fail as guidance in vanilla (mms_issue) + a couple of controls.
TASK_INDICES = [0, 1, 2, 5]   # bad_network_preference, bad_wifi_calling, break_apn, break_app_storage


def main():
    vclient = LLMClient(model="gpt-4o-mini", temperature=0.0, max_tokens=512)
    vcall = vclient.as_call()
    tasks = tau2.load_tasks("telecom_small")

    n_repairs_total = 0
    for i in TASK_INDICES:
        task = tasks[i]
        captured = []   # (orig, violated_ids, rationale, fixed)

        def hook(message, transcript):
            final, verdict, repaired = verify_and_repair(
                message, transcript, RUBRIC, vcall, grounded=True, enable_repair=True)
            if repaired and final != message:
                captured.append((message, verdict.violated_rule_ids, verdict.rationale, final))
            # mimic HookRecord shape enough for classify_violations (needs .verdict.ok)
            class R: pass
            r = R(); r.verdict = verdict; r.repaired = repaired
            return final, r

        print(f"\n=== EPISODE {i} id={getattr(task,'id','')[:50]} ===")
        sim, records = tau2.run_episode("telecom", task, 0, hook, CFG, max_steps=MAX_STEPS)
        reward, ri = tau2.get_reward(sim, task, "telecom")
        outcome = "SOLVED" if reward >= 1.0 else (
            "INCOMPLETE" if tau2.is_incomplete(sim, ri) else "FAILED")
        print(f"OUTCOME: {outcome} (reward={reward}) repairs_fired={len(captured)}")
        n_repairs_total += len(captured)
        for j, (orig, ids, rat, fixed) in enumerate(captured):
            print(f"  --- REPAIR {j+1} (rules={ids}) ---")
            print(f"  VERDICT: {rat[:200]}")
            print(f"  ORIG : {orig[:300]}")
            print(f"  FIXED: {fixed[:300]}")

    print(f"\n=== SUMMARY === total repairs fired across {len(TASK_INDICES)} episodes: {n_repairs_total}")
    if n_repairs_total == 0:
        print("no repairs fired -> verifier judged all guidance OK (verifier too lenient / rubric mismatch)")


if __name__ == "__main__":
    main()
