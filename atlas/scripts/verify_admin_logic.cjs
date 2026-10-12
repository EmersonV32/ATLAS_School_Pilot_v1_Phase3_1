/* Dependency-free regressions against the production dashboard JavaScript.
 * Uses synthetic DOM/network/timers only. No browser, live config or devices.
 * Run: node scripts/verify_admin_logic.cjs
 */
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const source = fs.readFileSync(path.join(__dirname, "../src/atlas/dashboard/static/admin.js"), "utf8");
class Element {
  constructor() {
    this.textContent = ""; this.value = ""; this.children = []; this.dataset = {}; this.attrs = {}; this.checked = false;
    this.clientHeight = this.scrollHeight = this.scrollTop = 0;
    const classes = new Set();
    this.classList = {
      add: (...names) => names.forEach(name => classes.add(name)),
      remove: (...names) => names.forEach(name => classes.delete(name)),
      contains: name => classes.has(name),
      toggle: (name, force) => { const on = force == null ? !classes.has(name) : force; if (on) classes.add(name); else classes.delete(name); return on; },
    };
  }
  setAttribute(name, value) { this.attrs[name] = value; }
  removeAttribute(name) { delete this.attrs[name]; }
  addEventListener() {}
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  focus() {}
  querySelectorAll() { return []; }
  contains() { return false; }
}
const nodes = new Map();
const timers = new Map();
let timerId = 0;
const storage = new Map();
const sandbox = {
  document: {
    body: new Element(), hidden: false,
    getElementById: id => { if (!nodes.has(id)) nodes.set(id, new Element()); return nodes.get(id); },
    createElement: () => new Element(), createDocumentFragment: () => new Element(), activeElement: null,
    querySelectorAll: () => [], querySelector: () => new Element(),
  },
  window: {
    scrollTo: () => {},
    setTimeout: fn => { timers.set(++timerId, fn); return timerId; }, clearTimeout: id => timers.delete(id),
    setInterval: fn => { timers.set(++timerId, fn); return timerId; }, clearInterval: id => timers.delete(id),
    sessionStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) },
  },
  Date, Map, Set, Promise, JSON, Boolean, String, Number, Error, AbortController, URL, Blob,
  fetch: async () => { throw new Error("Synthetic network unavailable"); },
};
vm.createContext(sandbox);
const startup = 'initialize().catch((error) => notice(error.message, true));';
assert(source.endsWith(startup + "\n") || source.trimEnd().endsWith(startup));
vm.runInContext(source.replace(startup, "/* Startup disabled only by the synthetic test harness. */"), sandbox);
const evaluate = script => vm.runInContext(script, sandbox);
let checks = 0;
function check(script, expected) { assert.deepEqual(JSON.parse(JSON.stringify(evaluate(script))), expected, script); checks++; }

