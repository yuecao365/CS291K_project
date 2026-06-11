r"""ORACLE UPPER-BOUND TEST for guidance repair.

Question this answers (and ONLY this): is the disappointing result of
`guidance_verify_repair` a PARADIGM ceiling (repair fundamentally can't recover the
guidance failures) or a VERIFIER-quality problem (my cheap gpt-4o-mini verifier +
prompt has low recall, so it never fires on the messages that matter)?

Design -- per task, at temperature=0 (so vanilla is deterministic and the repair arm
diverges ONLY because of the rewrite, isolating the repair effect):
  A = vanilla            : identity hook, no repair.
  B = repair-all (oracle): EVERY agent->user message is sent to repair (perfect
                           RECALL, no verifier gating), using the STRONG base model
                           (gpt-4.1-mini) + all HARD rules (best repair QUALITY).
  ORACLE = max(A, B) per task : a perfect SELECTOR keeps whichever rollout succeeds
                           (cancels B's over-repair harm).

Read-out:
  oracle_pass@1 ~= vanilla_pass@1  -> ceiling. Repair can't help. Negative result holds; write it.
  oracle_pass@1  >  vanilla_pass@1 -> headroom exists. Bottleneck is the verifier
                                      (recall/precision = the prompt+model). Worth fixing.

Run (key must be in THIS shell):
  $env:PYTHONUTF8="1"; $env:OPENAI_API_KEY="sk-..."; python scripts/oracle_repair.py
Options:
  python scripts/oracle_repair.py --trials 1 --limit 20 --temp 0.0
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents import tau2_adapter as tau2
from src.llm import LLMClient
from src.verifier.rubric_extractor import load_rubric, render_rubric

DOMAIN = "telecom"
TASK_SET = "telecom_small"
RUBRIC_PATH = "configs/rubrics/telecom.json"
BASE_MODEL = "gpt-4.1-mini"          # same base agent as the main experiment
REPAIR_MODEL = "gpt-4.1-mini"        # STRONG repair model: we want the ceiling, not the cheap impl
MAX_STEPS = 100
OUT_CSV = "results/oracle_repair.csv"

# Perfect-recall, rule-grounded, best-effort repair. Reviews EVERY guidance message; if it
# already complies (or no rule applies) it must return the message unchanged.
ORACLE_REPAIR_PROMPT = """You are reviewing ONE message a telecom customer-service AGENT is about to
send the USER, who will then act on it. The USER (not the agent) performs the device actions.

HARD policy rules constraining what the agent may INSTRUCT the user to do:
{rubric}

CONVERSATION SO FAR:
{transcript}

AGENT MESSAGE ABOUT TO BE SENT:
{message}

If -- given the conversation -- this message would cause the user to VIOLATE any rule above,
rewrite ONLY the instruction so it complies: add the missing precondition/check, fix the order,
or change what you ask the user to do. If the message already complies, or no rule's condition
actually holds here, return it UNCHANGED. Keep it natural and minimal. Do not mention this review.

