"""tau2-bench binding layer (the ONLY file that imports tau2).

CONFIRMED against the installed fork (inspect + source):
  registry.get_env_constructor(domain)() -> Environment   (no args; policy baked in)
  Environment.get_policy() / .get_tools() / .get_user_tools()
  LLMAgent(tools, domain_policy, llm=None, llm_args=None);
    .generate_next_message(message, state) -> (AssistantMessage, state)
  UserSimulator(tools=None, instructions=..., llm=None, llm_args=None)
  Orchestrator(domain, agent, user, environment, task, max_steps=100, max_errors=10,
               seed=None, solo_mode=False, validate_communication=False).run() -> SimulationRun
  evaluate_simulation(simulation, task, evaluation_type, solo_mode, domain) -> RewardInfo
  SimulationRun.reward_info / .agent_cost / .user_cost
  RewardInfo.reward / action_checks / db_check / env_assertions  (agent-action)
            / communicate_checks / nl_assertions               (guidance)
  load_tasks(task_set_name) -> [Task];  Task.user_scenario / .initial_state / .id

The base agent (Qwen on local vLLM) is driven through LiteLLM:
  model='openai/<served-name>' + llm_args={api_base, api_key, temperature}.
Guidance interception preserves the agent's type (see base_agent.install_guidance_hook).
"""
from __future__ import annotations

import random
from typing import Any

from .base_agent import install_guidance_hook


# --- tasks ------------------------------------------------------------------

def load_tasks(task_set: str = "telecom", num: int | None = None, seed: int = 0) -> list[Any]:
    from tau2.run import load_tasks as _load
    try:
        tasks = list(_load(task_set))
    except TypeError:
        # Some task loaders (e.g. get_tasks_small) don't accept task_split_name, which the
        # tau2.run.load_tasks wrapper passes unconditionally. Call the loader directly.
        from tau2.registry import registry
        loader = registry.get_tasks_loader(task_set)
        tasks = list(loader())
    tasks.sort(key=lambda t: str(getattr(t, "id", t)))         # deterministic order
    if num is not None and num < len(tasks):
        tasks = random.Random(seed).sample(tasks, num)
    return tasks


# --- environment / policy ---------------------------------------------------

def _make_env(domain: str):
    from tau2.registry import registry
    return registry.get_env_constructor(domain)()             # no-arg constructor


def get_domain_policy(domain: str = "telecom") -> str:
    return _make_env(domain).get_policy()


# --- rollout ----------------------------------------------------------------

def _litellm(cfg: dict) -> tuple[str, dict]:
    """Map our base_model config -> (litellm model string, llm_args) for a vLLM endpoint."""
    model = cfg["model"]
    if cfg.get("base_url") and not model.startswith("openai/"):
        model = f"openai/{model}"                              # LiteLLM openai-compatible route
    llm_args = {k: v for k, v in {
        "api_base": cfg.get("base_url"),
        "api_key": cfg.get("api_key"),
        "temperature": cfg.get("temperature"),
    }.items() if v is not None}
    return model, llm_args


def run_episode(domain: str, task: Any, seed: int, hook, base_llm_cfg: dict,
                max_steps: int = 50, rl_retries: int = 4, rl_wait: float = 30.0) -> tuple[Any, list]:
    """Build env+agent+user fresh (so each trial gets clean state), install the guidance
    hook on the agent (type preserved), run one episode. Returns (simulation, records).

    On a rate-limit error (TPM/RPM throttling on a low-tier key) we sleep `rl_wait`s and
    retry the whole episode up to `rl_retries` times -- tau2's built-in 3 litellm retries
    aren't enough for sustained TPM limits. Other exceptions (e.g. ctx overflow) -> the
    episode is recorded as a crash (None sim), which the metrics count as `errored`."""
    import time

    from tau2.agent.llm_agent import LLMAgent
    from tau2.user.user_simulator import UserSimulator
    from tau2.orchestrator.orchestrator import Orchestrator

    model, llm_args = _litellm(base_llm_cfg)

    for attempt in range(rl_retries + 1):
        env = _make_env(domain)
        policy = env.get_policy()
        agent = LLMAgent(tools=env.get_tools(), domain_policy=policy, llm=model, llm_args=llm_args)
        user = UserSimulator(tools=env.get_user_tools(), instructions=task.user_scenario,
                             llm=model, llm_args=llm_args)
        records = install_guidance_hook(agent, hook)
        orch = Orchestrator(domain=domain, agent=agent, user=user, environment=env, task=task,
                            max_steps=max_steps, seed=seed)
        try:
            return orch.run(), records
        except Exception as e:             # noqa: BLE001
            name = type(e).__name__
            if "RateLimit" in name and attempt < rl_retries:
                wait = rl_wait * (attempt + 1)        # linear backoff: 30s, 60s, 90s, 120s
                print(f"[run_episode] rate-limited (attempt {attempt+1}/{rl_retries}); "
                      f"sleeping {wait:.0f}s...")
                time.sleep(wait)
                continue
            # ctx overflow / give-up after retries / any other error -> crash episode
            print(f"[run_episode] {name}: episode failed (reward=0). {str(e)[:160]}")
            return None, records
    return None, records


# --- reward + violation decomposition --------------------------------------

