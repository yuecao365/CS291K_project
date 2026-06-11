"""Experiment runner: load Telecom tasks -> run a METHOD over a seeded subset for N
trials -> log per-trial TrialResult + verifier tokens -> dump metrics.

tau2 access is isolated in src/agents/tau2_adapter.py; guidance interception is in
src/agents/base_agent.py. This file is orchestration + bookkeeping only.

`tokens` per trial = verifier tokens (the marginal cost of our method); the base agent
runs on the local GPU so its $ cost is ~0 and tracked separately via sim cost.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from ..agents import tau2_adapter as tau2
from ..llm import LLMClient
from ..methods import METHODS, make_hook
from ..verifier.rubric_extractor import extract_rubric, load_rubric, save_rubric
from .metrics import TrialResult, summarize


def _load_config(path: str) -> dict:
    import yaml
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def ensure_rubric(domain: str, rubric_path: str, extract_call):
    p = Path(rubric_path)
    if p.exists():
        rules = load_rubric(p)
        print(f"[rubric] loaded {len(rules)} cached rules from {p}")
        return rules
    print(f"[rubric] no cache at {p}; extracting from {domain} policy...")
    rules = extract_rubric(tau2.get_domain_policy(domain), extract_call)
    save_rubric(rules, p)
    print(f"[rubric] extracted {len(rules)} rules -> {p.resolve()}  (HAND-CHECK before trusting results)")
    return rules


def run_task(task, method, domain, rubric, verifier_client, base_llm_cfg, trials,
             verifier_call, max_steps, base_seed=0) -> list[TrialResult]:
    task_id = str(getattr(task, "id", task))
    use_hook = method not in ("vanilla", "action_verifier")
    results = []
    for ti in range(trials):
        hook = make_hook(method, rubric, verifier_call) if use_hook else None
        before = verifier_client.usage.total_tokens
        sim, records = tau2.run_episode(domain, task, base_seed + ti, hook, base_llm_cfg, max_steps)
        reward, reward_info = tau2.get_reward(sim, task, domain)
        a_viol, g_viol = tau2.classify_violations(reward_info, records, reward)
        v_tokens = verifier_client.usage.total_tokens - before
        results.append(TrialResult(task_id=task_id, success=reward >= 1.0,
                                   agent_action_violation=a_viol, guidance_violation=g_viol,
                                   tokens=v_tokens, method=method,
                                   errored=tau2.is_incomplete(sim, reward_info)))
    return results


def write_cost_log(path: str, trials: list[TrialResult]):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["method", "task_id", "success", "errored", "agent_action_violation",
                    "guidance_violation", "verifier_tokens"])
        for t in trials:
            w.writerow([t.method, t.task_id, int(t.success), int(t.errored),
                        int(t.agent_action_violation), int(t.guidance_violation), t.tokens])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--method", choices=METHODS, help="override config rollout.method")
    ap.add_argument("--limit", type=int, help="cap number of tasks (smoke testing)")
    ap.add_argument("--trials", type=int, help="override config rollout.trials (smoke testing)")
    args = ap.parse_args()

    cfg = _load_config(args.config)
    domain = cfg["domain"]
    task_set = cfg["task_set"]
    method = args.method or cfg["rollout"]["method"]
    k, trials = cfg["eval"]["k"], (args.trials or cfg["rollout"]["trials"])
    max_steps = cfg.get("max_steps", 50)
    if trials < k:
        # smoke runs may use fewer trials than k -> skip pass^k instead of erroring out.
        print(f"[run] trials ({trials}) < k ({k}); pass^{k} will be skipped.")
        k = None

    verifier_client = LLMClient(**cfg["verifier_model"])
    verifier_call = verifier_client.as_call()

    # rubric extraction is one long output -> give it a big token budget (separate from
    # the small per-turn verify budget).
    extract_call = verifier_client.as_call(max_tokens=4096)
    rubric = (ensure_rubric(domain, cfg["paths"]["rubric"], extract_call)
              if method not in ("vanilla", "action_verifier") else [])
    tasks = tau2.load_tasks(task_set, num=cfg["subset"]["size"], seed=cfg["subset"]["seed"])
    if args.limit:
        tasks = tasks[:args.limit]
    print(f"[run] method={method} domain={domain} task_set={task_set} tasks={len(tasks)} trials={trials}")

    all_trials: list[TrialResult] = []
    for i, task in enumerate(tasks, 1):
        all_trials += run_task(task, method, domain, rubric, verifier_client, cfg["base_model"],
                               trials, verifier_call, max_steps, base_seed=cfg["subset"]["seed"] * 1000)
        print(f"  [{i}/{len(tasks)}] {getattr(task, 'id', '')} done")

    cost_path = cfg["paths"]["cost_log"].replace(".csv", f"_{method}.csv")
    write_cost_log(cost_path, all_trials)
    print(f"\n=== results ({method}) -> {cost_path} ===")
    for kk, vv in summarize(all_trials, k=k).items():
        print(f"  {kk}: {vv}")
    print(f"  verifier_tokens_total: {sum(t.tokens for t in all_trials)}")


if __name__ == "__main__":
    main()
