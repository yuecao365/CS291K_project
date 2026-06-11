"""Evaluation metrics for the guidance-verification experiments.

These are benchmark-agnostic: they consume per-task trial outcomes and emit the
numbers reported in the paper. `pass^k` follows the tau-bench definition (the
probability that a uniformly random size-k subset of a task's trials all pass).

Nothing here calls a model or the benchmark, so it is unit-testable in isolation
(`python -m src.eval.metrics` runs a quick self-check).
"""
from __future__ import annotations

from dataclasses import dataclass
from math import comb
from statistics import mean


@dataclass
class TrialResult:
    """Outcome of one run of one task."""
    task_id: str
    success: bool                      # task-level success (DB-state check from the benchmark)
    agent_action_violation: bool       # agent's own tool call violated policy
    guidance_violation: bool           # user took a policy-violating/dead-end action the agent guided
    tokens: int = 0                    # total tokens for cost accounting
    method: str = ""
    errored: bool = False              # episode crashed/overflowed -> no reward_info to attribute


def pass_at_1(trials: list[TrialResult]) -> float:
    """Mean success over all trials (== pass@1 when one trial per task)."""
    return mean(1.0 if t.success else 0.0 for t in trials) if trials else 0.0


def pass_hat_k(trials: list[TrialResult], k: int) -> float:
    """tau-bench pass^k: average over tasks of C(c,k)/C(n,k), where each task has
    n trials of which c succeeded. Requires n >= k for every task.
    """
    by_task: dict[str, list[TrialResult]] = {}
    for t in trials:
        by_task.setdefault(t.task_id, []).append(t)
    vals = []
    for task_id, ts in by_task.items():
        n = len(ts)
        c = sum(1 for t in ts if t.success)
        if n < k:
            raise ValueError(f"task {task_id}: need >= {k} trials for pass^{k}, got {n}")
        vals.append(comb(c, k) / comb(n, k))
    return mean(vals) if vals else 0.0


def violation_rates(trials: list[TrialResult]) -> dict[str, float]:
    """The headline decomposition: of the episodes that COMPLETED but FAILED, how do
    failures split between the agent's own actions vs. the guidance it gave the user?

    Crashed/overflowed episodes (`errored`) are excluded -- they have no reward_info,
    so attributing them would be guessing. They're surfaced via `error_rate` instead.
    """
    completed_failures = [t for t in trials if not t.success and not t.errored]
    n_all = len(trials) or 1
    denom = len(completed_failures) or 1
    g_count = sum(t.guidance_violation for t in completed_failures)
    a_count = sum(t.agent_action_violation for t in completed_failures)
    return {
        # SHARE (composition of failures): high in vanilla = "the headroom is guidance".
        # This need NOT drop when repair works -- numerator and denominator fall together.
        "agent_action_share": a_count / denom,
        "guidance_share": g_count / denom,
        # ABSOLUTE rate (over ALL trials): THIS is the thing repair should drive down, and
        # it moves in lockstep with pass@1 going up. Headline for the cross-method comparison.
        "guidance_fail_rate": g_count / n_all,
        "agent_action_fail_rate": a_count / n_all,
        "completed_failures": float(len(completed_failures)),
    }


def cost_per_solved(trials: list[TrialResult]) -> float:
    """Mean tokens spent per *successfully solved* task — the cost axis of the
    cost-vs-accuracy trade-off."""
    solved = [t for t in trials if t.success]
    if not solved:
        return float("inf")
    return sum(t.tokens for t in trials) / len(solved)


def summarize(trials: list[TrialResult], k: int | None = None) -> dict[str, float]:
    n = len(trials) or 1
    out = {"pass@1": pass_at_1(trials),
           "error_rate": sum(t.errored for t in trials) / n,
           "cost_per_solved": cost_per_solved(trials)}
    out.update(violation_rates(trials))
    if k is not None:
        out[f"pass^{k}"] = pass_hat_k(trials, k)
    return out


if __name__ == "__main__":
    # self-check: 1 task, 4 trials, 2 successes -> pass@1=0.5, pass^2 = C(2,2)/C(4,2)=1/6
    demo = [
        TrialResult("t1", True, False, False, 100),
        TrialResult("t1", True, False, False, 120),
        TrialResult("t1", False, False, True, 90),
        TrialResult("t1", False, True, False, 110),
    ]
    s = summarize(demo, k=2)
    assert abs(s["pass@1"] - 0.5) < 1e-9, s
    assert abs(s["pass^2"] - (comb(2, 2) / comb(4, 2))) < 1e-9, s
    assert abs(s["guidance_share"] - 0.5) < 1e-9, s            # 1 of 2 completed failures
    assert abs(s["agent_action_share"] - 0.5) < 1e-9, s
    assert abs(s["guidance_fail_rate"] - 0.25) < 1e-9, s       # 1 of 4 total trials
    print("metrics self-check OK:", s)
