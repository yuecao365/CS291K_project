"""Self-contained test of the verifier JSON robustness fixes (no API)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.json_parse import parse_json
from src.verifier.guidance_verifier import _parse_verdict

# 1. bare-identifier array elements (the exact gpt-4o-mini failure)
a = parse_json('{"ok":false,"violated_rule_ids":[R1],"rationale":"x"}')
assert a["violated_rule_ids"] == ["R1"], a
b = parse_json('{"ok":false,"violated_rule_ids":[R1, R2, R3],"rationale":"y"}')
assert b["violated_rule_ids"] == ["R1", "R2", "R3"], b
# 2. already-valid JSON unchanged
c = parse_json('{"ok": true, "violated_rule_ids": ["R5"], "rationale": "ok"}')
assert c["violated_rule_ids"] == ["R5"], c
# 3. booleans/null not quoted by the rescue
d = parse_json('{"ok": false, "x": [true, false, null]}')
assert d["x"] == [True, False, None], d

# 4. verdict parser: fail OPEN on garbage, never raise
g = _parse_verdict("total garbage not json")
assert g.ok is True and g.violated_rule_ids == [], (g.ok, g.violated_rule_ids)
# 5. verdict parser: bare-token verdict parses to a real violation
v = _parse_verdict('{"ok":false,"violated_rule_ids":[R1],"rationale":"x"}')
assert v.ok is False and v.violated_rule_ids == ["R1"], (v.ok, v.violated_rule_ids)

print("ALL PARSE TESTS PASS")