(async () => {
  check('componentState("Deepgram primary (ready); Whisper fallback (unavailable); last=not used yet")', "warning");
  check('componentState("Deepgram primary (unavailable); Whisper fallback (ready); last=Whisper")', "warning");
  check('componentState("Deepgram primary (unavailable); Whisper fallback (unavailable)")', "danger");
  check('componentState("Deepgram primary (ready); Whisper fallback (ready)")', "ok");
  for (const value of ["empty", "unavailable", "error: RuntimeError", "not ready", "disconnected", ""]) {
    sandbox.fixture = value; check('componentState(fixture)', "danger");
  }
  check('componentState("MockSTT")', "ok");
  check('componentState({status: "unavailable"})', "danger");
  check('valueIsHealthy("Deepgram primary (unavailable); Whisper fallback (ready)")', true);
  check('renderIssues(); $("issue-board").dataset.severity', "neutral");
  evaluate('latestStatus = {mode: "dev"}; latestHealth = {}; latestAudio = {}; latestVisitor = {}; lastStatusSync = Date.now(); renderIssues();');
  check('$("issue-title").textContent', "Simulated checks are healthy");
  evaluate('setIssue("camera", {title: "Camera unavailable", detail: "Check power", severity: "danger", view: "audio-vision"});');
  check('$("issue-board").dataset.severity', "danger");
  evaluate('notice("Audio test failed", true); setIssue("action", null);');
  check('issues.has("camera")', true);
  check('$("issue-title").textContent', "1 issue needs attention");
  evaluate('setIssue("camera", null);');
  check('$("issue-board").dataset.severity', "ok");
  evaluate('lastStatusSync = Date.now() - 12000; updateFreshness();');
  check('$("admin-state").textContent', "Status stale");
  check('issues.has("stale")', true);
  evaluate('setIssue("stale", null); setAdminView("settings");');
  check('$("dashboard-heading").textContent', "Settings");
  evaluate('setAdminView("not-a-view");');
  check('document.body.dataset.adminView', "main");
  evaluate('experienceDirty = true; $("sel-language").value = "fr"; syncExperienceForm({language: "en"});');
  check('$("sel-language").value', "fr");
  evaluate('adminUnlocked = true;');
  let release;
  sandbox.deferred = () => new Promise(resolve => { release = resolve; });
  const running = evaluate('pollOnce("slow", deferred)');
  check('pollsInFlight.has("slow")', true);
  let duplicate = false;
  sandbox.duplicate = () => { duplicate = true; };
  await evaluate('pollOnce("slow", duplicate)');
  assert.equal(duplicate, false); checks++;
  release(); await running;
  check('pollsInFlight.has("slow")', false);
  await evaluate('refreshStatus()');
  check('$("admin-state").textContent', "Offline");
  check('issues.has("status-request")', true);
  await evaluate('refreshAudio()');
  check('latestAudio', null);
  check('issues.has("audio-request")', true);
  await evaluate('refreshHealth()');
  check('latestHealth', null);
  check('issues.has("health-request")', true);
  evaluate('authRequired = false;');
  await evaluate('refreshVisitorStatus()');
  check('latestVisitor', null);
  check('issues.has("visitor-request")', true);
  evaluate('authRequired = false;');
  await evaluate('refreshCamera()');
  check('$("admin-camera").classList.contains("hidden")', true);
  check('$("camera-empty").classList.contains("hidden")', false);
  check('issues.has("camera-preview")', true);
  evaluate('setAdminLocked(true);');
  check('adminUnlocked', false);
  check('refreshIntervals.length', 0);
  evaluate('issues.clear(); notice("Token not accepted", true);');
  check('issues.has("action")', false);
  evaluate('adminUnlocked = true; authRequired = false; $("btn-start-demo").disabled = false;');
  let respond;
  sandbox.fetch = () => new Promise(resolve => { respond = resolve; });
  const mutation = evaluate('api("/api/admin/demo/start", {method: "POST"})');
  check('$("btn-start-demo").disabled', true);
  check('pendingMutations.size', 1);
  await assert.rejects(evaluate('api("/api/admin/demo/start", {method: "POST"})'), /already running/); checks++;
  respond({ ok: true, json: async () => ({ ok: true }) }); await mutation;
  check('$("btn-start-demo").disabled', false);
  check('pendingMutations.size', 0);
  evaluate('authRequired = true; $("inp-token").value = "old-synthetic-token";');
  const outdated = evaluate('requestApi("/status")');
  evaluate('$("inp-token").value = "new-synthetic-token";');
  respond({ ok: false, status: 401, json: async () => ({ detail: "Synthetic token rejected" }) });
  await assert.rejects(outdated, /Synthetic token rejected/); checks++;
  check('adminUnlocked', true);
  sandbox.fetch = (_, options) => new Promise((resolve, reject) => options.signal.addEventListener("abort", () => reject(new Error("Aborted"))));
  const stalled = evaluate('requestApi("/status")');
  timers.get(timerId)();
  await assert.rejects(stalled, /timed out/); checks++;
  const activity = {
    snapshot_id: "synthetic-v1", captured_at: "2026-10-12T12:00:00Z", runtime_available: true,
    text_visibility: {user_final: false, user_live: false, atlas: false}, events: [],
    runtime: [{id: "one", actor: "User", kind: "conversation", level: "info", timestamp: "", text: "Question received", raw: "[STT] Final result"}],
  };
  let logCalls = 0, releaseLog;
  evaluate('authRequired = false; adminUnlocked = true; document.body.dataset.adminView = "logs"; $("log-severity").value = "all";');
  sandbox.fetch = () => { logCalls++; return new Promise(resolve => { releaseLog = resolve; }); };
  const firstLog = evaluate('refreshLogs()');
  await evaluate('refreshLogs(true)');
  assert.equal(logCalls, 1); checks++;
  releaseLog({ok: true, json: async () => activity}); await firstLog;
  check('latestLogs.snapshot_id', "synthetic-v1");
  check('$("runtime-log-view").textContent', "User: Question received");
  evaluate('logFormats.runtime = "raw"; renderLogSnapshot();');
  check('$("runtime-log-view").textContent', "[STT] Final result");
  assert.equal(logCalls, 1, "Format switching must not fetch a different snapshot"); checks++;
  const pendingLog = evaluate('refreshLogs()');
  evaluate('$("chk-pause-logs").checked = true; logRefreshGeneration++;');
  releaseLog({ok: true, json: async () => ({...activity, snapshot_id: "must-not-appear"})}); await pendingLog;
  check('latestLogs.snapshot_id', "synthetic-v1");
  const pausedCalls = logCalls;
  await evaluate('refreshLogs()');
  assert.equal(logCalls, pausedCalls); checks++;
  evaluate('$("chk-pause-logs").checked = false;');
  sandbox.fetch = async () => { throw new Error("Synthetic connection lost"); };
  await evaluate('refreshLogs()');
  check('latestLogs.snapshot_id', "synthetic-v1");
  check('$("runtime-log-view").textContent', "[STT] Final result");
  check('$("log-freshness").textContent', "Offline · last shared snapshot");
  evaluate('lastLogSync = Date.now() - 12000; updateFreshness();');
  check('$("log-freshness").textContent', "Stale · last shared snapshot");
  sandbox.fetch = () => new Promise(resolve => { releaseLog = resolve; });
  const lateLog = evaluate('refreshLogs()');
  evaluate('setAdminLocked(true);');
  releaseLog({ok: true, json: async () => activity}); await lateLog;
  check('latestLogs.runtime.length', 0);
  check('$("runtime-log-view").textContent', "Unlock to view logs.");
  console.log(`${checks} dashboard JavaScript checks passed (synthetic, no live services).`);
})().catch(error => { console.error(error); process.exitCode = 1; });