Return ONLY the final message text the user should receive -- nothing else.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=1, help="rollouts per task (temp=0 -> 1 is enough)")
    ap.add_argument("--limit", type=int, default=None, help="first N tasks (deterministic, after sort)")
    ap.add_argument("--sample", type=int, default=None, help="RANDOM N tasks (use for telecom_full)")
    ap.add_argument("--task-set", default=TASK_SET, help="telecom_small (20) | telecom_full (2285)")
    ap.add_argument("--seed-tasks", type=int, default=0, help="sampling seed for --sample")
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--out", default=OUT_CSV)
    args = ap.parse_args()

    rubric = load_rubric(RUBRIC_PATH)
    rubric_str = render_rubric(rubric, hard_only=True)

    repair_client = LLMClient(model=REPAIR_MODEL, temperature=args.temp, max_tokens=1024)
    repair_call = repair_client.as_call()
    base_cfg = {"model": BASE_MODEL, "temperature": args.temp}

    def identity_hook(message, transcript):
        return message, None

    def oracle_hook(message, transcript):
        prompt = ORACLE_REPAIR_PROMPT.format(rubric=rubric_str, transcript=transcript, message=message)
        fixed = repair_call(prompt).strip()
        return (fixed or message), None

    if args.sample:                       # random subset (representative of the real distribution)
        tasks = tau2.load_tasks(args.task_set, num=args.sample, seed=args.seed_tasks)
    else:
        tasks = tau2.load_tasks(args.task_set)
        if args.limit:
            tasks = tasks[: args.limit]
    print(f"task_set={args.task_set} | running {len(tasks)} tasks x {args.trials} trial(s) "
          f"x 2 conditions = {len(tasks)*args.trials*2} episodes")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fcsv = open(args.out, "w", newline="", encoding="utf-8")
    w = csv.writer(fcsv)
    w.writerow(["condition", "task_id", "seed", "reward", "success", "incomplete"])

    # results[(task_id, seed)] = {"A": success_or_None, "B": ...}; None means incomplete/crash
    pair: dict[tuple[str, int], dict[str, bool | None]] = {}

    def run_one(cond, hook, task, tid, seed):
        sim, _ = tau2.run_episode(DOMAIN, task, seed, hook, base_cfg, max_steps=MAX_STEPS)
        reward, ri = tau2.get_reward(sim, task, DOMAIN)
        incomplete = tau2.is_incomplete(sim, ri)
        success = (reward >= 1.0)
        w.writerow([cond, tid, seed, reward, int(success), int(incomplete)])
        fcsv.flush()
        pair.setdefault((tid, seed), {})[cond] = (None if incomplete else success)
        tag = "INCOMPLETE" if incomplete else ("SOLVED" if success else "FAILED")
        print(f"  [{cond:9}] seed={seed} -> {tag} (reward={reward})")
        return success, incomplete

    for i, task in enumerate(tasks):
        tid = str(getattr(task, "id", i))
        print(f"\n=== TASK {i} {tid[:60]} ===")
        for seed in range(args.trials):
            run_one("vanilla", identity_hook, task, tid, seed)
            run_one("repair_all", oracle_hook, task, tid, seed)

    fcsv.close()

    # ---- aggregate -----------------------------------------------------------
    keys = sorted(pair.keys())
    n = len(keys)

    def succ(cond):  # incomplete/None counts as NOT a success (standard pass@1)
        return [bool(pair[k].get(cond)) for k in keys]

    a = succ("vanilla")
    b = succ("repair_all")
    oracle = [a[i] or b[i] for i in range(n)]

    van_p = sum(a) / n if n else 0.0
    rep_p = sum(b) / n if n else 0.0
    ora_p = sum(oracle) / n if n else 0.0

    # The two diagnostic numbers that actually decide it:
    converted = sum(1 for i in range(n) if (not a[i]) and b[i])   # vanilla-fail -> repair fixes
    broken = sum(1 for i in range(n) if a[i] and (not b[i]))      # vanilla-ok  -> repair breaks
    van_fails = sum(1 for i in range(n) if not a[i])

    tok = repair_client.usage.total_tokens
    # gpt-4.1-mini approx: $0.40/M in, $1.60/M out; use a blended ~$0.8/M as a rough upper guess.
    cost_est = (repair_client.usage.prompt_tokens * 0.40 + repair_client.usage.completion_tokens * 1.60) / 1e6

    print("\n" + "=" * 64)
    print(f"ORACLE UPPER-BOUND  (n={n} task-seeds, temp={args.temp}, repair_model={REPAIR_MODEL})")
    print("=" * 64)
    print(f"  vanilla     pass@1 : {van_p:.3f}")
    print(f"  repair_all  pass@1 : {rep_p:.3f}   (perfect recall, NO selector -- may be < vanilla)")
    print(f"  ORACLE      pass@1 : {ora_p:.3f}   (max per task = perfect selector)")
    print(f"  >>> HEADROOM (oracle - vanilla): {ora_p - van_p:+.3f}")
    print("-" * 64)
    print(f"  vanilla failures           : {van_fails}/{n}")
    print(f"  ... repair CONVERTED to win : {converted}   (these are the recoverable ones)")
    print(f"  vanilla wins repair BROKE   : {broken}   (over-repair harm the selector hides)")
    print("-" * 64)
    print(f"  repair tokens: {tok:,}   (~${cost_est:.2f} on {REPAIR_MODEL})")
    print("=" * 64)
    if ora_p - van_p >= 0.0499:           # tolerance: avoid the 0.04999.. float-boundary artifact
        print("VERDICT: HEADROOM EXISTS -> the bottleneck is the verifier (recall/precision =")
        print("         the prompt + model). The negative result was premature; fixing the")
        print("         verifier is worth it. Next: improve VERIFY_PROMPT / stronger verifier.")
    else:
        print("VERDICT: NO MEANINGFUL HEADROOM -> even a perfect verifier+repair can't recover")
        print("         these failures. This is a PARADIGM ceiling, not a prompt bug. The")
        print("         negative result is real and publishable. Next: write it up honestly.")
    print(f"\nrows -> {args.out}")


if __name__ == "__main__":
    main()
