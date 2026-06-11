# Running locally with Qwen on a remote AutoDL GPU

Architecture: **AutoDL = GPU inference server only.** Your code, τ²-bench, and the
verifier all run on local Windows. An SSH tunnel maps the remote Qwen port to a
local port, so `base_url=http://127.0.0.1:8000/v1` "just works".

```
LOCAL (Windows)                              AutoDL (remote)
  run.py / base_agent  ── SSH tunnel ──►  vLLM Qwen2.5-7B on :6006
  tau2-bench (tasks/scoring)
  verifier ── public internet ──► OpenAI API
```

## 1. AutoDL: serve Qwen (in `tmux` so it survives SSH disconnect)

In China, do NOT pull from HuggingFace directly. Either:
```bash
source /etc/network_turbo                 # AutoDL academic acceleration (HF), OR
pip install modelscope && modelscope download --model Qwen/Qwen2.5-7B-Instruct --local_dir /root/qwen
```
Then:
```bash
pip install vllm
tmux new -s qwen
python -m vllm.entrypoints.openai.api_server \
  --model /root/qwen --served-model-name Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 --port 6006 --dtype bfloat16
# detach: Ctrl-b then d
```

## 2. Local Windows: open the SSH tunnel (keep this PowerShell window open)
```powershell
ssh -p <ssh_port> -N -o ServerAliveInterval=60 `
    -L 8000:127.0.0.1:6006 root@<autodl_host>
```
`-L 8000:127.0.0.1:6006` = local 8000 → remote 6006 (Qwen). `default.yaml` already
points `base_model.base_url` at `http://127.0.0.1:8000/v1`, so no config change needed.

## 3. Verify
```powershell
python scripts/check_remote.py     # should print a reply + token usage
```

---

## Caveats (read before a full run)

- **Does τ²-bench install on Windows?** It's the one unknown. If `pip install -e .`
  fails on Windows (Unix-only deps), use **Fallback B** below instead of fighting it.
- **OpenAI from China.** The verifier calls OpenAI over the public internet; from a
  China network you likely need a proxy/VPN, or set the verifier to a domestic
  endpoint. Quick alternative for early dev: point `verifier_model` at the *same*
  Qwen tunnel (a "cheap verifier" ablation you'd report anyway).
- **Latency.** Every dialogue turn round-trips local↔AutoDL. Fine for correctness;
  for big sweeps it's slower than running on-box (see Fallback B).
- **Spot instances can be reclaimed** mid-run — checkpoint results per task to
  `results/` so a kill doesn't lose everything.
- **Shut the instance down** when idle; AutoDL bills by the hour.

## Fallback B — run everything on AutoDL (if Windows install is painful)

Put the repo + τ²-bench + Qwen all on AutoDL; run `run.py` there inside `tmux`.
Then `base_url=http://127.0.0.1:6006/v1` locally→remote becomes just `:6006` on-box,
no tunnel, lowest latency. Only the verifier still needs outbound internet. You edit
code locally and `scp`/`git pull` to the box. This is the most robust option for the
final big runs; use the tunnel setup above for quick local iteration.
