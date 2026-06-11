"""Summarize report-relevant result CSVs.

Unlike scripts/aggregate.py, this accepts arbitrary files, so it works for
micro experiments such as:

    python scripts/report_table.py results/report_micro_*.csv results/oracle_full60.csv
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from math import comb
from pathlib import Path


COST_HEADER = {
    "method",
    "task_id",
    "success",
    "errored",
    "agent_action_violation",
    "guidance_violation",
    "verifier_tokens",
}

ORACLE_HEADER = {"condition", "task_id", "seed", "reward", "success", "incomplete"}


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def _pass_hat_2(rows: list[dict[str, str]]) -> float | None:
    by_task: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_task[row["task_id"]].append(row)
    if not by_task or any(len(v) < 2 for v in by_task.values()):
        return None
    vals = []
    for trials in by_task.values():
        n = len(trials)
        c = sum(int(r["success"]) for r in trials)
        vals.append(comb(c, 2) / comb(n, 2))
    return sum(vals) / len(vals)


def summarize_cost(path: Path, rows: list[dict[str, str]]) -> dict[str, str]:
    n = len(rows)
    by_task: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_task[row["task_id"]].append(row)
    completed_failures = [
        r for r in rows if r["success"] == "0" and r.get("errored", "0") != "1"
    ]
    g = sum(int(r.get("guidance_violation", 0) or 0) for r in completed_failures)
    a = sum(int(r.get("agent_action_violation", 0) or 0) for r in completed_failures)
    pass2 = _pass_hat_2(rows)
    row_counts = [len(v) for v in by_task.values()] or [0]
    methods = Counter(r.get("method", "") for r in rows)
    successes = sum(int(r["success"]) for r in rows)
    errors = sum(int(r.get("errored", 0) or 0) for r in rows)
    balanced = min(row_counts) == max(row_counts)
    status = []
    status.append("balanced" if balanced else "unbalanced")
    status.append("clean" if errors == 0 else "dirty")
    return {
        "file": path.name,
        "kind": "cost_log",
        "status": ",".join(status),
        "methods": ",".join(methods),
        "tasks": str(len(by_task)),
        "trials": f"{min(row_counts)}-{max(row_counts)}",
        "pass@1": f"{successes / n:.3f}" if n else "0.000",
        "pass^2": "NA" if pass2 is None else f"{pass2:.3f}",
        "error_rate": f"{errors / n:.3f}" if n else "0.000",
        "guidance_fail_rate": f"{g / n:.3f}" if n else "0.000",
        "agent_fail_rate": f"{a / n:.3f}" if n else "0.000",
        "guidance_share": f"{g / len(completed_failures):.3f}" if completed_failures else "0.000",
        "converted": "",
        "broke": "",
        "incomplete": str(errors),
        "headroom": "",
        "tokens": str(sum(int(r.get("verifier_tokens", 0) or 0) for r in rows)),
    }


def summarize_oracle(path: Path, rows: list[dict[str, str]]) -> dict[str, str]:
    by_pair: dict[tuple[str, str], dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows:
        by_pair[(row["task_id"], row.get("seed", ""))][row["condition"]] = row
    paired = {
        k: v for k, v in by_pair.items()
        if "vanilla" in v and "repair_all" in v
    }
    n = len(paired)
    vanilla = sum(v["vanilla"]["success"] == "1" for v in paired.values())
    repair = sum(v["repair_all"]["success"] == "1" for v in paired.values())
    oracle = sum(
        v["vanilla"]["success"] == "1" or v["repair_all"]["success"] == "1"
        for v in paired.values()
    )
    converted = sum(
        v["vanilla"]["success"] != "1" and v["repair_all"]["success"] == "1"
        for v in paired.values()
    )
    broke = sum(
        v["vanilla"]["success"] == "1" and v["repair_all"]["success"] != "1"
        for v in paired.values()
    )
    incomplete_v = sum(v["vanilla"].get("incomplete") == "1" for v in paired.values())
    incomplete_r = sum(v["repair_all"].get("incomplete") == "1" for v in paired.values())
    return {
        "file": path.name,
        "kind": "oracle",
        "status": "paired",
        "methods": "vanilla,repair_all,oracle",
        "tasks": str(n),
        "trials": "paired",
        "pass@1": f"{vanilla / n:.3f}" if n else "0.000",
        "pass^2": "NA",
        "error_rate": "",
        "guidance_fail_rate": "",
        "agent_fail_rate": "",
        "guidance_share": "",
        "converted": str(converted),
        "broke": str(broke),
        "headroom": f"{(oracle - vanilla) / n:+.3f}" if n else "+0.000",
        "incomplete": f"{incomplete_v}/{incomplete_r}",
        "tokens": "",
        "repair_all": f"{repair / n:.3f}" if n else "0.000",
        "oracle": f"{oracle / n:.3f}" if n else "0.000",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="CSV files to summarize")
    args = ap.parse_args()

    rows_out = []
    for item in args.files:
        path = Path(item)
        if not path.exists():
            print(f"skip missing: {path}")
            continue
        header, rows = _read(path)
        h = set(header)
        if COST_HEADER <= h:
            rows_out.append(summarize_cost(path, rows))
        elif ORACLE_HEADER <= h:
            rows_out.append(summarize_oracle(path, rows))
        else:
            print(f"skip unknown schema: {path}")

    fields = [
        "file", "kind", "status", "methods", "tasks", "trials", "pass@1", "pass^2",
        "error_rate", "guidance_fail_rate", "agent_fail_rate",
        "guidance_share", "repair_all", "oracle", "headroom",
        "converted", "broke", "incomplete", "tokens",
    ]
    widths = {field: max(len(field), 10) for field in fields}
    for row in rows_out:
        for field in fields:
            widths[field] = max(widths[field], len(str(row.get(field, ""))))

    print(" | ".join(field.ljust(widths[field]) for field in fields))
    print("-+-".join("-" * widths[field] for field in fields))
    for row in rows_out:
        print(" | ".join(str(row.get(field, "")).ljust(widths[field]) for field in fields))


if __name__ == "__main__":
    main()
