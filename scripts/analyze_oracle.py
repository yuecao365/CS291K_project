import csv, sys
from collections import Counter

path = sys.argv[1] if len(sys.argv) > 1 else "results/oracle_full60.csv"
rows = list(csv.DictReader(open(path, encoding="utf-8")))

by = {}
for r in rows:
    by.setdefault(r["task_id"], {})[r["condition"]] = r

# only tasks with BOTH conditions are a usable oracle pair
paired = {t: d for t, d in by.items() if "vanilla" in d and "repair_all" in d}
n = len(paired)
print(f"file: {path}")
print(f"rows: {len(rows)} | tasks touched: {len(by)} | COMPLETE pairs: {n}")

def is_succ(r): return r["success"] == "1"
def is_inc(r):  return r["incomplete"] == "1"

van = sum(is_succ(d["vanilla"]) for d in paired.values())
rep = sum(is_succ(d["repair_all"]) for d in paired.values())
ora = sum(is_succ(d["vanilla"]) or is_succ(d["repair_all"]) for d in paired.values())
print(f"\nvanilla    pass@1: {van/n:.3f}  ({van}/{n})")
print(f"repair_all pass@1: {rep/n:.3f}  ({rep}/{n})")
print(f"ORACLE     pass@1: {ora/n:.3f}  ({ora}/{n})")
print(f">>> HEADROOM (oracle - vanilla): {(ora-van)/n:+.3f}")

# decompose vanilla failures: timeout (incomplete) vs scored failure (real guidance/action fail)
van_fail = {t: d for t, d in paired.items() if not is_succ(d["vanilla"])}
timeouts = {t: d for t, d in van_fail.items() if is_inc(d["vanilla"])}
scored = {t: d for t, d in van_fail.items() if not is_inc(d["vanilla"])}
print(f"\nvanilla failures: {len(van_fail)}")
print(f"  - timeouts (incomplete, MAX_STEPS): {len(timeouts)}")
print(f"  - SCORED failures (real fail, repairable in principle): {len(scored)}")

converted = [t for t, d in van_fail.items() if is_succ(d["repair_all"])]
conv_scored = [t for t in converted if t in scored]
print(f"\nrepair CONVERTED (vanilla-fail -> repair-win): {len(converted)}")
print(f"  ... of which were SCORED failures (the ones that matter): {len(conv_scored)}")
broke = [t for t, d in paired.items() if is_succ(d["vanilla"]) and not is_succ(d["repair_all"])]
print(f"repair BROKE (vanilla-win -> repair-fail): {len(broke)}")

print("\n--- SCORED vanilla failures (NOT timeouts) + what repair did ---")
for t, d in scored.items():
    v, rp = d["vanilla"], d["repair_all"]
    verdict = "FIXED!" if is_succ(rp) else ("still-fail" if not is_inc(rp) else "->timeout")
    print(f"  {t}\n      vanilla r={v['reward']} | repair r={rp['reward']} inc={rp['incomplete']}  [{verdict}]")

print("\n--- repair BROKE these working tasks ---")
for t in broke:
    rp = paired[t]["repair_all"]
    print(f"  {t}  (repair r={rp['reward']} inc={rp['incomplete']})")

cats = Counter(t.split("]")[0].strip("[") for t in paired)
print(f"\ncategory coverage of paired tasks: {dict(cats)}")