def _is_stub(ri: Any) -> bool:
    """The orchestrator attaches a stub reward_info (reward=0, reward_basis=None, all
    sub-checks null) when an episode terminates prematurely (MAX_STEPS). We can still
    score the FINAL state ourselves to learn *why* it failed."""
    if ri is None:
        return True
    d = ri.model_dump() if hasattr(ri, "model_dump") else dict(ri)
    if d.get("reward_basis"):
        return False
    return not any(d.get(k) for k in
                   ("env_assertions", "action_checks", "communicate_checks",
                    "nl_assertions", "db_check"))


def get_reward(sim: Any, task: Any, domain: str) -> tuple[float, Any]:
    """(reward in [0,1], RewardInfo). Prefer the orchestrator's reward_info when it is a
    real scored result; if it's a premature-termination stub, re-evaluate the final state
    deterministically (EnvType.ENV: db/env_assertions/action -- no LLM, no cost) so even a
    timed-out episode yields a decomposable failure. A None sim (crash) -> failed, no info."""
    if sim is None:
        return 0.0, None
    ri = getattr(sim, "reward_info", None)
    if ri is not None and getattr(ri, "reward", None) is not None and not _is_stub(ri):
        return float(ri.reward), ri
    from tau2.evaluator.evaluator import evaluate_simulation, EvaluationType
    et = getattr(EvaluationType, "ENV", None) or getattr(EvaluationType, "ALL", None) \
        or list(EvaluationType)[0]
    try:
        ri2 = evaluate_simulation(simulation=sim, task=task, evaluation_type=et,
                                  solo_mode=False, domain=domain)
        return float(getattr(ri2, "reward", 0.0)), ri2
    except Exception as e:                       # noqa: BLE001 -- evaluation of a partial sim
        print(f"[get_reward] re-eval failed ({type(e).__name__}: {str(e)[:120]}); using stub")
        return float(getattr(ri, "reward", 0.0) or 0.0), ri


def classify_violations(reward_info: Any, records: list, reward: float) -> tuple[bool, bool]:
    """Decompose a FAILED run into (agent_action_violation, guidance_violation).

    Grounded in the real RewardInfo structure (confirmed against a completed Telecom
    episode). The dual-control attribution signal is *who was responsible* for each
    failed check:
      - action_checks[i].action.requestor == "user"  -> the user took/omitted the action
      - env_assertions[i].env_assertion.env_type == "user" -> a user-side device/world state
      Both mean: the agent had to GUIDE the user to do it and failed -> guidance-induced.
      requestor/env_type == "assistant"/"agent" -> the agent's OWN action -> agent-action.
      communicate_checks / nl_assertions failed -> the agent's communication -> guidance.
      Our verifier flagging a hard violation on an agent->user message -> guidance.
    """
    if reward >= 1.0:
        return False, False
    flagged = any(getattr(getattr(r, "verdict", None), "ok", True) is False for r in records)
    if reward_info is None:
        # Episode crashed/overflowed -> no eval detail to attribute. Put it in NEITHER
        # bucket; it's tracked separately via the `errored` flag and reported as error_rate.
        return False, False

    d = reward_info.model_dump() if hasattr(reward_info, "model_dump") else dict(reward_info)
    user_fail = agent_fail = False

    for ck in (d.get("env_assertions") or []):
        if ck.get("met") is False:
            ea = ck.get("env_assertion") or {}
            if ea.get("env_type") == "user":
                user_fail = True
            else:
                agent_fail = True
    for ck in (d.get("action_checks") or []):
        if ck.get("action_match") is False:
            act = ck.get("action") or {}
            if act.get("requestor") == "user":
                user_fail = True
            else:
                agent_fail = True
    for key in ("communicate_checks", "nl_assertions"):   # about the agent's communication
        for ck in (d.get(key) or []):
            r = ck.get("reward")
            if ck.get("met") is False or (r is not None and r < 1.0):
                user_fail = True
    dbc = d.get("db_check")                                # final world state: ambiguous
    if isinstance(dbc, dict) and dbc.get("db_match") is False and not user_fail:
        agent_fail = True                                 # only blame the agent if no user-side fail

    guidance_violation = user_fail or flagged
    agent_action_violation = agent_fail and not guidance_violation
    # If nothing was decomposable (e.g. a MAX_STEPS timeout -> reward_basis=None and every
    # sub-check is null), DON'T default to agent_action -- that fabricates a signal. Leave
    # both False; the caller treats this as incomplete (see is_incomplete) and excludes it.
    return agent_action_violation, guidance_violation


def is_incomplete(sim: Any, reward_info: Any) -> bool:
    """True if the episode is not a scorable completed run: it crashed (sim is None) or it
    hit MAX_STEPS / otherwise produced no evaluable sub-checks (reward_basis None and all
    check lists empty). These must be excluded from the agent-vs-guidance decomposition."""
    if sim is None or reward_info is None:
        return True
    d = reward_info.model_dump() if hasattr(reward_info, "model_dump") else dict(reward_info)
    if d.get("reward_basis"):
        return False
    return not any(d.get(k) for k in
                   ("env_assertions", "action_checks", "communicate_checks",
                    "nl_assertions", "db_check"))


def sim_cost(sim: Any) -> float:
    """Base-model $ cost for the episode (agent+user). ~0 for local Qwen; the meaningful
    marginal cost of our method is the verifier tokens, tracked separately."""
    return float((getattr(sim, "agent_cost", 0) or 0) + (getattr(sim, "user_cost", 0) or 0))
