"""Capability-decomposition ablation: is the telecom bottleneck PLANNING or GUIDING the user?

Runs tau2's own agents on the SAME telecom_small subset our other runs use, no verifier:

  --mode vanilla : LLMAgent      (default dual-control; plan yourself + guide user)  -> baseline
  --mode gt      : LLMGTAgent    (ORACLE PLAN: gold steps injected; still must GUIDE the user)
  --mode solo    : LLMSoloAgent  (NO USER: agent does every action itself, info upfront)

Reading the result:
  * gt >> vanilla  -> a big chunk of failure was PLANNING (giving the plan fixes it).
  * gt ~ vanilla   -> planning was NOT the bottleneck; the gap is GUIDING the user.
  * solo >> gt     -> the model can plan+execute alone; the dual-control GUIDANCE channel is the wall.

Writes results/<out>_<mode>.csv in the cost_log schema so scripts/aggregate.py just works.

Run (venv active, key set):
  $env:PYTHONUTF8="1"
  .venv/Scripts/python.exe scripts/run_ablation.py --mode gt      --trials 4
  .venv/Scripts/python.exe scripts/run_ablation.py --mode solo    --trials 4
  .venv/Scripts/python.exe scripts/run_ablation.py --mode vanilla --trials 4   # same-config baseline
  .venv/Scripts/python.exe scripts/aggregate.py    # compare all CSVs in results/
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

import yaml

# allow `python scripts/run_ablation.py` (add project root so `import src` works)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents import tau2_adapter as tau2


def _build(mode, env, task, model, llm_args):
    """Return (agent, user, solo_mode) for the requested ablation mode."""
    from tau2.agent.llm_agent import LLMAgent, LLMGTAgent, LLMSoloAgent
    from tau2.user.user_simulator import UserSimulator, DummyUser

    policy = env.get_policy()
    if mode in ("vanilla", "selfrevise", "placebo", "epistemic"):
        # self-plan dual-control agent; verifier modes attach a guidance hook later.
        agent = LLMAgent(tools=env.get_tools(), domain_policy=policy, llm=model, llm_args=llm_args)
        user = UserSimulator(tools=env.get_user_tools(), instructions=task.user_scenario,
                             llm=model, llm_args=llm_args)
        return agent, user, False
    if mode in ("gt", "gtrepair", "gtrepair_gated", "gt_selfrevise", "gt_epistemic"):
        # Oracle plan: gold resolution steps are injected into the system prompt; the agent
        # still has to GUIDE the (real) user simulator through them. `gtrepair*` are identical
        # here -- the guidance verify+repair hook is attached later, in run_episode.
        agent = LLMGTAgent(tools=env.get_tools(), domain_policy=policy, task=task,
                           llm=model, llm_args=llm_args)
        user = UserSimulator(tools=env.get_user_tools(), instructions=task.user_scenario,
                             llm=model, llm_args=llm_args)
        return agent, user, False
    if mode == "solo":
        # No user: agent gets the ticket + ALL tools (assistant + user) and performs
        # every action itself. The orchestrator asserts env.solo_mode in solo runs.
        env.set_solo_mode(True)
        user_tools = env.get_user_tools() if env.user_tools else []
        agent = LLMSoloAgent(tools=env.get_tools() + user_tools, domain_policy=policy,
                             task=task, llm=model, llm_args=llm_args)
        user = DummyUser()
        return agent, user, True
    if mode == "gtsolo":
        # Absolute upper bound: ORACLE PLAN + NO USER. Solo agent (does everything itself,
        # no guidance friction) AND the gold resolution steps injected into its prompt.
        env.set_solo_mode(True)
        user_tools = env.get_user_tools() if env.user_tools else []
        agent = _GTSoloAgent(tools=env.get_tools() + user_tools, domain_policy=policy,
                             task=task, llm=model, llm_args=llm_args)
        user = DummyUser()
        return agent, user, True
    raise ValueError(mode)


def _GTSoloAgent(*args, **kwargs):
    """Solo agent whose system prompt also carries the gold resolution steps.

    Built lazily so tau2 imports stay inside call paths. In solo mode there is no
    user, so every gold action (assistant- OR user-side) is reframed as 'perform it
    yourself' -- the agent calls all tools directly.
    """
    from tau2.agent.llm_agent import (
        LLMSoloAgent, AGENT_SOLO_INSTRUCTION, SYSTEM_PROMPT_SOLO,
    )

    class LLMGTSoloAgent(LLMSoloAgent):
        @property
        def system_prompt(self) -> str:
            agent_instruction = AGENT_SOLO_INSTRUCTION.format(
                stop_function_name=self.STOP_FUNCTION_NAME, stop_token=self.STOP_TOKEN)
            steps = [
                f"[Step {i + 1}] Perform the following action: {a.get_func_format()}."
                for i, a in enumerate(self.task.evaluation_criteria.actions)
            ]
            base = SYSTEM_PROMPT_SOLO.format(
                agent_instruction=agent_instruction,
                domain_policy=self.domain_policy, ticket=self.task.ticket)
            return (base + "\n<resolution_steps>\n"
                    "These are the ground-truth steps that resolve the ticket. "
                    "Execute them in order with tool calls, then call `done`.\n"
                    + "\n".join(steps) + "\n</resolution_steps>")

    return LLMGTSoloAgent(*args, **kwargs)


def _solo_reward(sim, task, domain):
    """Score a solo episode with solo_mode=True (the dual-control re-eval path is wrong here)."""
    if sim is None:
        return 0.0, None
    ri = getattr(sim, "reward_info", None)
    if ri is not None and getattr(ri, "reward", None) is not None:
        return float(ri.reward), ri
    from tau2.evaluator.evaluator import evaluate_simulation, EvaluationType
    et = getattr(EvaluationType, "ALL", None) or list(EvaluationType)[0]
    ri2 = evaluate_simulation(simulation=sim, task=task, evaluation_type=et,
                              solo_mode=True, domain=domain)
    return float(getattr(ri2, "reward", 0.0)), ri2


def _wrap_trace(hook, sink):
    """Wrap a guidance hook so every agent->user message it sees is logged to `sink`
    (original text, delivered text, verdict). Lets --dump-traces show exactly what the
    verifier flagged and what repair rewrote it to."""
    def wrapped(message, transcript):
        action = hook(message, transcript)
        rec = getattr(action, "record", None)
        v = getattr(rec, "verdict", None)
        sink.append({
            "original": message,
            "kind": getattr(action, "kind", "keep"),
            "replacement": getattr(action, "text", None),
            "feedback": getattr(action, "feedback", None),
            "repaired": getattr(rec, "repaired", False),
            "revise_requested": getattr(action, "kind", "keep") == "revise",
            "verdict_ok": getattr(v, "ok", None),
            "violated_rule_ids": list(getattr(v, "violated_rule_ids", []) or []),
            "rationale": getattr(v, "rationale", ""),
        })
        return action
    return wrapped


def _dump_trace(out_dir, mode, tid, trial, sim, hook_log, records=None):
    """Persist one episode: full simulation (messages + reward_info + termination_reason)
    plus the per-message guidance/repair log and the EXECUTED revise outcomes.

    `revise_actions` counts what the installer actually did per intercepted turn
    (revise = regenerated, revise_suppressed = budget/dedup, revise_failed = regeneration
    threw and the draft was kept). This is the audit signal that the self-revision mechanism
    actually fired -- if every record is 'revise_failed', self-revise silently became vanilla."""
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9]+", "_", tid)[:80].strip("_")
    from collections import Counter
    actions = Counter(getattr(r, "action", "?") for r in (records or []))
    payload = {
        "mode": mode, "task_id": tid, "trial": trial,
        "termination_reason": str(getattr(sim, "termination_reason", None)),
        "n_messages": len(getattr(sim, "messages", []) or []) if sim is not None else 0,
        "reward": getattr(getattr(sim, "reward_info", None), "reward", None),
        "revise_actions": dict(actions),
        "guidance_log": hook_log,
        "simulation": sim.model_dump() if sim is not None else None,
    }
    path = out_dir / f"{safe}__trial{trial}.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def run_episode(mode, domain, task, seed, model, llm_args, max_steps, hook=None,
                rl_retries=4, rl_wait=30.0, trace=None):
    from tau2.orchestrator.orchestrator import Orchestrator
    from src.agents.base_agent import install_guidance_hook
    for attempt in range(rl_retries + 1):
        env = tau2._make_env(domain)
        agent, user, solo = _build(mode, env, task, model, llm_args)
        ep_hook = hook
        if trace is not None:
            trace.clear()                     # fresh per attempt (retries reset the log)
            if hook is not None:
                ep_hook = _wrap_trace(hook, trace)
        records = install_guidance_hook(agent, ep_hook)   # [] when hook is None
        orch = Orchestrator(domain=domain, agent=agent, user=user, environment=env, task=task,
                            max_steps=max_steps, seed=seed, solo_mode=solo)
        try:
            return orch.run(), records
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            # "exceeded your current quota" / insufficient_quota / billing == account out of
            # credit, NOT a transient throttle. Retrying just wastes 5 min of backoff per
            # episode, so fail fast; the row is recorded errored=1 -> purge_errored re-runs it.
            is_quota = any(s in msg.lower() for s in ("quota", "insufficient_quota", "billing"))
            if "RateLimit" in type(e).__name__ and not is_quota and attempt < rl_retries:
                wait = rl_wait * (attempt + 1)
                print(f"  rate-limited (attempt {attempt+1}); sleeping {wait:.0f}s...")
                time.sleep(wait)
                continue
            if is_quota:
                print(f"  [{mode}] QUOTA EXHAUSTED -- stop the run, top up, then re-run "
                      f"(purge_errored + foreach; resume-safe).")
            else:
                print(f"  [{mode}] episode failed (reward=0): {type(e).__name__}: {str(e)[:140]}")
            return None, records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True,
                    choices=["vanilla", "gt", "solo", "gtsolo", "gtrepair", "gtrepair_gated",
                             "selfrevise", "placebo", "gt_selfrevise",
                             "epistemic", "gt_epistemic"])
    ap.add_argument("--config", default="configs/openai.yaml")
    ap.add_argument("--task-set", help="override cfg task_set (e.g. telecom_full for the hard ids)")
    ap.add_argument("--trials", type=int)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--task-ids", help="JSON file with an explicit list of task_ids (overrides subset)")
    ap.add_argument("--out", default="results/cost_log_ablation")
    ap.add_argument("--dump-traces", action="store_true",
                    help="write full per-episode transcript + repair log to results/traces/<mode>/")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    domain, task_set = cfg["domain"], (args.task_set or cfg["task_set"])
    trials = args.trials or cfg["rollout"]["trials"]
    max_steps = cfg.get("max_steps", 50)
    model, llm_args = tau2._litellm(cfg["base_model"])
    base_seed = cfg["subset"]["seed"] * 1000

    ids_file = args.task_ids or cfg.get("task_ids_file")
    if ids_file:
        import json
        want = json.loads(Path(ids_file).read_text(encoding="utf-8"))
        by_id = {str(getattr(t, "id", t)): t for t in tau2.load_tasks(task_set)}
        tasks = [by_id[i] for i in want if i in by_id]
        missing = [i for i in want if i not in by_id]
        if missing:
            print(f"[ablation] WARNING: {len(missing)} task_ids not found in {task_set}")
        print(f"[ablation] using explicit task list: {len(tasks)} tasks from {ids_file}")
    else:
        tasks = tau2.load_tasks(task_set, num=cfg["subset"]["size"], seed=cfg["subset"]["seed"])
    if args.limit:
        tasks = tasks[:args.limit]
    method = f"ablation_{args.mode}"
    header = ["method", "task_id", "success", "errored", "agent_action_violation",
              "guidance_violation", "verifier_tokens"]
    out = f"{args.out}_{args.mode}.csv"
    Path(out).parent.mkdir(parents=True, exist_ok=True)

    # --- RESUME: keep rows of tasks already fully done (>= trials rows); drop partials ---
    from collections import Counter
    prior = []
    if Path(out).exists():
        with open(out, newline="", encoding="utf-8") as f:
            prior = [r for r in csv.reader(f)][1:]          # skip header
    cnt = Counter(r[1] for r in prior)
    done_ids = {tid for tid, c in cnt.items() if c >= trials}
    kept = [r for r in prior if r[1] in done_ids]           # full tasks only (de-dup partials)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(kept)
    n_pass = sum(int(r[2]) for r in kept); n_done = len(kept)
    todo = [t for t in tasks if str(getattr(t, "id", t)) not in done_ids]
    print(f"[ablation] mode={args.mode} domain={domain} task_set={task_set} model={model}")

    # gtrepair: oracle plan (LLMGTAgent) + our guidance verify+repair hook on the
    # agent->user channel. The fair test of the method -- plan is correct, so any gain
    # is pure guidance recovery (the gt->gtsolo 0.167 headroom).
    hook = vclient = None
    if args.mode in ("gtrepair", "gtrepair_gated"):
        from src.llm import LLMClient
        from src.verifier.rubric_extractor import load_rubric
        from src.methods import make_hook, make_gated_hook
        vclient = LLMClient(**cfg["verifier_model"])
        rubric = load_rubric(Path(cfg["paths"]["rubric"]))
        hook = make_hook("guidance_verify_repair", rubric, vclient.as_call())
        gated = ""
        if args.mode == "gtrepair_gated":
            # cheap binary gate: only run verify+repair on mutating-instruction messages
            hook = make_gated_hook(hook, vclient.as_call(max_tokens=5))
            gated = " + mutation-gate"
        print(f"[ablation] {args.mode}: {len(rubric)} rubric rules{gated}, "
              f"verifier={cfg['verifier_model']['model']}")
    elif args.mode in ("selfrevise", "placebo", "gt_selfrevise"):
        # procedure-grounded verify + self-revision (the new architecture). placebo fires on
        # the same trigger but with content-free feedback (resampling control).
        from src.llm import LLMClient
        from src.verifier.rubric_extractor import load_rubric
        from src.methods import make_hook
        vclient = LLMClient(**cfg["verifier_model"])
        proc_path = cfg["paths"].get("rubric_procedural", "configs/rubrics/telecom_procedural.json")
        rubric = load_rubric(Path(proc_path))
        method_name = "placebo_revise" if args.mode == "placebo" else "guidance_verify_selfrevise"
        hook = make_hook(method_name, rubric, vclient.as_call())
        print(f"[ablation] {args.mode}: {method_name}, {len(rubric)} procedural rules, "
              f"verifier={cfg['verifier_model']['model']}")
    elif args.mode in ("epistemic", "gt_epistemic"):
        from src.methods import make_hook
        hook = make_hook("epistemic_repair", rubric=[], verifier_call=None)
        print(f"[ablation] {args.mode}: epistemic prerequisite repair, deterministic verifier")
    print(f"[ablation] resume: {len(done_ids)} tasks already done, {len(todo)} to go "
          f"(trials={trials})")

    for i, task in enumerate(todo, 1):
        tid = str(getattr(task, "id", task))
        task_rows = []
        for ti in range(trials):
            v_before = vclient.usage.total_tokens if vclient else 0
            ep_trace = [] if args.dump_traces else None
            sim, recs = run_episode(args.mode, domain, task, base_seed + ti, model, llm_args,
                                    max_steps, hook=hook, trace=ep_trace)
            v_tok = (vclient.usage.total_tokens - v_before) if vclient else 0
            n_exec = sum(1 for r in (recs or []) if getattr(r, "action", "") == "revise")
            n_fail = sum(1 for r in (recs or []) if getattr(r, "action", "") == "revise_failed")
            if args.mode in ("selfrevise", "placebo", "gt_selfrevise"):
                print(f"      revise: executed={n_exec} failed={n_fail}"
                      + ("  <-- WARNING: revises FAILED (silent no-op!)" if n_fail and not n_exec else ""))
            if args.dump_traces:
                p = _dump_trace(Path("results/traces") / args.mode, args.mode, tid, ti,
                                sim, ep_trace or [], records=recs)
                print(f"    [trace] {p}")
            if args.mode in ("solo", "gtsolo"):
                reward, ri = _solo_reward(sim, task, domain)
                errored = sim is None
                a_viol = g_viol = False
            else:
                reward, ri = tau2.get_reward(sim, task, domain)
                a_viol, g_viol = tau2.classify_violations(ri, [], reward)
                errored = tau2.is_incomplete(sim, ri)
            ok = reward >= 1.0
            n_pass += int(ok); n_done += 1
            task_rows.append([method, tid, int(ok), int(errored), int(a_viol), int(g_viol), v_tok])
        # flush this task's rows immediately so an interruption keeps finished tasks
        with open(out, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(task_rows)
        print(f"  [{i}/{len(todo)}] {tid}  running pass@1={n_pass/max(n_done,1):.3f}")

    print(f"\n=== {method}: pass@1 = {n_pass}/{n_done} = {n_pass/max(n_done,1):.3f}  -> {out} ===")


if __name__ == "__main__":
    main()
