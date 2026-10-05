"""Independent reference verifier for the sentinel_dot v0.2 JSONL format.

Written from the published format description, not copied from sentinel_dot, so this
public repo's tests run without the (private) library. When sentinel_dot is installed,
tests/test_cross_verify.py also checks against it.

Checks: every line is canonical JSON; required fields present, no unknown fields;
seq continuous from 0; prev_log_hash chains from GENESIS; entry_hash recomputes
(SHA-256, or HMAC-SHA256 with key); no floats in parameters; optional anchored head.
"""
import hashlib, hmac, json

GENESIS = "0" * 64
REQUIRED = {"seq", "msg_type", "sender", "round", "action_type", "parameters",
            "permission_token", "prev_log_hash", "entry_hash"}
OPTIONAL = {"signature", "key_id"}
MSG_TYPES = {"action", "rejection", "round_boundary", "malformed_rejection"}


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _no_floats(v) -> bool:
    if isinstance(v, float):
        return False
    if isinstance(v, list):
        return all(_no_floats(x) for x in v)
    if isinstance(v, dict):
        return all(isinstance(k, str) and _no_floats(x) for k, x in v.items())
    return True


def entry_hash(entry: dict, key: bytes | None = None) -> str:
    body = canonical({k: v for k, v in entry.items() if k not in {"entry_hash"} | OPTIONAL}).encode()
    return hmac.new(key, body, hashlib.sha256).hexdigest() if key else hashlib.sha256(body).hexdigest()


def verify_log(path: str, key: bytes | None = None, expected_head=None):
    issues, prev, seq = [], GENESIS, 0
    data = open(path, "rb").read()
    if data and not data.endswith(b"\n"):
        issues.append({"reason": "torn_final_line"})
    for i, raw in enumerate(data.split(b"\n")[:-1] if data.endswith(b"\n") else data.split(b"\n")):
        try:
            e = json.loads(raw)
        except ValueError:
            issues.append({"line": i, "reason": "unparsable"}); continue
        if raw.decode("utf-8", "replace") != canonical(e):
            issues.append({"line": i, "reason": "non_canonical_encoding"})
        keys = set(e)
        if not REQUIRED <= keys or keys - REQUIRED - OPTIONAL:
            issues.append({"line": i, "reason": "schema"}); continue
        if e["msg_type"] not in MSG_TYPES or not _no_floats(e["parameters"]):
            issues.append({"line": i, "reason": "schema"})
        if e["seq"] != seq:
            issues.append({"line": i, "reason": "seq_gap", "expected": seq})
        if e["prev_log_hash"] != prev:
            issues.append({"line": i, "reason": "chain_break"})
        if entry_hash(e, key) != e["entry_hash"]:
            issues.append({"line": i, "reason": "entry_hash_mismatch"})
        prev, seq = e["entry_hash"], e["seq"] + 1
    if expected_head is not None and (seq, prev) != tuple(expected_head):
        issues.append({"reason": "head_mismatch", "expected": list(expected_head), "found": [seq, prev]})
    return not issues, issues
