# Guidance-Level Policy Verification in Dual-Control Tool Agents

Course project. **Thesis:** in τ²-bench's *dual-control* setting the risky action is taken by the **user**, so the prior "intercept-and-block the agent's tool call" paradigm cannot apply. The only lever is **repairing the agent's natural-language guidance to the user** before it is delivered. We build an online, policy-grounded **guidance verifier + repair** loop and measure how much of the known 18–25% dual-control `pass@1` drop it recovers.

See the full plan: `docs/PLAN.md` (copy of the approved plan).

## Why it's novel (vs. 2026 prior work)

| Prior work | Setting | What it verifies | Intervention |
|---|---|---|---|
| Solver-Aided Verification | τ-bench single-control | agent's own tool call | **block** (SMT/Z3) before execution |
| Verifier Tax | τ-bench single-control | agent's own actions | block; analyzes its cost |
| Willful Disobedience | τ²-bench | trajectory spec-violations | **post-hoc** detection (offline) |
| **This project** | **τ²-bench dual-control** | **agent → user guidance** | **repair guidance online** (no block possible) |

## Benchmark

Use **`amazon-agi/tau2-bench-verified`** (corrected policy/eval alignment), **Telecom** domain first. Subset ~50–100 tasks to control cost.

## Layout

```
src/
  agents/        base dual-control agent + baselines
  verifier/      policy→rubric extraction, guidance verifier, repair loop
  eval/          runner, metrics (pass@1, pass^k, violation rates, cost)
configs/         experiment configs (model, domain, k, subset)
results/         metrics tables + figures
docs/            PLAN.md, SETUP.md
```

## Methods to compare (all on the same subset)

1. `vanilla` — base dual-control agent, no verifier (reproduces the drop).
2. `self_verify` — generic self-verification of the agent message, **no policy grounding** (isolates grounding).
3. `action_verifier` — verifies the agent's own tool calls only (prior-art paradigm; should leave guidance failures untouched).
4. `guidance_verify` — **ours**: policy-grounded verification of agent→user guidance.
5. `guidance_verify_repair` — **ours + repair**: one bounded round of guidance repair.

## Quick start

See `docs/SETUP.md` for the AutoDL + API setup. Smoke-test 5 tasks before any full run.
