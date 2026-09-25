// Writes a JS-produced log for the Python cross-check. Usage: node tests/make_log.mjs out.jsonl [b64key]
import { createRequire } from "module"; import fs from "fs";
const { SentinelLog } = createRequire(import.meta.url)("../sentinel_dot.js");
const [out, key] = process.argv.slice(2);
const log = new SentinelLog({ sender: "invarianttap" });
if (key) await log.setKey(key);
await log.action("session_start", { app: "invarianttap", lock_version: "4.1.0" });
await log.action("lock_set", { section: "baseline", key: "OMEGA_LOCAL", value: String(1.42) });
await log.action("ring", { gate: "forward", id: 1, parent: null, moire_urad: -1234567, coherence_ppm: 812345 });
await log.reject("sight_pole", "not facing N or S", { az_mdeg: 91234 });
await log.action("unicode", { s: "Moiré ☀ ✧ 𝔸 \u007f \n\t\"\\", "é": 1, "z": [true, false, null], "A": {} });
await log.nextRound("reset");
await log.action("export", { entries: 6 });
await log.action("coerced", { f: 0.5 });              // action() coerces floats -> "0.500000"
if (log.entries.at(-1).parameters.f !== "0.500000") throw new Error("float not coerced");
let threw = false;
try { await log.append("action", "bad", { f: 0.5 }); } catch { threw = true; }
if (!threw) throw new Error("raw float not rejected");
const v = await log.verify(); if (!v.ok) throw new Error("self-verify failed");
fs.writeFileSync(out, log.toJsonl());
console.log(JSON.stringify(log.head()));
