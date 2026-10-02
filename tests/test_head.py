import json
import subprocess
import sys
from pathlib import Path

import pytest

from invarianttap.head import mint_head
from invarianttap.origin import OriginMissing, resolve_origin


ROOT = Path(__file__).resolve().parents[1]


def _seed_jsonl(path: Path, entries: int = 3):
    with path.open("w", encoding="utf-8") as stream:
        for i in range(entries):
            stream.write(json.dumps({"seq": i, "entry_hash": f"{i:064x}"}) + "\n")


def _verify(path, seq, entry_hash):
    return subprocess.run(
        [sys.executable, "-m", "invarianttap.verify", str(path),
         "--expect-seq", str(seq), "--expect-hash", entry_hash],
        cwd=ROOT, capture_output=True, text=True,
    )


def test_head_requires_origin(monkeypatch, tmp_path):
    monkeypatch.delenv("INVARIANTTAP_ORIGIN", raising=False)
    with pytest.raises(OriginMissing):
        resolve_origin(None)
    jsonl = tmp_path / "s.jsonl"
    _seed_jsonl(jsonl)
    with pytest.raises(OriginMissing):
        mint_head(jsonl, "block-1")
    assert not Path(str(jsonl) + ".head.json").exists()


def test_head_schema_v2(tmp_path):
    jsonl = tmp_path / "s.jsonl"
    _seed_jsonl(jsonl)
    head = mint_head(jsonl, "block-1", origin="origin-test")
    assert head == {
        "schema_version": 1,
        "leg": "invarianttap",
        "origin": "origin-test",
        "stage": "pre-super-block",
        "root_target": "sentinel_dot",
        "mode": "sha256",
        "block_id": "block-1",
        "hash": f"{2:064x}",
        "next_seq": 3,
    }
    assert json.loads(Path(str(jsonl) + ".head.json").read_text()) == head


def test_head_immutable(tmp_path):
    jsonl = tmp_path / "s.jsonl"
    _seed_jsonl(jsonl)
    mint_head(jsonl, "block-1", origin="origin-test")
    head_path = Path(str(jsonl) + ".head.json")
    first = head_path.read_text()
    with pytest.raises(FileExistsError):
        mint_head(jsonl, "block-1", origin="origin-test")
    assert head_path.read_text() == first


def test_verifier_exit_codes(tmp_path):
    jsonl = tmp_path / "s.jsonl"
    _seed_jsonl(jsonl)
    assert _verify(jsonl, 3, f"{2:064x}").returncode == 0
    assert _verify(jsonl, 99, f"{2:064x}").returncode == 1
    assert _verify(jsonl, 3, "0" * 64).returncode == 1
    assert _verify(tmp_path / "nope.jsonl", 1, "0" * 64).returncode == 2


def test_empty_log(tmp_path, monkeypatch):
    monkeypatch.setenv("INVARIANTTAP_ORIGIN", "environment-origin")
    jsonl = tmp_path / "s.jsonl"
    _seed_jsonl(jsonl, 0)
    head = mint_head(jsonl, "block-1")
    assert head["origin"] == "environment-origin"
    assert head["next_seq"] == 0
    assert head["hash"] == "0" * 64
    assert _verify(jsonl, 0, "0" * 64).returncode == 0


@pytest.mark.parametrize("content", [
    "{not json}\n",
    "[]\n",
    json.dumps({"seq": 1, "entry_hash": "0" * 64}) + "\n",
    json.dumps({"seq": False, "entry_hash": "0" * 64}) + "\n",
    json.dumps({"seq": 0, "entry_hash": "bad"}) + "\n",
    json.dumps({"seq": 0}) + "\n",
    "\n",
])
def test_invalid_log_creates_no_head(tmp_path, content):
    jsonl = tmp_path / "s.jsonl"
    jsonl.write_text(content)
    with pytest.raises(ValueError):
        mint_head(jsonl, "block-1", origin="origin-test")
    assert not Path(str(jsonl) + ".head.json").exists()
    assert _verify(jsonl, 1, "0" * 64).returncode == 2


@pytest.mark.parametrize("seq, entry_hash", [
    (-1, "0" * 64), (0, "bad"), (0, "G" * 64),
])
def test_invalid_expected_head(tmp_path, seq, entry_hash):
    jsonl = tmp_path / "s.jsonl"
    _seed_jsonl(jsonl)
    assert _verify(jsonl, seq, entry_hash).returncode == 2
