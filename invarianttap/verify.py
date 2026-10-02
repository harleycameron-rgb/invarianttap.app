"""Check a JSONL endpoint, not the cryptographic integrity of its entries."""

import argparse
import sys

from ._log import read_head, valid_hash


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl")
    parser.add_argument("--expect-seq", required=True, type=int)
    parser.add_argument("--expect-hash", required=True)
    args = parser.parse_args(argv)
    if args.expect_seq < 0 or not valid_hash(args.expect_hash):
        parser.error("expected sequence must be nonnegative and hash must be 64 lowercase hex digits")
    try:
        actual = read_head(args.jsonl)
    except (OSError, ValueError) as exc:
        print(f"Unable to read log: {exc}", file=sys.stderr)
        return 2
    if actual != (args.expect_seq, args.expect_hash):
        print("Log endpoint does not match the expected head", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
