"""Check every deterministic pattern shuffle in an InvariantTap sentinel_dot log.

    python tools/verify_patterns.py invarianttap-<time>.jsonl

Rule (derive v1): d = SHA-256(ascii(prev_log_hash) + "|soo:pattern|v1");
step i is on iff i == 0 or d[i] < 77. Run `sentinel_dot verify` first for chain integrity.
"""
import hashlib, json, sys

def derive(prev_hash: str, steps: int = 16) -> str:
    d = hashlib.sha256((prev_hash + "|soo:pattern|v1").encode("ascii")).digest()
    return "".join("1" if i == 0 or d[i] < 77 else "0" for i in range(steps))

def check(path: str):
    ok, n, bad = True, 0, []
    for line in open(path, encoding="utf-8"):
        e = json.loads(line)
        p = e.get("parameters", {})
        if e.get("action_type") != "soo:pattern" or p.get("derive") != "v1":
            continue
        n += 1
        want = derive(e["prev_log_hash"], len(p["pattern"]))
        if want != p["pattern"]:
            ok = False; bad.append((e["seq"], p["pattern"], want))
    return ok, n, bad

if __name__ == "__main__":
    ok, n, bad = check(sys.argv[1])
    for seq, got, want in bad:
        print(f"seq {seq}: logged {got} but chain derives {want}")
    print(f"{'OK' if ok else 'FAIL'}: {n} derived shuffle(s) checked")
    sys.exit(0 if ok else 1)
