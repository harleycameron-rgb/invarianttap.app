# invarianttap.app

**Moiré Pad · Sky Fused**, woven to [sentinel_dot](https://github.com/harleycameron-rgb/sentinel_dot).

A single-page instrument: drag on the pad to drive two moiré gates (forward + mirror) that fire relocation rings at phase convergence; with Motion on, the inverted sky tracks the phone's view direction and **Sight Pole** fixes latitude from a sighted angle (no geolocation call).

## The weave

Every control action the app takes is appended to an in-memory **sentinel_dot hash chain** by `sentinel_dot.js`, a browser writer that is byte-compatible with the Python reference. Tap **Log ⤓** to export:

- `invarianttap-<time>.jsonl` — the chain
- `invarianttap-<time>.head.json` — the head `(next_seq, hash)` to anchor externally

```bash
pip install "sentinel_dot @ git+https://github.com/harleycameron-rgb/sentinel_dot"
sentinel_dot verify invarianttap-<time>.jsonl --expect-seq <N> --expect-hash <hash>
# (optionally) timestamp the head into Bitcoin
sentinel_dot anchor stamp invarianttap-<time>.jsonl
```

| Event | msg_type | action_type | parameters |
|---|---|---|---|
| page load | action | `session_start` | lock version, lock id, hash mode |
| button toggles | action | `toggle:mirror` / `solar` / `sky` / `fingertip` / `pause` / `motion` | new state |
| motion denied / skipped | rejection | `toggle:motion` | reason |
| lock slider (debounced 400 ms) | action | `lock_set` | section, key, value (string) |
| Sight Pole success | action | `sight_pole` | `lat_mdeg`, hemi, `az_mdeg` |
| Sight Pole refused | rejection | `sight_pole` | reason (+ az/alt in millidegrees) |
| ring fired | action | `ring` | gate, id, parent, plane, `moire_urad`, `coherence_ppm`, `dx_mpx`, `dy_mpx` |
| Reset | round_boundary | `round_end` | `{note: "reset"}` — closes the round |
| Log export | action | `export` | entry count (the export itself is logged) |

**Schema discipline.** sentinel_dot forbids floats so hashes are identical across runtimes; the app logs scaled integers (milli-degrees, micro-radians, ppm, milli-px) or fixed-point strings. `canonicalJson` in `sentinel_dot.js` reproduces Python's `json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=True)` exactly, including `\uXXXX` escaping of DEL and non-ASCII.

**Never-list preserved.** Raw `alpha/beta/gamma` and accelerometer values are never logged — only derived, user-initiated results (sighting outcome, ring geometry).

**No persistence, no network.** The chain lives in memory until you export it.

### Keyed mode (HMAC-SHA256)

By default entries are plain SHA-256 (accident / edit detection; anyone can recompute). For forgery resistance open the app with a key in the URL fragment (fragments are never sent to a server):

```
index.html#key=<output of `sentinel_dot keygen`>
```

and verify with `--key-env SENTINEL_DOT_KEY`. Public-key (Ed25519 / ML-DSA) signing is not done in the browser; re-sign an exported log with `sentinel_dot migrate --signing-key` if auditors need it.

## Files

- `index.html` — the app
- `sentinel_dot.js` — browser/Node writer for the sentinel_dot v0.2 log format
- `tests/` — Node writes a log (incl. unicode, a coerced float, a refused raw float, a round boundary); Python `verify_log` must accept it, and must reject tampering, truncation and a wrong key

```bash
pytest -q tests
```

## Changes vs. the uploaded build

- Fixed a pre-existing crash: `phase_A` / `phase_B` read `slice[0].x` on an empty slice when `findConvergence` probed plane 0, throwing on every gate tick early in a drag. Both now return 0 for slices shorter than 3 samples.

## SOO + Sextant-Lock

A bottom pull-tab (**SOO ▴**) opens the SOO control panels: Timing, Signal dynamics, Synth engine, Sextant, Visual.

- **State machine** `READY → ONSET → DRAG → FAILURE → RECOVERY → READY` (plus `TAP` for presses shorter than `tapWindow`). ONSET holds gate firing for `onsetBuffer` ms, which stops the instant-escape jump on touch. FAILURE triggers when the forward origin passes the leash radius; RECOVERY pulls the origins back by `recoveryRate` per tick and re-arms at 10% of the leash.
- **Sextant-lock** eases three real inputs: horizon (view altitude), solar (sun altitude), axis (sighted latitude). `perturbationNoise` is a noise gate on those inputs. **Snap-to-orbit** eases toward `solar − horizon` and reports a lock within 0.01 rad.
- **Synth**: drone waveform, modulation depth, curvature→pitch, a 7-band EQ on the master bus (0.3 = flat), and optional tempo/swing quantize of ring tones.
- **Visual**: orbit arc, leash field, solar-band marker, sentinel pulse on each new log entry.
- Every state change, orbit lock and panel edit is written to the sentinel_dot chain; FAILURE is logged as a rejection.
- Defaults (dragStrength 0.6, modulationDepth 0.6, quantize off) leave the original pad behaviour unchanged.

### Snap to Orbit (perspective descent)
Zooms the view out to 0.3× over 0.7 s so the whole walk, leash and orbit are in frame, then runs a 3.2 s eased descent: zoom returns to 1× while both gate origins glide home along the same curve, drawn as contour rings and a gradient trail from where you were to home. Logged as `soo:snap` then `soo:home`.

### Drum kits
Kick fires once per ONSET (not every frame). Kits: Analog808, DeepHouse, TechnoHard, MinimalSoft. Axis (latitude) → pitch, horizon → decay, solar → drive; 4× pitch sweep in 45 ms, tanh drive, 4 ms high-passed noise click. Routed through the master EQ. Logged as `soo:kick`.
