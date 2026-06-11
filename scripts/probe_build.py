"""Live probe: actually construct a telecom environment via the registry and print
the exact API we need to finalize tau2_adapter.py (env constructor, tool/policy
accessors, agent/user constructor signatures, task fields, EvaluationType values).

Run on the box (no model calls, free):
    cd ~/Project && python scripts/probe_build.py 2>&1 | tee build_api.txt
Paste build_api.txt back.
"""
from __future__ import annotations

import inspect

DOMAIN = "telecom"


def sig(obj):
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return "(?)"


def publics(obj):
    return [n for n in dir(obj) if not n.startswith("_")]


def main():
    from tau2.registry import registry

    print("== registry constructors ==")
    env_ctor = registry.get_env_constructor(DOMAIN)
    print("get_env_constructor(telecom) ->", env_ctor, sig(env_ctor))
    try:
        agent_ctor = registry.get_agent_constructor("llm_agent")
        print("agent_ctor llm_agent ->", agent_ctor, sig(agent_ctor))
    except Exception as e:
        print("agent_ctor FAIL:", e)
    try:
        user_ctor = registry.get_user_constructor("user_simulator")
        print("user_ctor user_simulator ->", user_ctor, sig(user_ctor))
    except Exception as e:
        print("user_ctor FAIL:", e)

    print("\n== build environment ==")
    env = None
    for kwargs in ({}, {"solo_mode": False}):
        try:
            env = env_ctor(**kwargs)
            print(f"env_ctor(**{kwargs}) OK -> {type(env).__name__}")
            break
        except Exception as e:
            print(f"env_ctor(**{kwargs}) FAIL: {type(e).__name__}: {e}")
    if env is not None:
        print("env public methods/attrs:", publics(env))
        for name in ("get_tools", "get_agent_tools", "tools", "get_user_tools",
                     "get_policy", "policy", "get_domain_policy"):
            if hasattr(env, name):
                v = getattr(env, name)
                try:
                    val = v() if callable(v) else v
                    desc = f"len={len(val)}" if hasattr(val, "__len__") else type(val).__name__
                    print(f"  env.{name}{'()' if callable(v) else ''} -> {desc}")
                except Exception as e:
                    print(f"  env.{name} call FAIL: {e}")

    print("\n== tasks ==")
    from tau2.run import load_tasks
    for ts in ("telecom_small", "telecom"):
        try:
            tasks = load_tasks(ts)
            print(f"load_tasks({ts!r}) -> {len(tasks)} tasks")
        except Exception as e:
            print(f"load_tasks({ts!r}) FAIL: {e}")
    try:
        t = load_tasks("telecom_small")[0]
        print("first task id:", getattr(t, "id", None))
        print("user_scenario type:", type(getattr(t, "user_scenario", None)).__name__)
        print("initial_state type:", type(getattr(t, "initial_state", None)).__name__)
        print("evaluation_criteria type:", type(getattr(t, "evaluation_criteria", None)).__name__)
    except Exception as e:
        print("task field probe FAIL:", e)

    print("\n== EvaluationType members ==")
    try:
        from tau2.evaluator.evaluator import EvaluationType
        print([m for m in dir(EvaluationType) if not m.startswith("_")])
    except Exception as e:
        print("EvaluationType FAIL:", e)

    print("\n== Orchestrator.initialize source hint ==")
    try:
        from tau2.orchestrator.orchestrator import Orchestrator
        print("Orchestrator.__init__", sig(Orchestrator.__init__))
    except Exception as e:
        print("Orchestrator FAIL:", e)


if __name__ == "__main__":
    main()
