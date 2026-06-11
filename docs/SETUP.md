# Setup (budget-conscious: API + AutoDL)

This project does **no training**. Two cost levers:
- **Base agent + user simulator** → run a small open model (Qwen2.5/Qwen3 7B) on a *spot* AutoDL GPU via an OpenAI-compatible server, so the many tokens of dual-control dialogue are cheap.
- **Verifier** → a stronger API model, called far fewer times. (Ablation: run the verifier on Qwen too, to see if a small verifier suffices.)

## 1. Get the benchmark

```bash
git clone https://github.com/amazon-agi/tau2-bench-verified
cd tau2-bench-verified
pip install -e .
```

(Read its README for the exact task-loading API and the Telecom domain entry point. The original `sierra-research/tau2-bench` has the same interface but uncorrected data — prefer the verified fork.)

## 2. Base model on AutoDL (cheap path)

On the AutoDL instance, serve Qwen with an OpenAI-compatible endpoint (vLLM):

```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct --port 8000 --dtype bfloat16
```

Point the agent/user-simulator base URL at `http://<autodl-host>:8000/v1`. Use a *spot* instance and shut it down between runs.

## 3. API keys (verifier + optional strong baseline)

Set environment variables (PowerShell):

```powershell
$env:OPENAI_API_KEY = "..."      # or ANTHROPIC_API_KEY
```

Keep verifier calls few: one verification (+ at most one repair) per agent turn that contains user-directed guidance.

## 4. Cost control — do this BEFORE any full run

1. **Smoke test:** run `vanilla` on 5 Telecom tasks end-to-end; confirm pass/fail scoring and the cost logger work.
2. **Subset:** fix a 50–100 task subset (seeded) and reuse it for every method — never compare across different subsets.
3. **Log tokens per task** from day one (`results/cost_log.csv`), so the cost–accuracy trade-off is free to produce later.

## 5. Reproducibility

- Pin model versions and `temperature`/`k` in `configs/`.
- Seed task subset selection.
- Record the exact `tau2-bench-verified` commit hash.
