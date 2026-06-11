"""Provider-agnostic LLM client with token accounting.

One class talks to BOTH:
  * a local vLLM/Qwen server (OpenAI-compatible) -> the cheap base agent / user sim
  * a hosted API (OpenAI, or Anthropic via the openai-compatible shim) -> the verifier

Everywhere else in the codebase we pass around a plain `llm_call(prompt) -> str`
closure (see `.as_call()`), so modules stay decoupled from the SDK and are trivially
mockable in tests. The client tallies tokens so the cost-vs-accuracy curve is free.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    calls: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def add(self, p: int, c: int) -> None:
        self.prompt_tokens += p
        self.completion_tokens += c
        self.calls += 1


@dataclass
class LLMClient:
    """Thin wrapper over an OpenAI-compatible chat endpoint.

    For Qwen on AutoDL:  LLMClient(model="Qwen/Qwen2.5-7B-Instruct",
                                   base_url="http://<host>:8000/v1", api_key="EMPTY")
    For OpenAI:          LLMClient(model="gpt-4o-mini")  # reads OPENAI_API_KEY
    """
    model: str
    base_url: str | None = None
    api_key: str | None = None
    temperature: float = 0.0
    max_tokens: int = 1024
    usage: Usage = field(default_factory=Usage)
    _client: object = field(default=None, repr=False)

    def __post_init__(self):
        from openai import OpenAI  # imported lazily so tests w/o the dep still run
        key = self.api_key or os.environ.get("OPENAI_API_KEY", "EMPTY")
        self._client = OpenAI(api_key=key, base_url=self.base_url)

    def call(self, prompt: str, *, system: str | None = None, **overrides) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=overrides.get("temperature", self.temperature),
            max_tokens=overrides.get("max_tokens", self.max_tokens),
        )
        u = getattr(resp, "usage", None)
        if u is not None:
            self.usage.add(getattr(u, "prompt_tokens", 0) or 0,
                           getattr(u, "completion_tokens", 0) or 0)
        return resp.choices[0].message.content or ""

    def as_call(self, **defaults) -> Callable[[str], str]:
        """Return a bare `llm_call(prompt)->str` closure to inject into modules."""
        def _call(prompt: str) -> str:
            return self.call(prompt, **defaults)
        return _call
