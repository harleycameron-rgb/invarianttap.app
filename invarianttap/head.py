import json
from pathlib import Path

from ._log import read_head
from .origin import resolve_origin


def mint_head(
    jsonl: str | Path, block_id: str, *, origin: str | None = None
) -> dict:
    resolved_origin = resolve_origin(origin)
    next_seq, entry_hash = read_head(jsonl)
    head = {
        "schema_version": 1,
        "leg": "invarianttap",
        "origin": resolved_origin,
        "stage": "pre-super-block",
        "root_target": "sentinel_dot",
        "mode": "sha256",
        "block_id": block_id,
        "hash": entry_hash,
        "next_seq": next_seq,
    }
    payload = json.dumps(head, sort_keys=True, indent=2) + "\n"
    with Path(str(jsonl) + ".head.json").open("x", encoding="utf-8") as stream:
        stream.write(payload)
    return head
