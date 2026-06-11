"""Robust JSON extraction from LLM output.

Small models (Qwen 7B) often wrap JSON in prose or ```json fences, or emit a
trailing comma. This pulls out the first balanced JSON object/array and parses it,
tolerating the common failure modes. Used by the rubric extractor and the verifier.
"""
from __future__ import annotations

import json
import re


def _strip_fences(text: str) -> str:
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    return m.group(1) if m else text


def _first_balanced(text: str) -> str | None:
    """Return the first balanced {...} or [...] span (string-aware)."""
    start = None
    for i, ch in enumerate(text):
        if ch in "{[":
            start = i
            open_ch, close_ch = ch, ("}" if ch == "{" else "]")
            break
    if start is None:
        return None
    depth, in_str, esc = 0, False, False
    for j in range(start, len(text)):
        ch = text[j]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return text[start:j + 1]
    return None


def _salvage_array(text: str):
    """Rescue the complete leading objects from a truncated JSON array.
    `[{...},{...},{..` -> [obj1, obj2]. Returns None if nothing complete is found."""
    inner = _strip_fences(text)
    start = inner.find("[")
    if start == -1:
        return None
    objs, depth, in_str, esc, obj_start = [], 0, False, False, None
    for i in range(start + 1, len(inner)):
        ch = inner[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                obj_start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and obj_start is not None:
                try:
                    objs.append(json.loads(inner[obj_start:i + 1]))
                except json.JSONDecodeError:
                    pass
                obj_start = None
    return objs or None


def _quote_bare_tokens(s: str) -> str:
    """Rescue small-model JSON that emits bare identifiers as array elements or values,
    e.g. {"violated_rule_ids":[R1, R2]} -> {"violated_rule_ids":["R1","R2"]}. Only touches
    unquoted tokens that sit where a value is expected (after [ , or :)."""
    return re.sub(r'(?<=[\[,:])(\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*)(?=[,\]\}])',
                  lambda m: f'{m.group(1)}"{m.group(2)}"{m.group(3)}'
                  if m.group(2) not in ("true", "false", "null") else m.group(0),
                  s)


def parse_json(text: str):
    """Best-effort parse. Raises ValueError if nothing parseable is found."""
    candidate = _first_balanced(_strip_fences(text)) or text.strip()
    no_trailing = re.sub(r",(\s*[}\]])", r"\1", candidate)
    for attempt in (candidate, no_trailing, _quote_bare_tokens(no_trailing)):
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            continue
    salvaged = _salvage_array(text)          # handle truncated arrays (e.g. max_tokens cutoff)
    if salvaged:
        return salvaged
    raise ValueError(f"Could not parse JSON from model output:\n{text[:500]}")
