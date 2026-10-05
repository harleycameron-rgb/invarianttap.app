"""Deterministic shuffle: JS derivePattern (inside the append queue) == Python derive(prev_log_hash)."""
import json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from verify_patterns import check, derive
sys.path.insert(0, str(ROOT / "tests"))
from reference_verifier import verify_log

JS = r"""
const { SentinelLog, derivePattern } = require(process.argv[1]);
(async () => {
  const log = new SentinelLog({ sender: "invarianttap" });
  await log.action("session_start", { app: "invarianttap" });
  const racing = [];
  for (let i = 0; i < 6; i++) {
    racing.push(log.action("ring", { id: i }));              // interleaved appends must not break binding
    racing.push(log.append("action", "soo:pattern", async prev => ({ via: "test", pattern: await derivePattern(prev), derive: "v1" })));
  }
  await Promise.all(racing);
  process.stdout.write(log.toJsonl());
})();
"""

def test_js_patterns_match_python(tmp_path):
    out = tmp_path / "p.jsonl"
    out.write_text(subprocess.check_output(["node", "-e", JS, str(ROOT / "sentinel_dot.js")], text=True))
    assert verify_log(str(out))[0]
    ok, n, bad = check(str(out))
    assert ok and n == 6, bad
    pats = [json.loads(l)["parameters"]["pattern"] for l in out.read_text().splitlines() if "soo:pattern" in l]
    assert len(set(pats)) > 1                                  # different heads -> different grooves

def test_tampered_pattern_detected(tmp_path):
    out = tmp_path / "p.jsonl"
    out.write_text(subprocess.check_output(["node", "-e", JS, str(ROOT / "sentinel_dot.js")], text=True))
    lines = out.read_text().splitlines(True)
    i = next(k for k, l in enumerate(lines) if "soo:pattern" in l)
    e = json.loads(lines[i]); p = e["parameters"]["pattern"]
    e["parameters"]["pattern"] = p[:5] + ("0" if p[5] == "1" else "1") + p[6:]
    lines[i] = json.dumps(e) + "\n"; out.write_text("".join(lines))
    assert not check(str(out))[0]

def test_derive_is_stable():
    assert derive("0" * 64) == derive("0" * 64) and derive("0" * 64)[0] == "1"
