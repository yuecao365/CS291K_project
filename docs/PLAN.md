# Course Project Plan — Guidance-Level Policy Verification in Dual-Control Tool Agents

## Context

This is an LLM/agent course project. Requirements: **novel** (not a reproduction), **evaluable on an existing benchmark**, with clear **motivation + analysis**, under a tight budget (**API-only + a cheap AutoDL GPU rental**, no training).

A first draft ("policy-grounded verifier on τ-bench, select/repair among k trajectories") was **rejected after a literature check**: it overlaps heavily with existing 2026 work — *Solver-Aided Verification* (policy→SMT→block tool call pre-execution), *DeepVerifier* (rubric→verify→repair), *SETS* (sample-k→self-verify→correct), and *The Verifier Tax* (cost/horizon analysis of blocking). All of that prior work evaluates on **τ-bench, which is single-control**.

The repositioned project exploits the one structural gap they all share: they verify the **agent's own actions and block them before execution**. This plan instead targets **τ²-bench's dual-control setting**, where the risky action is taken by the **user**, blocking is impossible, and the only lever is **better guidance** — an unstudied verification channel.

---

## Motivation (why this is open and worth doing)

- The τ²-bench paper reports its **largest failure mode**: an **18–25% pass@1 drop** when the agent must *guide a user to act* instead of acting itself. This gap is acknowledged but not addressed by a verifier.
- In dual-control, the agent can be perfectly compliant in its *own* tool calls yet still cause a violation/failure by **mis-instructing the user** (e.g., "go ahead and factory-reset" when policy required a backup first).
- Because the user takes the action, the dominant prior paradigm — **intercept-and-block before execution** (Solver-Aided, gateway approaches) — *structurally cannot apply*. The only remaining lever is **repairing the guidance**, which also sidesteps the *Verifier Tax* critique ("blocking ≠ task success"): here there is nothing to block.

### How it differs from prior work

| Dimension | Prior work (Solver-Aided / Verifier Tax / DeepVerifier / SETS) | This project |
|---|---|---|
| Benchmark | τ-bench **single-control** | τ²-bench **dual-control** |
| What is verified | The agent's **own** tool call | The agent's **NL guidance to the user** |
| Intervention | **Block** the action pre-execution | **Repair guidance** (blocking impossible — user acts) |
| Representable in SMT/Z3? | Yes (action = constraint) | No — grounded NL + hidden user state |
| Target failure | Agent violates policy | Agent **causes the user** to violate/fail (the 18–25% drop) |

### Novel contributions
1. First to do failure decomposition (*agent-action* vs. **guidance-induced** violations) **online and interventionally** — i.e. verify the guidance *before* the user acts and *repair* it. (NB: *Willful Disobedience*, arXiv 2603.23806, already does **post-hoc** trace classification of spec violations on τ²-bench; it is the diagnostic/offline baseline this project must cite and beat by acting online.)
2. A **constructive guidance verifier–repair loop** that has no blocking analogue.
3. Evidence on **where the Verifier Tax conclusion flips**: when blocking is impossible, constructive verification is the only mechanism that can raise task success, changing the cost calculus.

---

## Method

1. **Base dual-control agent.** Run τ²-bench's Telecom (and optionally Airline/Retail) dual-control tasks with a standard tool-calling + user-guidance agent. Base model = small open model on AutoDL (Qwen2.5/Qwen3 7B) and/or a cheap API model; the user simulator is τ²-bench's built-in one.
2. **Policy → guidance rubric (one-time, per domain, cached).** Convert the domain policy doc into a checklist of *guidance-relevant* rules — preconditions the user must satisfy before an action, required ordering, prohibited instructions.
3. **Guidance verifier.** Before the agent's instruction is delivered to the user, score it against (a) the rubric and (b) the *inferred* user/world state, producing pass/fail + per-rule rationale. This operates on the **agent→user message channel**, not on tool calls.
4. **Guidance repair.** If a violation/dead-end is predicted, feed the flagged rules back and regenerate the instruction (one bounded round). No blocking — the corrected guidance is what the user receives.

