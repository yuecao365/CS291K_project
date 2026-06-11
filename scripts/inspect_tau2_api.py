"""Print tau2-bench's real API surface, so we lock src/agents/tau2_adapter.py.

Run on the machine where tau2 is installed (independent of the Qwen download):
    cd tau2-bench-verified && pip install -e .   # if not already
    python /path/to/Project/scripts/inspect_tau2_api.py

Paste the output back; the 4 [CONFIRM] spots in tau2_adapter.py get fixed in minutes.
This script only READS signatures via `inspect`; it runs nothing and calls no model.
"""
from __future__ import annotations

import inspect


def show(obj, label=None):
    label = label or getattr(obj, "__name__", repr(obj))
    print(f"\n=== {label} ===")
    try:
        if inspect.isclass(obj):
            print("  __init__", inspect.signature(obj.__init__))
            # pydantic models: list declared fields explicitly
            fields = getattr(obj, "model_fields", None)
            if fields:
                print("  model_fields:", list(fields))
            for name, m in inspect.getmembers(obj, predicate=callable):
                if name.startswith("_"):
                    continue
                try:
                    print(f"  .{name}{inspect.signature(m)}")
                except (ValueError, TypeError):
                    print(f"  .{name}(...)")
        else:
            print("  signature", inspect.signature(obj))
    except (ValueError, TypeError) as e:
        print("  <no signature>", e)


def try_import(path):
    try:
        mod = __import__(path, fromlist=["*"])
        print(f"\n##### module OK: {path}")
        return mod
    except Exception as e:  # noqa: BLE001
        print(f"\n##### module FAIL: {path}  ({type(e).__name__}: {e})")
        return None


def main():
    # ---- facade in tau2.run: tasks, build_*, run_simulation, config -------
    run_mod = try_import("tau2.run")
    if run_mod:
        for fn in ("load_tasks", "get_tasks", "build_orchestrator", "build_agent",
                   "build_user", "build_environment", "run_simulation", "run_single_task"):
            obj = getattr(run_mod, fn, None)
            if obj is not None:
                show(obj, f"tau2.run.{fn}")
        for cfg_name in ("TextRunConfig", "RunConfig"):
            obj = getattr(run_mod, cfg_name, None)
            if obj is not None:
                show(obj, f"tau2.run.{cfg_name}")

    # ---- registry: how to get policy / tasks / env -----------------------
    reg_mod = try_import("tau2.registry")
    if reg_mod:
        reg = getattr(reg_mod, "registry", None)
        print("registry public attrs:",
              [n for n in dir(reg) if not n.startswith("_")] if reg else "no `registry` object")

    # ---- core classes / evaluator / enums --------------------------------
    for mod_path, names in [
        ("tau2.orchestrator.orchestrator", ["Orchestrator"]),
        ("tau2.agent.llm_agent", ["LLMAgent"]),
        ("tau2.user.user_simulator", ["UserSimulator"]),
        ("tau2.evaluator.evaluator", ["evaluate_simulation", "EvaluationType"]),
        ("tau2.data_model.simulation", ["SimulationRun", "RewardInfo", "CommunicationMode"]),
        ("tau2.data_model.tasks", ["Task"]),
    ]:
        mod = try_import(mod_path)
        if not mod:
            continue
        for n in names:
            obj = getattr(mod, n, None)
            if obj is not None:
                show(obj, f"{mod_path}.{n}")

    # ---- where does reward live on a SimulationRun? ----------------------
    sim_mod = try_import("tau2.data_model.simulation")
    if sim_mod and hasattr(sim_mod, "SimulationRun"):
        sr = sim_mod.SimulationRun
        fields = getattr(sr, "model_fields", None)
        print("\nSimulationRun fields:", list(fields) if fields else
              [n for n in dir(sr) if not n.startswith("_")])


if __name__ == "__main__":
    main()
