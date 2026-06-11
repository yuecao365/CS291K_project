# Guidance-Level Policy Verification in Dual-Control Tool Agents

This repository contains a CS291K course project on verification for dual-control
tool agents. In many support and operations workflows, the agent does not directly
perform every consequential action. Instead, it observes the situation, reasons
about the next step, and instructs a user, human operator, or another agent to act.
In this setting, checking only the agent's own tool calls can miss failures caused
by bad user-facing guidance.

The project studies whether verifier feedback can be moved from structured tool
calls to the guidance channel. The main empirical finding is bounded: user-side
guidance is a meaningful failure-attribution channel in tau2 Telecom, but checking
and rewriting only the final natural-language message is often too local to
reliably improve outcomes. The experiments motivate verifying the planned user
action, its preconditions, and its supporting evidence before the final instruction
is written.

## Repository Contents

```text
src/
  agents/        tau2 adapter and guidance interception hook
  verifier/      policy-to-rubric extraction and guidance verifier prompts
  eval/          metrics and evaluation runner
  llm/           provider-agnostic LLM client with token accounting
  methods.py     verifier, repair, self-revise, placebo, and epistemic variants

scripts/         experiment runners, diagnostics, aggregation, and report builder
configs/         model, task, rubric, and experiment configs
results/         CSV summaries and full trace JSON files from local experiments
tests/           offline/unit tests for parsing, hooks, and metrics
docs/            setup notes, experiment plan, and report notes
ppt/             presentation source and slide deck
Report.docx      final written report
```

## Benchmark Dependency

This repository does not vendor the external benchmark checkout. Install
`tau2-bench-verified` separately:

```powershell
git clone https://github.com/amazon-agi/tau2-bench-verified
cd tau2-bench-verified
pip install -e .
```

Then return to this project directory and install this project's Python
dependencies:

```powershell
pip install -r requirements.txt
```

The code imports the installed `tau2` package through `src/agents/tau2_adapter.py`;
it does not require the benchmark repository to be committed inside this repo.

## API Keys

The configs read model credentials from environment variables. Do not put real
API keys in YAML files.

```powershell
$env:OPENAI_API_KEY = "..."
```

## Main Experiment Commands

Run one method from a config:

```powershell
python scripts/run_ablation.py --config configs/report_micro.yaml --mode vanilla
python scripts/run_ablation.py --config configs/report_micro.yaml --mode gt
python scripts/run_ablation.py --config configs/report_micro.yaml --mode gtrepair_gated
python scripts/run_ablation.py --config configs/report_micro.yaml --mode selfrevise
python scripts/run_ablation.py --config configs/report_micro.yaml --mode placebo
```

Run the report micro batch:

```powershell
python scripts/run_report_micro.py
```

Summarize result CSVs:

```powershell
python scripts/report_table.py results/report_micro_vanilla.csv results/report_micro_gt.csv results/report_micro_gtrepair_gated.csv
```

## Results and Traces

The `results/` directory contains:

- CSV summaries used in the report.
- `results/traces/`, full JSON traces for the local runs.

The trace files are included to make the error analysis auditable. They contain
complete simulated conversations and model/tool metadata, so they are useful for
debugging verifier behavior but should be treated as experiment artifacts rather
than minimal reproduction assets.

## Notes

- `tau2-bench-verified/`, `.venv/`, `ppt/node_modules/`, cache directories, and
  generated slide renders are intentionally ignored.
- The project does no training; all experiments are API/runtime evaluations.
- See `docs/REPORT_EXPERIMENT_PLAN.md` and `docs/REPORT_DRAFT.md` for the
  experiment narrative and reporting notes.
