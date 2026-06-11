# Guidance-Level Policy Verification in Dual-Control Tool Agents

## Abstract

Most policy-verification work for tool agents assumes a single-control setting: the agent proposes an action, a verifier checks that action, and unsafe tool calls can be blocked before execution. This project studies a different setting in `tau2-bench-verified`, where the user also performs actions on a shared environment. In this dual-control setting, the agent often cannot execute the critical action itself; it must guide the user to do so. I test whether an online verifier over the agent-to-user guidance channel can improve task completion by detecting and repairing bad instructions before the simulated user acts. The result is mostly negative but informative. Guidance-attributed failures are common, so the channel is real. However, external final-message repair does not improve pass@1 on the easy Telecom set, and an oracle repair upper bound shows little headroom: repair fixes a few failures but also breaks already-correct trajectories. The evidence suggests that final-message guidance repair is too late in the pipeline; the more promising target is verifying the agent's diagnosis or intended user-action plan before it writes the instruction.

## 1. Introduction

Tool-using agents are often evaluated and verified in settings where the agent is the only actor that can change the environment. In that single-control setting, policy verification has a natural intervention point: inspect the agent's tool call and block it if it violates a policy. This framing motivates approaches such as solver-aided verification, action-level verifiers, and post-hoc trajectory audits.

Dual-control environments change the problem. In `tau2-bench-verified`, especially the Telecom domain, both the agent and the user can act on the world. The agent controls service-provider tools such as customer lookup, bill status, and line configuration. The user controls device-side tools such as checking APN settings, toggling airplane mode, granting app permissions, or rebooting the phone. A task may fail not because the agent directly called a bad tool, but because it gave the user a bad or premature instruction.

This project asks whether a verifier can improve performance by checking the agent's natural-language guidance before it is delivered to the user. If the verifier predicts that the guidance violates a policy rule or asks the user to act before a required diagnostic step, the system can either rewrite the instruction externally or ask the base agent to revise its own message. This is different from blocking: the user will eventually act, so the only available intervention is constructive repair.

The initial hypothesis was that guidance-level verification should recover a meaningful part of the dual-control performance drop. The experiments do not support that optimistic version. They instead support a narrower conclusion: user-guidance is an important failure channel, but final-message repair is not an effective way to fix it in this benchmark slice.

## 2. Method

The system is implemented as a hook around the base `tau2` LLM agent. The hook intercepts only assistant messages that contain user-directed text and no tool calls. Tool-call turns are left untouched, so all methods share the same base agent and differ only in the guidance channel.

The verifier uses a cached guidance rubric extracted from the Telecom policy. The original rubric contains rules such as not asking the user to reset APN settings before confirming the current APN settings are wrong, and not asking the user to grant app permissions before checking current permissions. A later procedural version rewrites these rules as observable ordering constraints: before instructing a mutating user action, the transcript should show the relevant diagnostic step.

I implemented several conditions:

- `vanilla`: the base dual-control agent, with no guidance verifier.
- `guidance_verify`: policy-grounded verification, but no repair. This is a detect-only no-op control.
- `guidance_verify_repair`: policy-grounded verification followed by one external rewrite of the message.
- `gtrepair_gated`: oracle-plan agent plus guidance repair, gated so the verifier fires only on mutating user instructions.
- `guidance_verify_selfrevise`: procedural verifier plus self-revision, where the verifier critique is injected back to the base agent and the base agent regenerates the message.

The main integration point is `install_guidance_hook`, which patches `LLMAgent.generate_next_message` in place. This preserves the agent object's type, which is necessary because the `tau2` orchestrator type-checks participants. The hook records verifier verdicts and repairs so failure attribution can later distinguish agent-action failures from user-side guidance failures.

## 3. Experimental Setup

The benchmark is `tau2-bench-verified`, Telecom domain. Telecom is the right target because its tasks naturally require dual-control interaction: the agent must diagnose account and network state, while the user performs device-side checks and fixes.

The primary metrics are pass@1, pass^2, error rate, verifier token cost, and a failure decomposition. In a failed completed run, a failed expected action with `requestor=user` or a failed environment assertion with `env_type=user` is treated as guidance-attributed: the user-side state was not fixed, and the agent's job was to guide the user there. Crashes and max-step timeouts are counted as errors and are not forced into either action or guidance attribution.

The current evidence comes from three result groups:

