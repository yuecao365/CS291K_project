import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import src.agents.tau2_adapter as t

for ts in ["telecom_small", "telecom_full"]:
    tasks = t.load_tasks(ts)
    bases = Counter()
    none_crit = 0
    for task in tasks:
        ec = getattr(task, "evaluation_criteria", None)
        if ec is None:
            none_crit += 1
            continue
        rb = getattr(ec, "reward_basis", None) or []
        bases[tuple(sorted(str(x) for x in rb))] += 1
    print(f"\n{ts}: {len(tasks)} tasks | no-criteria: {none_crit}")
    for combo, n in bases.most_common():
        print(f"   reward_basis={combo} -> {n}")
