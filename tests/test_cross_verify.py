"""JS writer (sentinel_dot.js) -> Python reference verifier (sentinel_dot.verify_log)."""
import base64, json, os, subprocess, pathlib
import pytest
from sentinel_dot.log import verify_log

ROOT = pathlib.Path(__file__).resolve().parents[1]

def make(tmp_path, key=None):
    out = tmp_path / "log.jsonl"
    args = ["node", str(ROOT / "tests/make_log.mjs"), str(out)] + ([key] if key else [])
    head = json.loads(subprocess.check_output(args, text=True).strip())
    return out, (head[0], head[1])

@pytest.mark.parametrize("keyed", [False, True])
def test_js_log_verifies_in_python(tmp_path, keyed):
    key = os.urandom(32) if keyed else None
    out, head = make(tmp_path, base64.b64encode(key).decode() if key else None)
    ok, issues = verify_log(str(out), key=key, expected_head=head)
    assert ok, issues
    assert head[0] == 8  # 8 entries; raw float append was refused

def test_tamper_detected(tmp_path):
    out, head = make(tmp_path)
    lines = out.read_text().splitlines(True)
    lines[2] = lines[2].replace("812345", "812346")
    out.write_text("".join(lines))
    ok, issues = verify_log(str(out), expected_head=head)
    assert not ok

def test_truncation_detected(tmp_path):
    out, head = make(tmp_path)
    out.write_text("".join(out.read_text().splitlines(True)[:-1]))
    ok, _ = verify_log(str(out), expected_head=head)
    assert not ok

def test_wrong_key_rejected(tmp_path):
    out, head = make(tmp_path, base64.b64encode(os.urandom(32)).decode())
    ok, _ = verify_log(str(out), key=os.urandom(32), expected_head=head)
    assert not ok
