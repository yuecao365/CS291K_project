r"""Aggregate the per-method cost_log_*.csv files into one comparison table (the headline
result). Reads whatever methods are present in results/, computes the summary metrics per
method, prints a table, and writes results/summary.csv.

    python scripts/aggregate.py [--k 2]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.eval.metrics import TrialResult, summarize

METHOD_ORDER = ["vanilla", "action_verifier", "self_verify",
                "guidance_verify", "guidance_verify_repair"]
COLS = ["pass@1", "pass^{k}", "guidance_fail_rate", "agent_action_fail_rate",
        "guidance_share", "error_rate", "completed_failures", "cost_per_solved",
        "verifier_tokens_total"]


def load_trials(path: Path) -> list[TrialResult]:
    out = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.append(TrialResult(
                task_id=row["task_id"],
                success=bool(int(row["success"])),
                agent_action_violation=bool(int(row.get("agent_action_violation", 0))),
                guidance_violation=bool(int(row.get("guidance_violation", 0))),
                tokens=int(row.get("verifier_tokens", 0) or 0),
                method=row["method"],
                errored=bool(int(row.get("errored", 0))),
            ))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=2)
    args = ap.parse_args()
    resdir = Path("results")

    rows = []
    for m in METHOD_ORDER:
        p = resdir / f"cost_log_{m}.csv"
        if not p.exists():
            continue
        trials = load_trials(p)
        s = summarize(trials, k=args.k)
        s["verifier_tokens_total"] = sum(t.tokens for t in trials)
        s["method"] = m
        s["n_trials"] = len(trials)
        rows.append(s)

    if not rows:
        print("No results/cost_log_*.csv found. Run scripts/run_all.ps1 first.")
        return

    kcol = f"pass^{args.k}"
    header = ["method", "n_trials", "pass@1", kcol, "guidance_fail_rate",
              "agent_action_fail_rate", "guidance_share", "error_rate",
              "completed_failures", "cost_per_solved", "verifier_tokens_total"]
    widths = {h: max(len(h), 12) for h in header}

    def fmt(v):
        if isinstance(v, float):
            return "inf" if v == float("inf") else f"{v:.3f}"
        return str(v)

    print(" | ".join(h.ljust(widths[h]) for h in header))
    print("-+-".join("-" * widths[h] for h in header))
    out_rows = []
    for r in rows:
        line = {h: fmt(r.get(h, "")) for h in header}
        out_rows.append(line)
        print(" | ".join(line[h].ljust(widths[h]) for h in header))

    with (resdir / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(out_rows)
    print(f"\n-> wrote {resdir / 'summary.csv'}")


if __name__ == "__main__":
    main()
