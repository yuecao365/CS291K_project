"""Run the five report micro experiments with one command.

This is only an orchestration wrapper. Each experiment is still implemented by
scripts/run_ablation.py, so resume behavior, trace dumping, verifier hooks, and
CSV schemas stay identical to the single-mode runner.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


DEFAULT_MODES = ("vanilla", "gt", "gtrepair_gated", "selfrevise", "placebo")
EXTRA_MODES = ("epistemic", "gt_epistemic")
ALL_MODES = DEFAULT_MODES + EXTRA_MODES
TRACE_MODES = {"gtrepair_gated", "selfrevise", "placebo", "epistemic", "gt_epistemic"}


def _run(cmd: list[str], env: dict[str, str]) -> None:
    print("\n$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, env=env)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/report_micro.yaml")
    ap.add_argument("--out", default="results/report_micro")
    ap.add_argument("--modes", nargs="+", default=list(DEFAULT_MODES),
                    choices=ALL_MODES)
    ap.add_argument("--no-traces", action="store_true",
                    help="do not dump traces for verifier/revision modes")
    ap.add_argument("--skip-summary", action="store_true",
                    help="skip the final report_table.py summary")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    config = str(Path(args.config))
    out = str(Path(args.out))

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    for mode in args.modes:
        cmd = [
            sys.executable,
            str(root / "scripts" / "run_ablation.py"),
            "--mode",
            mode,
            "--config",
            config,
            "--out",
            out,
        ]
        if mode in TRACE_MODES and not args.no_traces:
            cmd.append("--dump-traces")
        _run(cmd, env)

    if not args.skip_summary:
        files = [f"{out}_{mode}.csv" for mode in args.modes]
        oracle = Path("results/oracle_full60.csv")
        if oracle.exists():
            files.append(str(oracle))
        _run([sys.executable, str(root / "scripts" / "report_table.py"), *files], env)


if __name__ == "__main__":
    main()
