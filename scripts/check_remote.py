"""Connectivity check: is the tunneled Qwen endpoint reachable from local?

Run AFTER starting the SSH tunnel (docs/REMOTE.md):
    python scripts/check_remote.py

Prints the model's reply + token usage if the cheap path is wired, else a clear hint.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.llm import LLMClient

BASE_URL = "http://127.0.0.1:8000/v1"   # local end of the SSH tunnel
MODEL = "Qwen/Qwen2.5-7B-Instruct"      # must match vLLM --served-model-name


def main():
    try:
        c = LLMClient(model=MODEL, base_url=BASE_URL, api_key="EMPTY", max_tokens=64)
        reply = c.call("Reply with exactly: tunnel-ok")
        print("REPLY:", reply.strip())
        print("USAGE:", c.usage)
        print("\n✅ Qwen reachable through the tunnel.")
    except Exception as e:  # noqa: BLE001 - this is a diagnostic
        print(f"❌ Could not reach {BASE_URL}\n   {type(e).__name__}: {e}\n")
        print("Checklist:")
        print("  1. Is vLLM running on AutoDL (port 6006)?")
        print("  2. Is the SSH tunnel up?  ssh -p <port> -N -L 8000:127.0.0.1:6006 root@<host>")
        print("  3. Does --served-model-name match MODEL above?")
        sys.exit(1)


if __name__ == "__main__":
    main()
