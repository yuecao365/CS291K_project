import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import src.agents.tau2_adapter as t

for ts in ["telecom", "telecom_full", "telecom_small"]:
    try:
        tasks = t.load_tasks(ts)
        cats = Counter(str(getattr(x, "id", "")).split("]")[0].strip("[") for x in tasks)
        print(f"{ts:14} -> {len(tasks):4d} tasks | {dict(cats)}")
    except Exception as e:
        print(f"{ts:14} -> ERR {type(e).__name__}: {str(e)[:90]}")
