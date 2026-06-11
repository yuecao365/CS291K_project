# Speech Script — Guidance-Level Policy Verification in Dual-Control Tool Agents

*Presenter: Yue Cao. 15 slides. Target ≈ 11–13 minutes. Slide numbers follow the on-screen footer (the title slide is unnumbered).*

---

## Slide 1 — Title

Hi everyone, I'm Yue Cao. My project asks a simple question with a not-so-simple answer: **when the user — not the agent — is the one holding the controls, can we make a tool-using agent more reliable by repairing the natural-language guidance it gives the user?** I'll walk through the idea, the experiments, and — being upfront — an honest negative result that turned out to be more interesting than a small win would have been.

---

## Slide 2 — The setting: single- vs. dual-control

First, the setting. Most agent benchmarks are **single-control**: only the agent touches the world through tools, and the user just supplies information. That's the world prior verification work lives in — and crucially, in that world a verifier can inspect the agent's tool call and **block** it before it executes.

τ²-bench introduces **dual-control**: both the agent *and* the user act on a shared world, modeled as a decentralized POMDP. Now the agent's hardest job isn't acting — it's **guiding the user to act**. And here's the structural twist: the user's action can't be blocked. So the only lever left is the **guidance itself**. The benchmark reports an 18–25% pass@1 drop moving from single- to dual-control — the risky action effectively moves from a tool call into a natural-language instruction.

---

## Slide 3 — A concrete example

Let me make that concrete with something everyone has lived through: "I'm locked out of my account." The fix is a password reset.

In a single-control world, the agent just calls `reset_password()` itself — done, nothing to guide. But in reality, the reset link lands in *your* inbox, on *your* device. The agent can't click it. All it can do is **instruct** you: "open the reset email we just sent and click the link." You perform it. And if the agent tells you to click the link *before* it actually sent the email, you wait forever, and you fail — and there was no tool call to intercept. **You cannot block a sentence; you can only try to repair it.** That sentence is the entire lever this project studies.

---

## Slide 4 — The dual-control loop

Here's how the default agent actually runs, step by step. It diagnoses — possibly calling its own tools. Then it produces a **guidance message** to the user. The user acts on their own device. That changes the shared world. The agent observes the new state and continues, until it confirms the issue is resolved or gives up.

The key thing to notice is the handoff at steps 2-to-3 — the agent's guidance crossing to the user's action. That arrow, highlighted in coral, is **the only place we can intervene**: verify, and if needed repair, the guidance before the user acts. Everything in this talk hangs on whether that single point of leverage is enough.

---

## Slide 5 — Where prior work stops

So why hasn't this been done? Because every related line of work verifies the **agent's own action and blocks it**. Solver-Aided Verification compiles the policy into SMT constraints and blocks non-compliant tool calls. The Verifier Tax paper studies exactly that blocking and finds — tellingly — that blocking rarely translates into task success. AgentPex detects spec violations, but offline, after the fact. DeepVerifier and SETS do verify-and-repair, but on the agent's own output, in single-control.

All of them assume the risky action is the agent's and is blockable. **In dual-control it's neither.** That's the gap: the only remaining lever is repairing the natural-language guidance before the user acts.

---

## Slide 6 — The idea / hypothesis

So the hypothesis is direct: **repair the agent's guidance before the user acts.** A verify-then-repair loop on the agent-to-user message channel — the one intervention point that has no "block" analogue. If failures really are caused by bad guidance, then correcting that guidance should recover them. That's the bet.

---

## Slide 7 — Method architecture

Here's the architecture. On the left is the agent itself: it runs a **reason-and-act loop**, calling tools and observing the environment — that's the self-loop you see between AGENT and TOOLS. When the agent emits a user-directed message, that guidance is intercepted by **our module**: we VERIFY it, and if there's a problem, we REPAIR it once — then deliver the corrected version to the user. The user acts, the shared world changes, and the agent observes again — the dashed outer loop.

The important design point: there is **no blocking**. We never stop the agent; we only rewrite the sentence it was about to send. The intervention is a drop-in on one channel, which is what makes the ablations clean.

---

## Slide 8 — Benchmark & evaluation

We evaluate on **τ²-bench, Telecom domain**. Here's what one test task actually looks like: an issue type — say, an MMS problem — with one or more injected faults on the user's device, a persona controlling how cooperative the user is, agent-side tools, and user-side tools that act on the device. Success is checked by **environment assertions** on the final device state, and the reward is **binary**: 1.0 only if *all* assertions hold at the end, otherwise 0. A timeout or crash is a 0.

We use two task sets: **telecom_small**, 20 curated single-fault tasks, and **telecom_full**, from which we sample 60 — and these have a median of five simultaneous faults. The base agent and user simulator are gpt-4.1-mini; the online verifier is the cheaper gpt-4o-mini. It's API-only, no training. Metrics: pass@1, pass^k for reliability, the guidance-versus-agent failure split, and verifier token cost.

