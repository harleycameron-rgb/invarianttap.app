/* sentinel_dot.js — browser writer for the sentinel_dot log format (v0.2).
 *
 * Produces JSONL byte-compatible with the Python reference
 * (github.com/harleycameron-rgb/sentinel_dot), so exported logs verify with:
 *     sentinel_dot verify invarianttap.jsonl [--key-env SENTINEL_DOT_KEY] --expect-seq N --expect-hash H
 *
 * entry_hash = HMAC-SHA256(key, canonical_json(entry \ {entry_hash}))  if a key is set
 *            = SHA-256(canonical_json(entry \ {entry_hash}))           otherwise
 * canonical_json == json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=True)
 *
 * In-memory only: nothing is persisted or sent. The user exports the log explicitly.
 * Works in browsers (WebCrypto) and Node >= 18 (globalThis.crypto).
 */
(function (root) {
  "use strict";
  const GENESIS_HASH = "0".repeat(64);
  const MSG_TYPES = new Set(["action", "rejection", "round_boundary", "malformed_rejection"]);
  const subtle = () => {
    const s = root.crypto && root.crypto.subtle;
    if (!s) throw new Error("sentinel_dot: WebCrypto unavailable (needs https or localhost)");
    return s;
  };

  /* Strict schema: str, safe int, bool, null, array, object. Floats are refused
     (encode as scaled int or string) so hashes match across runtimes. */
  function checkValue(v, path) {
    if (v === null || typeof v === "string" || typeof v === "boolean") return;
    if (typeof v === "number") {
      if (!Number.isSafeInteger(v)) throw new Error(`${path}: floats/unsafe ints not allowed`);
      return;
    }
    if (Array.isArray(v)) { v.forEach((x, i) => checkValue(x, `${path}[${i}]`)); return; }
    if (typeof v === "object") { for (const k of Object.keys(v)) checkValue(v[k], `${path}.${k}`); return; }
    throw new Error(`${path}: unsupported type ${typeof v}`);
  }

  const cmpCodePoint = (a, b) => {           // Python sorts str by code point
    const A = Array.from(a), B = Array.from(b);
    for (let i = 0; i < Math.min(A.length, B.length); i++) {
      const d = A[i].codePointAt(0) - B[i].codePointAt(0);
      if (d) return d;
    }
    return A.length - B.length;
  };

  function canonicalJson(v) {
    if (v === null || typeof v !== "object") {
      // Python ensure_ascii escapes everything outside 0x20-0x7e (incl. DEL), lowercase hex
      return JSON.stringify(v).replace(/[\u007f-\uffff]/g, c =>
        "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"));
    }
    if (Array.isArray(v)) return "[" + v.map(canonicalJson).join(",") + "]";
    return "{" + Object.keys(v).sort(cmpCodePoint)
      .map(k => canonicalJson(k) + ":" + canonicalJson(v[k])).join(",") + "}";
  }

  const hex = buf => Array.from(new Uint8Array(buf), b => b.toString(16).padStart(2, "0")).join("");
  const utf8 = s => new TextEncoder().encode(s);

  function b64decode(s) {
    const bin = (root.atob ? root.atob(s.trim()) : Buffer.from(s.trim(), "base64").toString("binary"));
    return Uint8Array.from(bin, c => c.charCodeAt(0));
  }

  /* Coerce app values into the strict schema (mirrors agent._jsonable,
     except floats become fixed-point strings rather than Python repr). */
  function jsonable(v, digits = 6) {
    if (v === null || v === undefined) return null;
    if (typeof v === "boolean" || typeof v === "string") return v;
    if (typeof v === "number") return Number.isSafeInteger(v) ? v : (Number.isFinite(v) ? v.toFixed(digits) : String(v));
    if (Array.isArray(v)) return v.map(x => jsonable(x, digits));
    if (typeof v === "object") { const o = {}; for (const k of Object.keys(v)) o[k] = jsonable(v[k], digits); return o; }
    return String(v);
  }

  class SentinelLog {
    constructor({ sender = "invarianttap", round = 0 } = {}) {
      this.sender = sender; this.round = round;
      this.entries = []; this.lines = [];
      this._hmacKey = null; this._queue = Promise.resolve();
      this.mode = "sha256";
    }
    /* base64 key, >= 32 bytes (same as SENTINEL_DOT_KEY). Must be set before the first entry. */
    async setKey(b64) {
      if (this.entries.length) throw new Error("sentinel_dot: set the key before the first entry");
      const raw = b64decode(b64);
      if (raw.length < 32) throw new Error("sentinel_dot: key must decode to >= 32 bytes");
      this._hmacKey = await subtle().importKey("raw", raw, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
      this.mode = "hmac-sha256";
    }
    head() {
      const n = this.entries.length;
      return n ? [n, this.entries[n - 1].entry_hash] : [0, GENESIS_HASH];
    }
    async _hash(body) {
      const data = utf8(body);
      return hex(this._hmacKey ? await subtle().sign("HMAC", this._hmacKey, data)
                               : await subtle().digest("SHA-256", data));
    }
    /* Appends are serialised through a promise queue so the chain order equals call order. */
    append(msg_type, action_type, parameters = {}, permission_token = null) {
      const p = this._queue.then(async () => {
        if (!MSG_TYPES.has(msg_type)) throw new Error(`unknown msg_type: ${msg_type}`);
        if (!action_type) throw new Error("action_type must be non-empty");
        checkValue(parameters, "parameters");
        const [seq, prev] = this.head();
        const e = { seq, msg_type, sender: this.sender, round: this.round, action_type,
                    parameters, permission_token, prev_log_hash: prev };
        e.entry_hash = await this._hash(canonicalJson(e));
        this.entries.push(e); this.lines.push(canonicalJson(e));
        if (this.onAppend) try { this.onAppend(e); } catch (_) {}
        return e;
      });
      this._queue = p.catch(() => {});
      return p;
    }
    action(type, params, token = null) { return this.append("action", type, jsonable(params), token); }
    reject(type, reason, params = {}) { return this.append("rejection", type, Object.assign(jsonable(params), { reason })); }
    async nextRound(note = "") {
      const e = await this.append("round_boundary", "round_end", { note });
      this.round += 1; return e;
    }
    toJsonl() { return this.lines.map(l => l + "\n").join(""); }
    /* Self-check of chain + hashes (same D1 rules as verify_log, minus file-level checks). */
    async verify() {
      let prev = GENESIS_HASH;
      for (let i = 0; i < this.entries.length; i++) {
        const e = this.entries[i];
        const { entry_hash, ...body } = e;
        if (e.seq !== i || e.prev_log_hash !== prev) return { ok: false, seq: i, reason: "chain_break" };
        if (await this._hash(canonicalJson(body)) !== entry_hash) return { ok: false, seq: i, reason: "hash_mismatch" };
        prev = entry_hash;
      }
      return { ok: true, head: this.head() };
    }
  }

  const api = { SentinelLog, canonicalJson, jsonable, GENESIS_HASH };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.SentinelDot = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