1. `telecom_small`, a 20-task easy set, comparing vanilla, detect-only verification, and external repair.
2. Oracle repair experiments, where every guidance message is reviewed by a strong repair model and a perfect selector keeps the better of vanilla and repair-all.
3. Hard-task ablations, where an oracle-plan agent and a no-user/oracle-plan agent identify how much failure is due to planning versus dual-control user guidance.

Some hard-set self-revision results are not clean enough for headline claims. The balanced `.bak` files have high error rates, and the current non-backup vanilla hard file is unbalanced across tasks. I therefore treat those results as diagnostic evidence only.

## 4. Results

On `telecom_small`, external guidance repair does not improve task success. The vanilla run has pass@1 `0.787` and pass^2 `0.658`. The full external repair method has pass@1 `0.775` and pass^2 `0.600`, with a higher error rate and `1,256,156` verifier tokens. The detect-only condition also differs from vanilla even though it does not change delivered messages, which indicates that the easy-set experiment has nontrivial sampling noise and should not be over-interpreted.

The oracle repair experiments are more decisive. On the 20-task easy set, vanilla pass@1 is `0.900`, repair-all is `0.800`, and the oracle selector is still `0.900`, giving zero headroom. On a 60-task sample from `telecom_full`, vanilla is `0.250`, repair-all is `0.200`, and the oracle selector is `0.300`. This means the best possible selector over vanilla and repair-all gains only `+0.050`. Repair converts 3 failures to successes, but it breaks 6 successes. This is the central result: even when the verifier has perfect recall over all guidance messages, final-message rewriting has limited upside and meaningful downside.

The hard-task ablations explain why. On the 12-task hard set, the oracle-plan condition reaches pass@1 `0.708`, while the oracle-plan no-user condition reaches `1.000`. This means the base agent suffers from planning/diagnosis failures, but even with the correct plan there remains a dual-control gap caused by user-side execution and communication. The important point is that this gap is not necessarily fixable by rewriting the final message. The instruction may already be downstream of a wrong diagnosis, wrong ordering decision, or a trajectory-level failure that cannot be repaired locally.

The self-revision implementation remains inconclusive. The full hard-set backup results show high error rates for self-revision and placebo-revision runs, so I cannot rigorously claim whether self-repair helps or hurts. This is an implementation limitation, not a substantive negative result about self-repair in general.

## 5. Discussion

The original idea was plausible because dual-control moves risk from tool calls into natural-language instructions. The experiments confirm that guidance is a real failure channel: many completed failures are associated with user-side actions or user-side final state. However, the tested intervention is too local. A verifier that only sees the final user-facing instruction often cannot fix the upstream reason the instruction was bad.

There are three practical reasons final-message repair struggles. First, many failures are trajectory-level: the agent may have skipped a diagnostic step several turns earlier, not merely phrased the final instruction poorly. Second, repair can over-correct harmless instructions. The trace logs show frequent triggering on APN, permission, and roaming-related rules, but such triggers are not always causally connected to task success. Third, rewriting the sentence can disrupt the base agent's plan or confuse the user simulator, turning a previously successful trajectory into a failure.

The most defensible conclusion is therefore a negative one: in this implementation and benchmark slice, final-message guidance verification and repair does not improve task completion. The result is still useful because it identifies a better intervention point. Instead of verifying the final instruction, future work should verify the agent's diagnosis or intended sequence of user actions before the agent starts issuing device-side instructions.

## 6. Planned Micro Follow-Up

Before finalizing the report, I recommend one small follow-up on `configs/report_micro.yaml`, which uses the existing 4-task trace subset. The goal is not to run another broad benchmark, but to produce one clean hard-subset table. The subset is small but targeted: it contains three MMS tasks and one mobile-data task from `telecom_full`, with 5 to 9 simultaneous faults per task. The expected actions are mostly user-side device actions, so it directly stresses the dual-control guidance channel rather than generic assistant-side tool use.

The recommended modes are `vanilla`, `gt`, `gtrepair_gated`, and `selfrevise`, each with 4 trials. The key comparison is `gt` versus `gtrepair_gated`: if repair does not beat the oracle-plan baseline, then final guidance repair is not useful even after the planning bottleneck is reduced. `selfrevise` should be reported only if its error rate is low; otherwise it should remain an implementation limitation.

## 7. Conclusion

This project tested whether adding a guidance verifier can improve dual-control tool-agent performance. The answer from the current evidence is mostly no. Guidance failures exist and are important, but final-message repair is a weak intervention. Oracle repair has little headroom and breaks correct trajectories. The report should present this as a rigorous negative result and argue that dual-control verification should move upstream, from sentence-level repair to plan-level or diagnosis-level verification.
