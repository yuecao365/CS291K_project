"""Drop errored rows from cost_log CSVs so resume re-runs those tasks.

A row is errored when the `errored` column == "1" (episode crashed / API outage /
MAX_STEPS). The task-level resume in run_ablation keeps a task only if it has >= trials
rows; removing its errored rows makes it "partial" -> it gets re-run cleanly on the next
invocation. Tasks already fully clean (no errored rows) keep all rows and are skipped.

Backs up each file to <file>.bak before rewriting. Run again with --restore to undo.

Usage:
  python scripts/purge_errored.py                      # default 5-arm hard files
  python scripts/purge_errored.py results/cost_log_hard_selfrevise.csv ...
  python scripts/purge_errored.py --restore            # restore from .bak
"""
from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

DEFAULT = [f"results/cost_log_hard_{m}.csv"
           for m in ("vanilla", "selfrevise", "placebo", "gt", "gt_selfrevise")]
TRIALS = 4
ERR_COL = 3   # header: method,task_id,success,errored,agent_action_violation,guidance_violation,verifier_tokens


def restore(files):
    for f in files:
        bak = Path(f + ".bak")
        if bak.exists():
            Path(f).write_text(bak.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"restored {f} from .bak")
        else:
            print(f"no backup for {f}")


def purge(files):
    for f in files:
        p = Path(f)
        if not p.exists():
            print(f"skip (missing): {f}")
            continue
        rows = list(csv.reader(p.open(encoding="utf-8")))
        header, body = rows[0], rows[1:]
        p.with_suffix(p.suffix + ".bak").write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
        kept = [r for r in body if r[ERR_COL] != "1"]
        removed = len(body) - len(kept)
        with p.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh); w.writerow(header); w.writerows(kept)
        tasks = Counter(r[1] for r in kept)
        will_rerun = sum(1 for c in tasks.values() if c < TRIALS) + \
            len({r[1] for r in body} - set(tasks))   # tasks that lost ALL rows
        done = sum(1 for c in tasks.values() if c >= TRIALS)
        print(f"{p.name:34s} removed={removed:3d} errored rows | "
              f"clean_done={done:2d} tasks | will_rerun={will_rerun:2d} tasks")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = args or DEFAULT
    if "--restore" in sys.argv:
        restore(files)
    else:
        purge(files)
        print("\nDone. Now re-run the same foreach command; resume will redo only the affected tasks.")
