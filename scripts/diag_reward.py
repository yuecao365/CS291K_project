r"""Sweep ALL telecom_small tasks (1 trial each, vanilla, no verifier) and for every
failed episode print the real failed RewardInfo sub-checks + our classify decision.

Purpose: (1) get a representative agent-action vs guidance decomposition across issue
types (the first 3 tasks were all mms_issue), and (2) verify classify_violations reads
the RewardInfo fields correctly.

Run (venv active, key set, PYTHONUTF8=1):
    $env:PYTHONUTF8="1"; $env:OPENAI_API_KEY="sk-..."
    python scripts/diag_reward.py 2>&1 | Select-String "TASK|reward=|CLASSIFY|FAIL:|SUMMARY|reward_basis"
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents import tau2_adapter as tau2

CFG = {"model": "gpt-4.1-mini", "temperature": 0.0}   # temp 0 -> deterministic single trial
MAX_STEPS = 100   # gpt-4o-mini is 128k ctx; telecom tasks need >40 steps to finish


def failed_checks(d: dict) -> list[str]:
    out = []
    for ck in (d.get("env_assertions") or []):
        if ck.get("met") is False:
            ea = ck.get("env_assertion") or {}
            out.append(f"env_assertion[env_type={ea.get('env_type')},func={ea.get('func_name')}]")
    for ck in (d.get("action_checks") or []):
        if ck.get("action_match") is False:
            act = ck.get("action") or {}
            out.append(f"action[requestor={act.get('requestor')},name={act.get('name')}]")
    for key in ("communicate_checks", "nl_assertions"):
        for ck in (d.get(key) or []):
            r = ck.get("reward")
            if ck.get("met") is False or (r is not None and r < 1.0):
                out.append(f"{key}[met={ck.get('met')},reward={r}]")
    dbc = d.get("db_check")
    if isinstance(dbc, dict) and dbc.get("db_match") is False:
        out.append("db_check[db_match=False]")
    return out


def main():
    tasks = tau2.load_tasks("telecom_small")
    n = len(tasks)
    solved = errored = agent_v = guid_v = 0
    for i, task in enumerate(tasks):
        tid = getattr(task, "id", "")
        print(f"\n=== TASK {i+1}/{n} id={tid[:55]} ===")
        sim, records = tau2.run_episode("telecom", task, 0, None, CFG, max_steps=MAX_STEPS)
        reward, ri = tau2.get_reward(sim, task, "telecom")
        term = getattr(sim, "termination_reason", None) if sim is not None else "CRASH/ERROR"
        print(f"reward={reward} term={term}")
        incomplete = tau2.is_incomplete(sim, ri)
        if reward >= 1.0:
            solved += 1
        if incomplete:
            errored += 1
            print(f"  INCOMPLETE (timeout/crash, not scorable) reward_info={'None' if ri is None else 'null-checks'}")
        elif ri is not None:
            d = ri.model_dump()
            print(f"  reward_basis={d.get('reward_basis')}")
            for fc in failed_checks(d):
                print(f"  FAIL: {fc}")
        a, g = tau2.classify_violations(ri, records, reward)
        agent_v += int(a)
        guid_v += int(g)
        print(f"CLASSIFY: agent_action={a} guidance={g}")

    comp_fail = n - solved - errored
    print(f"\n=== SUMMARY (n={n}) ===")
    print(f"  solved={solved}  incomplete(timeout/crash)={errored}  completed_failures={comp_fail}")
    print(f"  agent_action_violations={agent_v}  guidance_violations={guid_v}")
    if comp_fail:
        print(f"  guidance_share_of_failures={guid_v/comp_fail:.2f}")


if __name__ == "__main__":
    main()
