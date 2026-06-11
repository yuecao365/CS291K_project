r"""Diagnostic: run telecom episodes (no verifier) at max_steps=100 and report, for
each, whether it COMPLETED (non-null reward_info) vs hit MAX_STEPS. Dumps the real
RewardInfo of the first completed episode so we can calibrate classify_violations.

Run on the box (local Qwen, free):
    cd ~/Project && python scripts/diag.py 2>&1 | grep -v "DEBUG\|INFO\|WARNING\|mapped" | tail -50
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents import tau2_adapter as tau2

CFG = {"model": "Qwen/Qwen2.5-14B-Instruct-AWQ", "base_url": "http://127.0.0.1:6006/v1",
       "api_key": "EMPTY", "temperature": 0.7}
N_TASKS = 3
MAX_STEPS = 40


def _completed(ri) -> bool:
    if ri is None:
        return False
    d = ri.model_dump()
    return any(d.get(k) is not None for k in
               ("db_check", "env_assertions", "action_checks", "nl_assertions", "communicate_checks"))


def main():
    tasks = tau2.load_tasks("telecom_small", num=N_TASKS, seed=0)
    first_dump = None
    for i, task in enumerate(tasks):
        sim, _ = tau2.run_episode("telecom", task, 0, None, CFG, max_steps=MAX_STEPS)
        reward, ri = tau2.get_reward(sim, task, "telecom")
        term = getattr(sim, "termination_reason", None) if sim is not None else "CRASH/OVERFLOW"
        n = len(getattr(sim, "messages", [])) if sim is not None else 0
        done = _completed(ri)
        print(f"[{i}] id={getattr(task,'id','')[:50]} reward={reward} "
              f"term={term} msgs={n} completed={done}")
        if done and first_dump is None:
            first_dump = ri.model_dump()

    print("\n=== first COMPLETED episode RewardInfo ===")
    if first_dump is None:
        print("NONE completed within max_steps -> base agent loops/fails; consider API base.")
    else:
        print(json.dumps(first_dump, indent=2, default=str)[:3500])


if __name__ == "__main__":
    main()
