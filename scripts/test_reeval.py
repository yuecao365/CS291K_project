r"""Test whether forcing evaluate_simulation on a TIMED-OUT episode yields decomposable
sub-checks (env_assertions with env_type, action_checks with requestor). If yes, every
timeout becomes a scorable+decomposable failure for free.

Runs 2 tasks that timed out in the last sweep (indices 0 and 7).

    $env:PYTHONUTF8="1"; python scripts/test_reeval.py 2>&1 | Select-String "TASK|reward=|FAIL:|CLASSIFY|is_incomplete|re-eval"
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents import tau2_adapter as tau2

CFG = {"model": "gpt-4o-mini", "temperature": 0.0}
MAX_STEPS = 100
WHICH = [0, 7]   # mms_issue bad_network_preference, mobile_data bad_network_preference


def failed_checks(d: dict):
    for ck in (d.get("env_assertions") or []):
        if ck.get("met") is False:
            ea = ck.get("env_assertion") or {}
            print(f"  FAIL: env_assertion env_type={ea.get('env_type')} func={ea.get('func_name')}")
    for ck in (d.get("action_checks") or []):
        if ck.get("action_match") is False:
            act = ck.get("action") or {}
            print(f"  FAIL: action requestor={act.get('requestor')} name={act.get('name')}")
    dbc = d.get("db_check")
    if isinstance(dbc, dict) and dbc.get("db_match") is False:
        print("  FAIL: db_check db_match=False")


def main():
    tasks = tau2.load_tasks("telecom_small")
    for i in WHICH:
        task = tasks[i]
        print(f"\n=== TASK {i} id={getattr(task,'id','')[:50]} ===")
        sim, records = tau2.run_episode("telecom", task, 0, None, CFG, max_steps=MAX_STEPS)
        reward, ri = tau2.get_reward(sim, task, "telecom")
        term = getattr(sim, "termination_reason", None) if sim is not None else "CRASH"
        print(f"reward={reward} term={term} is_incomplete={tau2.is_incomplete(sim, ri)}")
        if ri is not None:
            d = ri.model_dump()
            print(f"  reward_basis={d.get('reward_basis')}")
            failed_checks(d)
        a, g = tau2.classify_violations(ri, records, reward)
        print(f"CLASSIFY: agent_action={a} guidance={g}")


if __name__ == "__main__":
    main()
