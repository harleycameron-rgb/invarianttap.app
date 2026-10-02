import json
import re
from pathlib import Path


GENESIS_HASH = "0" * 64


def valid_hash(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def read_head(path: str | Path) -> tuple[int, str]:
    next_seq, entry_hash = 0, GENESIS_HASH
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            entry = json.loads(line)
            if not isinstance(entry, dict):
                raise ValueError(f"line {line_number}: expected an object")
            seq = entry.get("seq")
            if type(seq) is not int or seq != next_seq:
                raise ValueError(f"line {line_number}: expected seq {next_seq}")
            entry_hash = entry.get("entry_hash")
            if not valid_hash(entry_hash):
                raise ValueError(f"line {line_number}: invalid entry_hash")
            next_seq += 1
    return next_seq, entry_hash
