# Report Experiment Plan

This note is for the 5-page report. It separates what the current evidence can support from what still needs a small follow-up run.

## Current Evidence Audit

Use as main evidence:

- `results/summary.csv`: easy `telecom_small` comparison. `vanilla` is `0.787`, `guidance_verify_repair` is `0.775`, and repair spends `1,256,156` verifier tokens. This supports the claim that the first implementation does not improve task success on the easy set.
- `results/oracle_repair.csv`: 20 paired easy tasks. `vanilla=0.900`, `repair_all=0.800`, `oracle=0.900`, so the easy set has no repair headroom.
- `results/oracle_full60.csv`: 60 paired sampled full tasks. `vanilla=0.250`, `repair_all=0.200`, `oracle=0.300`, so the upper-bound headroom is only `+0.050`; repair converts 3 failures but breaks 6 successes.
- `results/cost_log_hard_gt.csv`: 12 hard tasks with oracle plans, `pass@1=0.708`. This is useful for showing that planning/diagnosis is a major bottleneck.
- `results/cost_log_hard_gtsolo.csv`: 12 hard tasks with oracle plan and no user, `pass@1=1.000`. This is useful for showing that the remaining gap is specifically dual-control/user-guidance friction.

Use only as diagnostics, not headline claims:

- `results/cost_log_hard_vanilla.csv`: current file is unbalanced across tasks (`2-4` rows per task), so it is not a clean final table.
- `results/cost_log_hard_*.csv.bak` for self-revise/placebo: balanced but dirty, with high error rates (`25-35%` for self-revise/GT-selfrevise). These support "the implementation was unstable", not "self-repair is worse" as a rigorous conclusion.
- `results/traces/*`: useful for examples of verifier over-triggering (`R6/R8/R9`), but some trace fields come from older code paths. Use them qualitatively, not as quantitative evidence.

## Recommended Thesis For The Report

The most defensible conclusion is a negative but meaningful one:

> In dual-control Telecom tasks, many failures are user-side/guidance-attributed, so guidance is a real failure channel. However, checking and rewriting the final agent-to-user message is not an effective intervention in this implementation. The failure is mostly upstream: diagnosis/planning and multi-step trajectory control. When repair is applied at the final message level, it has low upside and can break already-correct guidance.

This is stronger and more honest than claiming the proposed verifier improves task completion.

## Why More Experiments Are Needed

One small follow-up is still worth doing before writing the final report:

- The easy set has a ceiling effect.
- The hard set has stronger signal but incomplete/dirty method coverage.
- The report needs a clean table for the real intervention on a tiny but hard subset.

Do not run another broad sweep. Run a micro experiment on the existing 4-task trace subset.

## Micro Experiment

Config: `configs/report_micro.yaml`

Task file: `configs/trace_task_ids.json`

Task composition:

- 4 tasks from `telecom_full`.
- 3 MMS tasks and 1 mobile-data task.
- Fault counts per task: 9, 7, 5, and 5.
- Expected actions are mostly user-side device actions: 9/11, 8/9, 5/7, and 4/5 respectively.
- This makes the subset small but directly targeted at the dual-control guidance channel.

Run these modes:

```powershell
$env:PYTHONUTF8="1"
.venv/Scripts/python.exe scripts/run_ablation.py --mode vanilla        --config configs/report_micro.yaml --out results/report_micro
.venv/Scripts/python.exe scripts/run_ablation.py --mode gt             --config configs/report_micro.yaml --out results/report_micro
.venv/Scripts/python.exe scripts/run_ablation.py --mode gtrepair_gated --config configs/report_micro.yaml --out results/report_micro --dump-traces
.venv/Scripts/python.exe scripts/run_ablation.py --mode selfrevise     --config configs/report_micro.yaml --out results/report_micro --dump-traces
```

Summarize after the runs:

```powershell
.venv/Scripts/python.exe scripts/report_table.py `
  results/report_micro_vanilla.csv `
  results/report_micro_gt.csv `
  results/report_micro_gtrepair_gated.csv `
  results/report_micro_selfrevise.csv `
  results/oracle_full60.csv
```

Minimum acceptable evidence:

- 4 tasks x 4 trials for `vanilla`, `gt`, and `gtrepair_gated`.
- `selfrevise` may be reported only if error rate is low. If error rate remains high, report it as an implementation limitation and do not use its pass rate as a method comparison.
- Include error rate next to pass@1. Do not hide incomplete runs.

Interpretation rules:

- If `gt >> vanilla`, the base agent is diagnosis/planning-limited.
- If `gtrepair_gated > gt`, final guidance repair helps even when planning is solved.
- If `gtrepair_gated <= gt`, final guidance repair is not the right intervention point.
- If `selfrevise` has high error rate, the self-repair implementation is not stable enough to support a conclusion.

## Five-Page Report Structure

1. Introduction and motivation: prior verifiers block agent actions, but dual-control moves critical actions to the user.
2. Method: policy-to-rubric, online guidance verifier, external repair, and self-revision attempt.
3. Experimental setup: tau2-bench-verified Telecom, `telecom_small`, oracle repair, hard/micro subset, metrics and error handling.
4. Results: easy-set no improvement, oracle upper bound small, hard/micro decomposition if rerun completes.
5. Discussion: negative result, why final-message repair is too late, limitations, and future direction toward plan/diagnosis verification.

## Recommended Wording

Avoid:

- "Our method improves dual-control task completion."
- "Self-repair is worse than external repair" unless the rerun is clean.
- "Guidance repair cannot work in general."

Use:

- "In this implementation and benchmark slice, final-message guidance repair did not improve pass@1."
- "Oracle repair shows limited headroom and substantial risk of over-repair."
- "The next intervention should verify the agent's diagnosis or intended user-action plan before the final instruction is written."