## Baselines (evaluated identically)
- Vanilla dual-control agent (no verifier) — reproduces the 18–25% drop.
- Generic self-verification of the agent message (SETS-style, **no policy grounding**) — isolates policy grounding as the contribution.
- Action-level verifier only (the prior-art paradigm, verifying the agent's own tool calls) — shows it leaves the *guidance* failure untouched.

## Evaluation
- **Benchmark:** **`amazon-agi/tau2-bench-verified`** (corrected version — fixes policy/eval misalignment in the original, important since this project tests *policy* compliance), Telecom domain first (the canonical dual-control domain); subset tasks to control cost.
- **Metrics:** pass@1, **pass^k** (reliability), **guidance-induced violation rate** (new), agent-action violation rate, **cost/tokens per solved task**.
- **Ablations:** verifier with vs. without policy grounding; selection-only vs. selection+repair; small vs. large base model; rubric quality (auto vs. lightly hand-checked).
- **Headline analysis:** decompose the dual-control failure (how much of the 18–25% drop is guidance-induced?) and report how much each method recovers, vs. its cost.

## Budget fit
τ²-bench is text-only and subsettable. A subset (~50–100 tasks) × small `k` × a few methods is affordable on API; cheaper if the base agent runs as Qwen on a spot AutoDL GPU and only the verifier uses an API model.

## Risks & mitigations
- **A appears already done** → before coding, run one focused scan for "dual-control guidance verification / agent-to-user instruction compliance"; if taken, fall back to Project B below.
- **τ²-bench dual-control harness friction** (user simulator, Telecom env) → smoke-test 5 tasks end-to-end in W1 before committing.
- **Verifier weak / rubric noisy** → report the oracle upper bound (best achievable guidance) regardless; partial recovery + analysis is still a valid result.
- **Inferring hidden user state is hard** → start with the observable transcript only; treat state inference as a stretch ablation.

---

## Backup — Project B: "Risk-Triggered Selective Verification" (lower risk, on τ-bench)
If A is taken or the dual-control harness proves too heavy: directly operationalize the *Verifier Tax*. Learn a cheap risk classifier that fires the expensive verifier **only** on irreversible actions (refund/cancel/factory-reset) and trace the **safety × success × cost** Pareto vs. always-verify (Solver-Aided) and never-verify. Contribution = recovering most of the safety benefit at a fraction of verifier cost, with the horizon analysis the Verifier Tax called for. Cheaper, simpler, lower novelty risk.

---

## Deliverables & timeline (~6 weeks)
1. **W1** — Stand up τ²-bench Telecom dual-control; reproduce the vanilla agent + the guidance-failure drop on a small subset; confirm cost model.
2. **W2** — Implement the two baselines (generic self-verification; action-level verifier).
3. **W3** — Policy→guidance rubric extraction + guidance verifier (pre-delivery scoring).
4. **W4** — Guidance repair loop; full ablations (grounding on/off, selection vs. selection+repair, small/large base).
5. **W5** — Analysis: failure decomposition (guidance-induced vs. action), recovery vs. cost, figures.
6. **W6** — Write-up: motivation, method, results, analysis, limitations.

## Verification of success
- "Works" if the pipeline runs end-to-end on τ²-bench Telecom and reports pass@1 / pass^k / guidance-violation rate / cost for every method on the same subset.
- Hypothesis "supported" if guidance-level policy verification recovers a meaningful share of the 18–25% dual-control drop and beats both baselines at comparable cost, with an error analysis attributing the gain to corrected guidance.

## Note
This is a research/ideation plan; there is no existing repository in `C:\Users\cy200\Desktop\Project` to modify. Approving it means I'd next scaffold the τ²-bench dual-control harness, the baseline agents, and the guidance verifier.
