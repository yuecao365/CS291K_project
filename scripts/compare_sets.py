import sys, statistics as st
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import src.agents.tau2_adapter as t

def summarize(ts, tasks):
    n_assert, n_sub, persona = [], [], Counter()
    for task in tasks:
        ec = getattr(task, "evaluation_criteria", None)
        ea = (getattr(ec, "env_assertions", None) or []) if ec else []
        n_assert.append(len(ea))
        tid = str(getattr(task, "id", ""))
        # format: [issue_type]tok1|tok2|...[PERSONA:X] -> count fault tokens between ] and [PERSONA
        mid = tid.split("]", 1)[1].split("[PERSONA")[0] if "]" in tid else tid
        mid = mid.strip()
        n_sub.append(mid.count("|") + 1 if mid else 0)
        if "PERSONA:" in tid:
            persona[tid.split("PERSONA:")[-1].rstrip("]")] += 1
    def f(x): return f"mean={st.mean(x):.2f} median={st.median(x)} max={max(x)}"
    print(f"\n=== {ts} (n={len(tasks)}) ===")
    print(f"  env_assertions/task : {f(n_assert)}")
    print(f"  sub-faults/task     : {f(n_sub)}")
    print(f"  persona             : {dict(persona)}")

summarize("telecom_small", t.load_tasks("telecom_small"))
# same 60-sample the oracle used (seed=0)
summarize("telecom_full sample60 (seed0)", t.load_tasks("telecom_full", num=60, seed=0))