---

## Slide 9 — Five conditions

To attribute any effect cleanly, we run five conditions that all share the same base agent and differ **only at the hook**. **default** is the baseline. **action_verifier** checks the agent's *own* tool calls and does nothing to the guidance — that's the prior-art paradigm, and it shows that paradigm can't touch guidance failures. **self_verify** repairs the guidance with *no* policy grounding — that isolates the value of grounding. **guidance_verify** grounds the check but does *not* repair — so by construction it's a no-op on the message, an almost-control for default. And **guidance_verify_repair** is our full method. Because each rung turns off exactly one ingredient, we can say precisely where any gain — or any harm — comes from.

---

## Slide 10 — Finding 1: failures are guidance-induced

Now the results. Finding one is the motivation, and it holds. On the default baseline, **89% of failing tasks are guidance-induced** — 8 of the 9 distinct tasks that fail. If you count per trial instead, it's 93%, 14 of 15. I show both numbers deliberately: some tasks fail on every trial, so the per-trial number double-counts them — but even after de-duplicating to distinct tasks, guidance still dominates. The attribution isn't my guess; it comes from τ²-bench's ground truth — a failed check whose requestor is the user. So the premise is real: the dominant failure channel is exactly the agent-to-user guidance that prior blocking-based methods can't reach.

---

## Slide 11 — Finding 2: repair never beats default

Finding two is where the story turns. Across every condition on telecom_small, **repairing the guidance never beats the default agent.** Our full method ties the baseline at 0.825. And notice guidance_verify, the detect-only condition, reads 0.75 — *below* default. But that's the tell: guidance_verify never changes the message, so it *should* equal default exactly; the gap is pure sampling noise at temperature 0.7. When we doubled the trials for power, default at 0.79 still edged out repair at 0.78. So the headline intervention — the thing the whole project is built around — does not raise pass@1.

---

## Slide 12 — Finding 3: the oracle ceiling

Naturally, you ask: is that just a weak verifier or a weak prompt? So we built an **oracle upper bound**. We give repair every possible advantage — perfect recall by reviewing *every* message, a strong model doing the rewriting, and a perfect selector that, per task, keeps whichever outcome is better. No real verifier can beat this.

On the easy set, the headroom is **exactly zero** — default is already at 0.90, and the few remaining failures are timeouts, not guidance violations. On the realistic 60-task set, the ceiling is **+0.05** — repair genuinely fixes 3 real failures, but it *breaks* 6, so naive repair is net-negative, and even the perfect-selector ceiling is tiny. The conclusion: this is a **paradigm ceiling**, not a prompt or model bug. Improving the verifier cannot rescue it.

---

## Slide 13 — Analysis: limitations of our experiments

Let me be honest about the limitations of this study. **First, the sample is small and narrow** — only about 9 of our 20 tasks ever fail, so a difference of a couple of tasks sits inside the noise, and we have no confidence intervals. **Second, the noise is as big as the effect** — remember guidance_verify, the no-op control, swings ±0.05 from default just from sampling; that's the same size as the oracle headroom we were chasing. **Third, coverage is limited** — the full five-method comparison is only on the easy set; on the hard set we only have the oracle bound, and it's all one base agent, one domain. **And fourth, the users are simulated** — the user is itself an LLM, so its behaviour may not match how real people follow instructions. None of these overturn the conclusion, but they're the honest caveats around it.

---

## Slide 14 — Future work

So what would I try next? Four simple things. **One**, run more experiments across difficulty levels — actually run the real methods, not just the oracle, on the harder multi-fault tasks, with more trials and other domains. **Two**, adjust the architecture — move the check to the agent's plan or diagnosis, rather than the final guidance sentence. **Three**, make repair more conservative — only fire when the verifier is confident, so it stops breaking correct guidance. And **four**, a finer error analysis — trace which *step* in the conversation actually caused each failure, instead of only looking at the final outcome.

---

## Slide 15 — Thank you

To sum up in one line: **dual-control failures are guidance-induced, but repairing the guidance can't recover them — the real lever is the agent's diagnosis.** Thank you. I'm happy to take questions.

---

### Q&A — likely questions and short answers

- **"Isn't 89% just a few tasks?"** Yes — only 9 of 20 tasks ever fail, so it's a strong signal on a narrow base. That's why I report both task- and trial-level numbers and don't over-claim significance.
- **"Why is guidance_verify below default if it changes nothing?"** Exactly because it changes nothing — it should equal default. The gap is sampling noise at temperature 0.7, and it usefully marks the experiment's noise floor.
- **"Did you try a stronger repair model?"** The oracle already uses a strong model for the rewrite and still only nets +0.05, and most failures are timeouts or trajectory-level — so a stronger model can't lift the ceiling, only reduce the breakage.
- **"What would make it work?"** A setting where failures are genuinely single-message policy violations, or — more realistically — moving the intervention to the agent's diagnosis rather than its wording.
