/* ATLAS operations dashboard. No build step or external dependencies. */
"use strict";

const $ = (id) => document.getElementById(id);
let authRequired = true;
let adminUnlocked = false;
let adminAccessGeneration = 0;
class AdminAccessChangedError extends Error {
  constructor() { super("Admin access changed; outdated response discarded."); }
}
let cameraTimer = null;
let currentHelpRequestId = null;
let lastAlertedHelpRequestId = null;
let helpAlertsEnabled = false;
let refreshIntervals = [];
let experienceDirty = false;
let visitorMonitorCollapsed = false;
let cameraRequestInFlight = false;
let cameraObjectUrl = null;
let arducamTimer = null;
let arducamRequestInFlight = false;
let arducamObjectUrl = null;
let latestPan = null;
let panSequence = 0;
let panJogDirection = 0;
let panJogTimer = null;
let panJogRequestInFlight = false;
let panStatusInFlight = false;
let panGeneration = 0;
// Per-page ID, supported on local HTTP; never persisted.
const panClientId = "10000000-1000-4000-8000-100000000000".replace(/[018]/g, (c) =>
  (Number(c) ^ (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (Number(c) / 4)))).toString(16));
let audioVolumeTimer = null;
const logFormats = { runtime: "human", events: "human" };
let latestStatus = null;
let latestHealth = null;
let latestAudio = null;
let latestConfig = null;
let latestLogs = { runtime: [], events: [], snapshot_id: "", captured_at: "" };
let logsRequestInFlight = false;
let logRefreshGeneration = 0;
let lastLogSync = 0;
let latestVisitor = null;
let lastStatusSync = 0;
const issues = new Map();
const pollsInFlight = new Set();
const pendingMutations = new Set();
const actionControls = {
  "/admin/config": ["btn-save-config", "btn-save-config-top"],
  "/api/admin/demo/start": ["btn-start-demo"],
  "/api/admin/session/stop": ["btn-stop", "btn-visitor-stop"],
  "/session/profile": ["btn-apply-experience"],
  "/api/admin/audio/test": ["btn-test-audio"],
  "/session/manual-artwork": ["btn-override", "btn-clear-override"],
  "/session/capture": ["btn-capture"],
  "/content/ingest": ["btn-ingest"],
  "/eval/rag": ["btn-eval"],
  "/hardware/emergency-stop": ["btn-estop"],
  "/hardware/clear-emergency-stop": ["btn-clear-estop"],
};
const viewCopy = {
  main: ["Live overview", "Your cameras, visitor experience and system health in one place."],
  demo: ["Demo controls", "Set up the experience, check readiness and run a live demonstration."],
  "audio-vision": ["Audio & vision", "Follow the signal from the camera and microphone to the spoken answer."],
  arducam: ["Arducam", "An independent CSI preview. Frames are live only and never stored."],
  visitor: ["Visitor monitor", "Follow onboarding, readiness and assistance without exposing identifying details."],
  logs: ["Activity & logs", "Follow the conversation, camera and controls in plain language. Technical details stay in sync."],
  settings: ["Settings", "Review the active configuration. Saved changes require a runtime restart."],
};

function setIssue(key, issue) {
  if (issue) issues.set(key, issue);
  else issues.delete(key);
  renderIssues();
}

function replaceIssues(prefix, entries) {
  for (const key of issues.keys()) if (key.startsWith(prefix)) issues.delete(key);
  for (const [key, issue] of entries) issues.set(`${prefix}${key}`, issue);
  renderIssues();
}

function renderIssues() {
  const active = [...issues.values()].sort((a, b) => (a.severity === "danger" ? 0 : 1) - (b.severity === "danger" ? 0 : 1));
  const confirmed = latestStatus && latestHealth && latestAudio && latestVisitor && lastStatusSync;
  const simulated = latestStatus && latestStatus.mode !== "device";
  const severity = active.some((item) => item.severity === "danger") ? "danger" : active.length ? "warning" : confirmed ? "ok" : "neutral";
  $("issue-board").dataset.severity = severity;
  $("issue-mark").textContent = active.length ? "!" : confirmed ? "✓" : "…";
  const heading = active.length ? `${active.length} ${active.length === 1 ? "issue needs" : "issues need"} attention`
    : confirmed ? (simulated ? "Simulated checks are healthy" : "Reported checks are healthy") : "Checking system health";
  // Avoid repeatedly announcing the same summary on every polling response.
  if ($("issue-title").textContent !== heading) $("issue-title").textContent = heading;
  $("issue-summary").textContent = active.length ? "Live faults stay here until they recover. Open the relevant view to investigate."
    : confirmed ? (simulated ? "Mock/dev runtime — this is not a physical device or cloud-service validation." : "The latest runtime reports no active faults. This is not a full hardware or cloud-service test.")
      : "Readiness is not confirmed until live checks complete.";
  const list = $("issue-list");
  // Preserve keyboard focus: do not rebuild identical live rows every second.
  const signature = JSON.stringify(active);
  if (list.dataset.signature !== signature) {
    list.dataset.signature = signature;
    list.replaceChildren();
    active.forEach((issue) => {
      const row = document.createElement("li");
      const copy = document.createElement("div");
      const title = document.createElement("strong");
      const detail = document.createElement("p");
      title.textContent = issue.title;
      detail.textContent = issue.detail;
      copy.append(title, detail);
      row.append(copy);
      if (issue.view) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "secondary compact-button";
        button.textContent = "Inspect";
        button.setAttribute("aria-label", `Inspect ${issue.title}`);
        button.addEventListener("click", () => {
          setAdminView(issue.view);
          $("dashboard-heading").focus();
        });
        row.append(button);
      }
      list.append(row);
    });
  }
  $("btn-clear-action-error").classList.toggle("hidden", !issues.has("action"));
  $("btn-show-issues").classList.toggle("hidden", !active.length);
  $("btn-show-issues").textContent = `${active.length} ${active.length === 1 ? "issue" : "issues"}`;
}

function updateFreshness() {
  if (lastLogSync && adminUnlocked && document.body.dataset.adminView === "logs" && !$("chk-pause-logs").checked && Date.now() - lastLogSync >= 10000) {
    $("log-freshness").textContent = "Stale · last shared snapshot";
  }
  if (!lastStatusSync) return;
  const age = Math.max(0, Math.floor((Date.now() - lastStatusSync) / 1000));
  $("last-sync").textContent = age < 5 ? "Updated just now" : `Last update ${age}s ago`;
  if (age >= 10) {
    setIssue("stale", { title: "Live status is stale", detail: "Displayed values are last known, not confirmed live. Check the Jetson connection.", severity: "danger", view: "logs" });
    $("admin-state").textContent = "Status stale";
    $("admin-state").className = "status-pill danger";
  }
}

async function pollOnce(key, refresh) {
  if (!adminUnlocked || pollsInFlight.has(key)) return;
  pollsInFlight.add(key);
  try { await refresh(); } finally { pollsInFlight.delete(key); }
}

function token() {
  return $("inp-token").value.trim();
}

function setAdminLocked(locked, message = "") {
  if (locked) {
    adminAccessGeneration++;
    stopPanJog();
    panGeneration++;
    latestPan = null;
    disablePanControls();
    $("pan-state").textContent = "Locked";
    $("pan-angle").textContent = "--";
    adminUnlocked = false;
    logRefreshGeneration++;
    lastLogSync = 0;
    latestLogs = { runtime: [], events: [], snapshot_id: "", captured_at: "" };
    $("activity-timeline").replaceChildren();
    $("activity-timeline").dataset.signature = "";
    $("activity-count").textContent = "Unlock to view live activity.";
    $("runtime-log-view").textContent = "Unlock to view logs.";
    $("event-log-view").textContent = "Unlock to view logs.";
    refreshIntervals.forEach(window.clearInterval);
    refreshIntervals = [];
    window.clearTimeout(cameraTimer);
    window.clearTimeout(arducamTimer);
    window.clearTimeout(audioVolumeTimer);
    for (const url of [cameraObjectUrl, arducamObjectUrl]) if (url) URL.revokeObjectURL(url);
    cameraObjectUrl = arducamObjectUrl = null;
    ["admin-camera", "admin-arducam"].forEach((id) => { $(id).removeAttribute("src"); $(id).classList.add("hidden"); });
    ["camera-empty", "arducam-empty"].forEach((id) => $(id).classList.remove("hidden"));
  }
  document.body.classList.toggle("admin-locked", locked);
  document.body.classList.toggle("admin-unlocked", !locked);
  $("admin-unlock-gate").setAttribute("aria-hidden", String(!locked));
  $("admin-unlock-message").textContent = message;
  if (locked) window.setTimeout(() => $("inp-token").focus(), 0);
}

async function api(path, options = {}, protectedRoute = true) {
  if (!options.method || options.method === "GET" || path === "/api/admin/audio") return requestApi(path, options, protectedRoute);
  const key = `${options.method} ${path}`;
  if (pendingMutations.has(key)) throw new Error("This action is already running. Wait for it to finish.");
  pendingMutations.add(key);
  const controls = (actionControls[path] || []).map((id) => [$(id), $(id).disabled]);
  controls.forEach(([button]) => { button.disabled = true; button.setAttribute("aria-busy", "true"); });
  try { return await requestApi(path, options, protectedRoute); }
  finally {
    pendingMutations.delete(key);
    controls.forEach(([button, disabled]) => { button.disabled = disabled; button.removeAttribute("aria-busy"); });
  }
}

async function requestApi(path, options = {}, protectedRoute = true) {
  const accessGeneration = adminAccessGeneration;
  const requestToken = token();
  if (protectedRoute && authRequired && !token()) throw new Error("Admin token required");
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (protectedRoute && authRequired) headers["X-Atlas-Admin-Token"] = token();
  const controller = new AbortController();
  const { timeoutMs, signal: callerSignal, ...fetchOptions } = options;
  const cancel = () => controller.abort();
  if (callerSignal?.aborted) controller.abort();
  else callerSignal?.addEventListener("abort", cancel, { once: true });
  const deadline = window.setTimeout(cancel, timeoutMs || (options.method && options.method !== "GET" ? 60000 : 10000));
  let response;
  let body = null;
  try {
    response = await fetch(path, { ...fetchOptions, headers, signal: controller.signal });
    try { body = await response.json(); } catch (_) { /* no response body */ }
  } catch (_) {
    if (protectedRoute && (accessGeneration !== adminAccessGeneration || requestToken !== token())) throw new AdminAccessChangedError();
    throw new Error(controller.signal.aborted ? "Request timed out. Check the connection and retry." : "Cannot reach ATLAS. Check the connection and retry.");
  } finally {
    window.clearTimeout(deadline);
    callerSignal?.removeEventListener("abort", cancel);
  }
  if (protectedRoute && (accessGeneration !== adminAccessGeneration || requestToken !== token())) {
    throw new AdminAccessChangedError();
  }
  if (!response.ok) {
    const detail = body && body.detail ? body.detail : response.statusText;
    if (protectedRoute && response.status === 401 && authRequired && accessGeneration === adminAccessGeneration && headers["X-Atlas-Admin-Token"] === token()) {
      window.sessionStorage.removeItem("atlasAdminToken");
      setAdminLocked(true, "This token was not accepted. Try again.");
    }
    throw new Error(typeof detail === "string" ? detail : "The request was rejected. Check the entered values and retry.");
  }
  return body;
}

function notice(message, bad = false) {
  if (bad && adminUnlocked) setIssue("action", { title: "Action did not complete", detail: message, severity: "danger" });
  const node = $("admin-notice");
  node.textContent = message;
  node.classList.toggle("bad", bad);
  node.classList.remove("hidden");
  window.clearTimeout(notice.timer);
  notice.timer = window.setTimeout(() => node.classList.add("hidden"), 4500);
}

function renderObject(target, data) {
  $(target).textContent = JSON.stringify(data, null, 2);
}

function appendStatus(list, name, value, bad = false) {
  const item = document.createElement("li");
  const label = document.createElement("span");
  const state = document.createElement("strong");
  label.textContent = name;
  state.textContent = String(value);
  state.className = bad ? "bad" : "ok";
  item.append(label, state);
  list.append(item);
}

function titleCase(value) {
  return String(value || "--")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatAgeGuidance(value) {
  return { under_7: "6 or younger", under_13: "7–12", "13_17": "13–17", "18_plus": "18+" }[value]
    || "Not provided";
}

function playHelpTone() {
  if (!helpAlertsEnabled) return;
  const AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!AudioContext) return;
  const context = new AudioContext();
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  oscillator.type = "sine";
  oscillator.frequency.setValueAtTime(523.25, context.currentTime);
  oscillator.frequency.setValueAtTime(659.25, context.currentTime + 0.14);
  gain.gain.setValueAtTime(0.0001, context.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.08, context.currentTime + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.34);
  oscillator.connect(gain).connect(context.destination);
  oscillator.start();
  oscillator.stop(context.currentTime + 0.36);
  oscillator.addEventListener("ended", () => context.close());
}

function renderVisitorStatus(payload) {
  latestVisitor = payload;
  const state = payload.state;
  const readiness = payload.readiness;
  const help = payload.help_request;
  const connected = state.connection === "online";
  const helpRequested = Boolean(help && help.status === "requested");
  const visitorIssues = [];
  if (!connected) visitorIssues.push(["connection", { title: "Visitor connection lost", detail: "The visitor monitor cannot confirm an active connection.", severity: "danger", view: "visitor" }]);
  if (state.transfer === "failed") visitorIssues.push(["transfer", { title: "Visitor profile transfer failed", detail: "Review the visitor readiness checks before starting again.", severity: "danger", view: "visitor" }]);
  if (helpRequested) visitorIssues.push(["help", { title: "Visitor needs assistance", detail: "Open the visitor monitor and acknowledge the request.", severity: "warning", view: "visitor" }]);
  readiness.items.filter((item) => item.status !== "ready").forEach((item) => {
    visitorIssues.push([`ready-${item.id}`, { title: `${item.label}: ${titleCase(item.status)}`, detail: item.detail || "Review this readiness check in the visitor monitor.", severity: ["unavailable", "unsupported"].includes(item.status) ? "danger" : "warning", view: "visitor" }]);
  });
  replaceIssues("visitor-", visitorIssues);
  setIssue("visitor-request", null);
  $("visitor-live-panel").classList.toggle("has-help-request", helpRequested);
  $("visitor-assistance").classList.toggle("has-help-request", helpRequested);
  document.body.classList.toggle("visitor-help-active", helpRequested);
  document.title = helpRequested ? "HELP REQUEST · ATLAS Admin" : "ATLAS Admin";
  $("visitor-live-state").textContent = connected ? titleCase(state.phase) : "Disconnected";
  $("visitor-live-state").className = `status-pill ${connected ? (state.phase === "in_use" ? "ok" : "neutral") : "danger"}`;
  $("visitor-unit").textContent = state.unit_id;
  $("visitor-phase").textContent = titleCase(state.phase);
  $("visitor-step").textContent = titleCase(state.step);
  $("visitor-language").textContent = state.language ? state.language.toUpperCase() : "Not chosen";
  $("visitor-age-guidance").textContent = formatAgeGuidance(state.profile.age_guidance);
  $("visitor-interests").textContent = state.profile.interests.length
    ? state.profile.interests.map(titleCase).join(", ") : "None";
  $("visitor-updated").textContent = new Date(state.updated_at)
    .toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  $("visitor-readiness-state").textContent = readiness.ready ? "Ready" : "Needs attention";
  $("visitor-readiness-state").className = `status-pill ${readiness.ready ? "ok" : "warning"}`;
  $("visitor-expertise").textContent = state.profile.expertise ? titleCase(state.profile.expertise) : "Not provided";
  $("visitor-accessibility").textContent = state.profile.accessibility.length
    ? state.profile.accessibility.map(titleCase).join(", ") : "None";
  $("visitor-demo-mode").textContent = state.demo_mode ? "On" : "Off";
  $("visitor-connection").textContent = titleCase(state.connection);
  $("visitor-ready-count").textContent = `${readiness.items.filter((item) => item.status === "ready").length} / ${readiness.items.length}`;
  $("visitor-blocker-count").textContent = String(readiness.blockers.length);
  $("visitor-transfer-state").textContent = titleCase(state.transfer);
  $("visitor-transfer-state").className = `status-pill ${state.transfer === "complete" ? "ok" : (state.transfer === "failed" ? "danger" : "neutral")}`;
  $("btn-start-demo").textContent = state.demo_mode && state.phase === "in_use"
    ? "Restart demo" : "Start demo";

  const readinessList = $("visitor-readiness-list");
  readinessList.replaceChildren();
  readiness.items.forEach((item) => {
    const row = document.createElement("li");
    row.className = `readiness-${item.status}`;
    const label = document.createElement("span");
    const status = document.createElement("strong");
    label.textContent = item.label;
    status.textContent = titleCase(item.status);
    row.append(label, status);
    readinessList.append(row);
  });

  currentHelpRequestId = help && help.status === "requested" ? help.request_id : null;
  $("btn-ack-help").disabled = !currentHelpRequestId;
  if (help) {
    $("visitor-help-badge").textContent = helpRequested ? "Help requested" : titleCase(help.status);
    $("visitor-help-badge").className = `status-pill ${help.status === "requested" ? "warning" : "ok"}`;
    $("visitor-help-detail").textContent = `${titleCase(help.context)} request · ${new Date(help.requested_at).toLocaleTimeString()}`;
    if (help.status === "requested" && help.request_id !== lastAlertedHelpRequestId) {
      playHelpTone();
      if (helpAlertsEnabled) lastAlertedHelpRequestId = help.request_id;
    }
  } else {
    $("visitor-help-badge").textContent = "No request";
    $("visitor-help-badge").className = "status-pill neutral";
    $("visitor-help-detail").textContent = "No visitor assistance request is active.";
  }
}

async function refreshVisitorStatus() {
  if (authRequired && !token()) {
    $("visitor-live-state").textContent = "Unlock required";
    $("visitor-live-state").className = "status-pill warning";
    return;
  }
  try {
    renderVisitorStatus(await api("/api/admin/live-status", {}, true));
  } catch (_) {
    if (_ instanceof AdminAccessChangedError) return;
    latestVisitor = null;
    setIssue("visitor-request", { title: "Visitor monitor unavailable", detail: "Onboarding and assistance values may be out of date. Check the connection.", severity: "danger", view: "visitor" });
    $("visitor-live-state").textContent = "Unavailable";
    $("visitor-live-state").className = "status-pill danger";
  }
}

function componentState(value) {
  const normalized = String(value && typeof value === "object" ? value.status || value.active || value.provider || "" : value || "").toLowerCase();
  if (/primary \((ready|unavailable)\).*fallback \((ready|unavailable)\)/.test(normalized)) {
    const primary = normalized.includes("primary (ready)");
    const fallback = normalized.includes("fallback (ready)");
    return primary && fallback ? "ok" : primary || fallback ? "warning" : "danger";
  }
  if (!normalized || /error|unavailable|failed|disconnected|not ready|^empty$|^unknown$/.test(normalized)) return "danger";
  return /degraded|fallback active/.test(normalized) ? "warning" : "ok";
}

function valueIsHealthy(value) {
  return componentState(value) !== "danger";
}

function cameraIsFresh(camera) {
  const age = camera && camera.last_frame_age_s;
  return Boolean(camera && camera.ready) && typeof age === "number"
    && Number.isFinite(age) && age >= 0 && age <= 3;
}

function renderDemoReadiness() {
  if (!latestStatus) return;
  const status = latestStatus;
  const components = latestHealth && latestHealth.components || {};
  const camera = status.camera || {};
  const audioReady = latestAudio && routeIsAvailable(latestAudio);
  const checks = [
    ["Runtime", !status.emergency_stopped, status.emergency_stopped ? "Stopped" : "Safety clear"],
    ["Speech input", valueIsHealthy(components.stt), providerLabel(components.stt)],
    ["Speech output", valueIsHealthy(components.tts), providerLabel(components.tts)],
    ["Artwork camera (optional)", cameraIsFresh(camera), cameraIsFresh(camera) ? "Frame ready" : "Offline · voice demo available"],
    ["Knowledge", valueIsHealthy(components.retriever), providerLabel(components.retriever)],
    ["Audio route", Boolean(audioReady), latestAudio
      ? `${titleCase(latestAudio.route)}${audioReady ? "" : " unavailable"}` : "Checking"],
  ];
  const board = $("demo-readiness-grid");
  board.replaceChildren();
  checks.forEach(([name, good, detail]) => {
    const item = document.createElement("div");
    item.className = good ? "check-good" : "check-bad";
    const label = document.createElement("span");
    const value = document.createElement("strong");
    label.textContent = name;
    value.textContent = detail || "Not ready";
    item.append(label, value);
    board.append(item);
  });
}

function renderOperationalDetails() {
  if (!latestStatus) return;
  const status = latestStatus;
  const components = latestHealth && latestHealth.components || {};
  const camera = status.camera || {};
  const artwork = status.artwork || {};
  const answer = status.last_answer || {};
  const interaction = status.last_interaction;
  const sessionActive = Boolean(status.session_active);
  const demoActive = Boolean(status.demo_active);

  $("demo-cycle-state").textContent = demoActive ? "Running" : "Waiting";
  $("demo-cycle-state").className = `status-pill ${demoActive ? "ok" : "neutral"}`;
  $("demo-stage-listen").textContent = sessionActive ? "Session active" : "Idle";
  $("demo-stage-language").textContent = status.experience && status.experience.language
    ? status.experience.language.toUpperCase() : "No language";
  $("demo-stage-artwork").textContent = artwork.label || "No artwork";
  $("demo-stage-response").textContent = interaction ? (interaction.state === "failed" ? "Needs attention" : interaction.state === "completed" ? "Response completed" : "Control applied") : answer.answer ? "Dashboard answer ready" : "No response recorded";

  $("diag-camera").textContent = cameraIsFresh(camera) ? "Connected" : "Offline · optional for speech";
  $("diag-yolo").textContent = latestConfig
    ? titleCase(latestConfig.hardware.yolo_backend)
    : providerLabel(components.vision);
  $("diag-stt").textContent = providerLabel(components.stt);
  $("diag-tts").textContent = providerLabel(components.tts);
  const speechReady = valueIsHealthy(components.stt) && valueIsHealthy(components.tts);
  const criticalGood = cameraIsFresh(camera) && speechReady;
  $("signal-state").textContent = criticalGood ? "Ready" : speechReady ? "Voice ready · camera offline" : "Needs attention";
  $("signal-state").className = `status-pill ${criticalGood ? "ok" : "warning"}`;
  renderDemoReadiness();
}

function setAdminView(view, { persist = true } = {}) {
  const supported = new Set(["main", "demo", "audio-vision", "arducam", "visitor", "logs", "settings"]);
  const nextView = supported.has(view) ? view : "main";
  if (nextView !== "arducam") stopPanJog();
  document.body.dataset.adminView = nextView;
  $("dashboard-heading").textContent = viewCopy[nextView][0];
  $("dashboard-description").textContent = viewCopy[nextView][1];
  document.querySelectorAll("[data-admin-tab]").forEach((button) => {
    const active = button.dataset.adminTab === nextView;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  document.querySelectorAll("[data-admin-views]").forEach((panel) => {
    panel.classList.toggle("view-hidden", !panel.dataset.adminViews.split(" ").includes(nextView));
  });
  if (persist) {
    window.sessionStorage.setItem("atlasAdminView", nextView);
    window.scrollTo(0, 0);
  }
  if (adminUnlocked) refreshCamera();
  if (nextView === "logs" && adminUnlocked) refreshLogs();
  if (nextView === "arducam" && adminUnlocked) {
    refreshArducamStatus();
    refreshArducam();
    refreshPanStatus();
  }
}

function providerLabel(provider) {
  if (typeof provider === "string") return provider;
  if (!provider || typeof provider !== "object") return "Unknown";
  return provider.active || provider.provider || provider.primary || "Fallback ready";
}

function routeIsAvailable(status) {
  if (status.route === "both") return status.both_available;
  return status.route === "speaker" ? status.speaker_available : status.headset_available;
}

function renderAudioStatus(status) {
  latestAudio = status;
  const routeAvailable = routeIsAvailable(status);
  setIssue("audio-request", null);
  setIssue("audio-route", routeAvailable ? null : { title: "Selected audio output unavailable", detail: "Connect the selected headset or speaker, or choose an available output.", severity: "danger", view: "audio-vision" });
  document.querySelectorAll("[data-audio-route]").forEach((button) => {
    const active = button.dataset.audioRoute === status.route;
    button.setAttribute("aria-pressed", String(active));
  });
  $("audio-volume").value = status.volume_percent;
  $("audio-volume-value").textContent = `${status.volume_percent}%`;
  $("audio-output-name").textContent = status.output_device_name;
  $("audio-input-name").textContent = status.headset_name || "Not reported";
  $("audio-provider").textContent = providerLabel(status.provider);
  $("audio-state").textContent = routeAvailable ? `${titleCase(status.route)} active` : `${titleCase(status.route)} unavailable`;
  $("audio-state").className = `status-pill ${routeAvailable ? "ok" : "warning"}`;
  $("metric-audio").textContent = routeAvailable ? titleCase(status.route) : "Unavailable";
  $("diag-audio-output").textContent = status.output_device_name || "Unavailable";
  $("diag-audio-input").textContent = status.headset_name || "Shokz headset";
  const headset = document.querySelector('[data-audio-route="headset"]');
  const speaker = document.querySelector('[data-audio-route="speaker"]');
  const both = document.querySelector('[data-audio-route="both"]');
  headset.title = status.headset_available ? "Shokz output is available" : "Shokz output is not currently detected";
  speaker.title = status.speaker_available ? "Judge speaker is available" : "Judge speaker is not currently detected";
  both.title = status.both_available ? "Both outputs are available" : "Both outputs require Shokz and the judge speaker";
  renderOperationalDetails();
}

async function refreshAudio() {
  try {
    renderAudioStatus(await api("/api/admin/audio", {}, true));
  } catch (error) {
    if (error instanceof AdminAccessChangedError) return;
    latestAudio = null;
    $("metric-audio").textContent = "Unknown";
    setIssue("audio-request", { title: "Audio status unavailable", detail: "Cannot confirm the selected output. Check the connection and audio devices.", severity: "danger", view: "audio-vision" });
    $("audio-state").textContent = "Unavailable";
    $("audio-state").className = "status-pill danger";
    // The persistent issue board is the operator-facing error surface.
  }
}

async function applyAudioChange(patch) {
  const status = await api("/api/admin/audio", {
    method: "PUT",
    body: JSON.stringify(patch),
  }, true);
  renderAudioStatus(status);
  return status;
}

async function refreshStatus() {
  try {
    const status = await api("/status");
    latestStatus = status;
    lastStatusSync = Date.now();
    setIssue("status-request", null);
    setIssue("stale", null);
    updateFreshness();
    const simulated = status.mode !== "device";
    $("runtime-mode").textContent = simulated ? "Simulated runtime" : "Device runtime";
    if (status.camera_pan) updatePanIssue(status.camera_pan);
    $("runtime-mode").className = `status-pill ${simulated ? "warning" : "neutral"}`;
    replaceIssues("runtime-", [
      ...(status.emergency_stopped ? [["stop", { title: "Emergency stop is active", detail: "Motion is stopped. Only clear the stop once the equipment is safe.", severity: "danger", view: "audio-vision" }]] : []),
      ...(!cameraIsFresh(status.camera) ? [["camera", { title: "Camera offline · voice demo available", detail: "Live recognition is unavailable. Ask about an artwork by name or choose it in Artwork context; speech and knowledge still work.", severity: "warning", view: "audio-vision" }]] : []),
      ...(status.last_interaction && status.last_interaction.response_failed ? [["response", { title: "Last response failed", detail: "ATLAS reported an AI or interaction failure. Review Activity & logs before retrying.", severity: "danger", view: "logs" }]] : []),
      ...(status.last_interaction && status.last_interaction.speech_ok === false ? [["speech", { title: "Last spoken response was not played", detail: "Check the headset, selected output and speech provider before retrying.", severity: "danger", view: "audio-vision" }]] : []),
    ]);
    $("admin-state").textContent = status.emergency_stopped ? "Emergency stop" : "Online";
    $("admin-state").className = `status-pill ${status.emergency_stopped ? "danger" : "ok"}`;
    $("metric-mode").textContent = status.mode;
    $("metric-session").textContent = status.session_active ? "Active" : "Idle";
    $("metric-artwork").textContent = status.artwork.label || "None";
    const latency = status.last_interaction ? status.last_interaction.latency_ms : status.last_answer && status.last_answer.latency_ms;
    $("metric-latency").textContent = latency != null ? `${Math.round(latency)} ms` : "--";
    $("vision-session").textContent = status.session_active ? "Active" : "Idle";
    $("vision-language").textContent = (status.experience && status.experience.language || "--").toUpperCase();
    $("vision-artwork").textContent = status.artwork.label || "None";
    $("vision-confidence").textContent = status.artwork.confidence == null
      ? "--" : `${Math.round(Number(status.artwork.confidence) * 100)}%`;
    $("vision-latency").textContent = latency != null ? `${Math.round(latency)} ms` : "--";
    // The overview shows answer state, not private visitor speech or answers.
    const interaction = status.last_interaction;
    $("vision-last-answer").textContent = interaction ? (interaction.state === "failed" ? "Last interaction needs attention. See the issue board." : interaction.state === "control" ? "Last voice control applied." : `Last ${interaction.source === "voice" ? "spoken" : "dashboard"} response completed.`)
      : status.last_answer && status.last_answer.answer ? "Last dashboard response completed." : "No response recorded yet.";
    $("btn-stop").disabled = !status.session_active;
    $("btn-capture").disabled = !cameraIsFresh(status.camera);
    if (!experienceDirty) {
      $("experience-state").textContent = status.session_active ? "Session active" : "Session idle";
    }
    $("estop-status").textContent = status.emergency_stopped ? "STOP ACTIVE" : "Safety clear";
    $("estop-status").className = `status-pill ${status.emergency_stopped ? "danger" : "ok"}`;

    syncExperienceForm(status.experience || {});

    const artwork = status.artwork || {};
    const confidence = artwork.confidence == null ? null : Number(artwork.confidence);
    $("camera-detection").textContent = artwork.label || "No artwork";
    $("camera-detection").className = `status-pill ${artwork.stable ? "ok" : "neutral"}`;
    $("camera-confidence").textContent = confidence == null ? "--" : `${Math.round(confidence * 100)}%`;
    $("camera-source").textContent = artwork.current_view_confirmed === false && artwork.artwork_id
      ? "Remembered artwork / not a confirmed current view"
      : artwork.artwork_id
      ? `${artwork.stable ? "Stable" : "Detecting"} / ${artwork.source}` : "Camera stream";
    const camera = status.camera || {};
    $("metric-camera").textContent = cameraIsFresh(camera) ? "Frame ready" : "Offline · optional";
    const cameraResolution = camera.actual_width && camera.actual_height
      ? ` @ ${camera.actual_width}x${camera.actual_height}` : "";
    $("vision-camera-fps").textContent = camera.observed_fps != null
      ? `${Number(camera.observed_fps).toFixed(1)} fps${cameraResolution}` : "--";
    if (camera.last_error) {
      $("camera-source").textContent = "Camera offline. Ask by artwork name or select one manually; voice conversation remains available.";
    }
    renderOperationalDetails();
  } catch (_) {
    if (_ instanceof AdminAccessChangedError) return;
    setIssue("status-request", { title: "Runtime connection lost", detail: "Live values are last known. Check the Jetson, network and ATLAS service.", severity: "danger", view: "logs" });
    $("admin-state").textContent = "Offline";
    $("admin-state").className = "status-pill danger";
  }
}

async function refreshHealth() {
  const list = $("health-list");
  list.replaceChildren();
  try {
    const health = await api("/health");
    latestHealth = health;
    setIssue("health-request", null);
    $("vision-stt").textContent = health.components.stt || "Unavailable";
    $("vision-tts").textContent = health.components.tts || "Unavailable";
    Object.entries(health.components).forEach(([name, value]) => {
      appendStatus(list, titleCase(name), providerLabel(value), !valueIsHealthy(value));
    });
    replaceIssues("health-", Object.entries(health.components).filter(([, value]) => componentState(value) !== "ok").map(([name, value]) => [name, { title: `${titleCase(name)} needs attention`, detail: componentState(value) === "warning" ? "A primary or fallback path is degraded, but another path is reported available." : "The runtime reported this component as unavailable or unhealthy. Review diagnostics.", severity: componentState(value), view: "audio-vision" }]));
    renderOperationalDetails();
  } catch (error) {
    if (error instanceof AdminAccessChangedError) return;
    latestHealth = null;
    setIssue("health-request", { title: "Component checks unavailable", detail: "Camera, speech and knowledge readiness cannot be confirmed.", severity: "danger", view: "audio-vision" });
    appendStatus(list, "dashboard", error.message, true);
  }
}

async function refreshContentChoices() {
  const [packs, artworks] = await Promise.all([api("/content/packs"), api("/artworks")]);
  [$("sel-pack"), $("content-pack")].forEach((select) => {
    select.replaceChildren();
    packs.forEach((pack) => {
      const option = document.createElement("option");
      option.value = pack.pack_id;
      option.textContent = pack.name;
      option.selected = Boolean(pack.selected);
      select.append(option);
    });
  });
  $("sel-artwork").replaceChildren();
  artworks.forEach((artwork) => {
    const option = document.createElement("option");
    option.value = artwork.artwork_id;
    option.textContent = artwork.title;
    $("sel-artwork").append(option);
  });
}

function setValue(id, value) {
  const node = $(id);
  if (node.type === "checkbox") node.checked = Boolean(value);
  else node.value = value;
}

function fillConfig(payload) {
  const config = payload.config;
  latestConfig = config;
  setValue("cfg-llm-provider", config.llm.provider);
  setValue("cfg-llm-model", config.llm.model);
  setValue("cfg-llm-timeout", config.llm.timeout_s);
  setValue("cfg-cloud-llm", config.llm.cloud_llm_enabled);
  setValue("cfg-streaming", config.llm.streaming_enabled);
  setValue("cfg-sentence-tts", config.llm.sentence_tts_enabled);
  setValue("cfg-stt", config.speech.stt_provider);
  setValue("cfg-tts", config.speech.tts_provider);
  setValue("cfg-deepgram-model", config.speech.deepgram_model);
  setValue("cfg-deepgram-language", config.speech.deepgram_language);
  setValue("cfg-listen-duration", config.speech.listen_duration_s);
  setValue("cfg-max-utterance", config.speech.max_utterance_s);
  setValue("cfg-cartesia-model", config.speech.cartesia_model);
  setValue("cfg-cartesia-voice", config.speech.cartesia_voice_id);
  setValue("cfg-vad-threshold", config.speech.silero_threshold);
  setValue("cfg-vad-silence", config.speech.silero_min_silence_ms);
  setValue("cfg-vad-hesitation", config.speech.silero_hesitation_silence_ms);
  setValue("cfg-cloud-speech", config.speech.cloud_speech_enabled);
  setValue("cfg-offline-fallback", config.speech.offline_fallback_enabled);
  setValue("cfg-yolo", config.hardware.yolo_backend);
  setValue("cfg-confidence", config.hardware.vision_conf_threshold);
  setValue("cfg-mask-confidence", config.hardware.vision_mask_conf_threshold);
  setValue("cfg-center-weight", config.hardware.vision_center_weight);
  setValue("cfg-center-threshold", config.hardware.vision_center_threshold);
  setValue("cfg-hold", config.hardware.vision_hold_seconds);
  setValue("cfg-gap-tolerance", config.hardware.vision_gap_tolerance_s);
  setValue("cfg-crop", config.hardware.manual_capture_crop_ratio);
  setValue("cfg-top-k", config.rag.top_k);
  setValue("cfg-dense-top-k", config.rag.dense_top_k);
  setValue("cfg-keyword-top-k", config.rag.keyword_top_k);
  setValue("cfg-chunk-words", config.rag.chunk_max_words);
  setValue("cfg-language-fallback", config.rag.language_fallback_enabled);
  setValue("cfg-fallback-language", config.rag.fallback_language);
  setValue("cfg-log-transcripts", config.logging.log_transcripts);
  setValue("cfg-log-live-stt", config.logging.log_live_stt);
  setValue("cfg-log-llm", config.logging.log_llm_responses);
  $("restart-badge").classList.toggle("hidden", !payload.restart_required);
  $("summary-llm").textContent = `${titleCase(config.llm.provider)} / ${config.llm.model}`;
  $("summary-speech").textContent = `${titleCase(config.speech.stt_provider)} / ${titleCase(config.speech.tts_provider)}`;
  $("summary-vision").textContent = `${titleCase(config.hardware.yolo_backend)} / ${Math.round(config.hardware.vision_conf_threshold * 100)}%`;
  $("summary-camera").textContent = `${config.hardware.camera_width}x${config.hardware.camera_height} @ ${config.hardware.camera_fps} fps`;
  $("summary-rag").textContent = `${config.rag.top_k} results / ${config.rag.fallback_language.toUpperCase()} fallback`;
  const enabledLogs = [config.logging.log_transcripts, config.logging.log_live_stt, config.logging.log_llm_responses].filter(Boolean).length;
  $("summary-logging").textContent = `${enabledLogs} of 3 enabled`;
  $("settings-summary-state").textContent = payload.restart_required ? "Restart required" : "Current";
  $("settings-summary-state").className = `status-pill ${payload.restart_required ? "warning" : "ok"}`;
  $("diag-yolo").textContent = titleCase(config.hardware.yolo_backend);
  $("diag-camera-mode").textContent = `${config.hardware.camera_width}x${config.hardware.camera_height} @ ${config.hardware.camera_fps}`;
  $("diag-vision-trigger").textContent = `${config.hardware.vision_hold_seconds}s hold / ${Math.round(config.hardware.vision_conf_threshold * 100)}%`;
}

async function loadConfig() {
  const payload = await api("/admin/config", {}, true);
  fillConfig(payload);
  adminUnlocked = true;
  if (authRequired) window.sessionStorage.setItem("atlasAdminToken", token());
  await refreshVisitorStatus();
}

function markExperienceDirty() {
  experienceDirty = true;
  $("experience-state").textContent = "Unsaved changes";
}

function syncExperienceForm(experience) {
  if (experienceDirty) return;
  $("sel-language").value = experience.language || "en";
  $("sel-profile").value = experience.profile || "adult_beginner";
  $("chk-accessibility").checked = Boolean(experience.accessibility_mode);
  if (experience.pack_id) $("sel-pack").value = experience.pack_id;
}

function setVisitorMonitorCollapsed(collapsed, { persist = true } = {}) {
  visitorMonitorCollapsed = collapsed;
  document.body.classList.toggle("visitor-monitor-collapsed", collapsed);
  $("visitor-live-panel").classList.toggle("is-collapsed", collapsed);
  $("btn-toggle-visitor-monitor").textContent = collapsed ? "Show monitor" : "Hide monitor";
  $("btn-toggle-visitor-monitor").setAttribute("aria-expanded", String(!collapsed));
  if (persist) window.sessionStorage.setItem("atlasVisitorMonitorCollapsed", String(collapsed));
}

function startRefreshLoops() {
  if (refreshIntervals.length) return;
  refreshIntervals = [
    window.setInterval(() => pollOnce("status", refreshStatus), 2000),
    window.setInterval(() => pollOnce("health", refreshHealth), 12000),
    window.setInterval(() => pollOnce("logs", refreshLogs), 2000),
    window.setInterval(() => pollOnce("visitor", refreshVisitorStatus), 1000),
    window.setInterval(() => pollOnce("audio", refreshAudio), 5000),
    window.setInterval(() => pollOnce("arducam", refreshArducamStatus), 2000),
    window.setInterval(refreshPanStatus, 500),
    window.setInterval(updateFreshness, 1000),
  ];
}

async function unlockAdmin({ quiet = false } = {}) {
  try {
    await loadConfig();
    setAdminLocked(false);
    await Promise.all([refreshStatus(), refreshHealth(), refreshContentChoices(), refreshLogs(true), refreshAudio()]);
    refreshCamera();
    refreshArducam();
    startRefreshLoops();
    if (!quiet) notice("Admin dashboard unlocked");
  } catch (error) {
    if (error instanceof AdminAccessChangedError) return;
    if (authRequired) {
      window.sessionStorage.removeItem("atlasAdminToken");
      setAdminLocked(true, "Token not accepted. Check it and try again.");
    }
    throw error;
  }
}

function numberValue(id) {
  return Number($(id).value);
}

function configPatch() {
  return {
    llm: {
      provider: $("cfg-llm-provider").value,
      model: $("cfg-llm-model").value.trim(),
      timeout_s: numberValue("cfg-llm-timeout"),
      cloud_llm_enabled: $("cfg-cloud-llm").checked,
      streaming_enabled: $("cfg-streaming").checked,
      sentence_tts_enabled: $("cfg-sentence-tts").checked,
    },
    speech: {
      stt_provider: $("cfg-stt").value,
      tts_provider: $("cfg-tts").value,
      deepgram_model: $("cfg-deepgram-model").value.trim(),
      deepgram_language: $("cfg-deepgram-language").value.trim(),
      listen_duration_s: numberValue("cfg-listen-duration"),
      max_utterance_s: numberValue("cfg-max-utterance"),
      cartesia_model: $("cfg-cartesia-model").value.trim(),
      cartesia_voice_id: $("cfg-cartesia-voice").value.trim(),
      silero_threshold: numberValue("cfg-vad-threshold"),
      silero_min_silence_ms: numberValue("cfg-vad-silence"),
      silero_hesitation_silence_ms: numberValue("cfg-vad-hesitation"),
      cloud_speech_enabled: $("cfg-cloud-speech").checked,
      offline_fallback_enabled: $("cfg-offline-fallback").checked,
    },
    hardware: {
      yolo_backend: $("cfg-yolo").value,
      vision_conf_threshold: numberValue("cfg-confidence"),
      vision_mask_conf_threshold: numberValue("cfg-mask-confidence"),
      vision_center_weight: numberValue("cfg-center-weight"),
      vision_center_threshold: numberValue("cfg-center-threshold"),
      vision_hold_seconds: numberValue("cfg-hold"),
      vision_gap_tolerance_s: numberValue("cfg-gap-tolerance"),
      manual_capture_crop_ratio: numberValue("cfg-crop"),
    },
    rag: {
      top_k: numberValue("cfg-top-k"),
      dense_top_k: numberValue("cfg-dense-top-k"),
      keyword_top_k: numberValue("cfg-keyword-top-k"),
      chunk_max_words: numberValue("cfg-chunk-words"),
      language_fallback_enabled: $("cfg-language-fallback").checked,
      fallback_language: $("cfg-fallback-language").value,
    },
    logging: {
      log_transcripts: $("cfg-log-transcripts").checked,
      log_live_stt: $("cfg-log-live-stt").checked,
      log_llm_responses: $("cfg-log-llm").checked,
    },
  };
}

function keepLogPosition(node, content) {
  const follow = node.scrollHeight - node.scrollTop - node.clientHeight < 48;
  node.textContent = content;
  if (follow) node.scrollTop = node.scrollHeight;
}

function logMatches(entry) {
  const query = $("log-search").value.trim().toLowerCase();
  const level = $("log-severity").value;
  const normalized = `${entry.actor} ${entry.text} ${JSON.stringify(entry.raw)}`.toLowerCase();
  if (query && !normalized.includes(query)) return false;
  if (level !== "all" && level && entry.level !== level) return false;
  return true;
}

function entryText(entry, guided) {
  if (!guided) return typeof entry.raw === "string" ? entry.raw : JSON.stringify(entry.raw, null, 2);
  return `${entry.actor}: ${entry.text}`;
}

function renderActivity(runtimeEntries, eventEntries) {
  const timeline = $("activity-timeline");
  const signature = JSON.stringify([...runtimeEntries, ...eventEntries]);
  if (timeline.dataset.signature === signature) return;
  const oldScroll = timeline.scrollTop;
  const openIds = new Set([...timeline.querySelectorAll("details[open]")].map(node => node.dataset.entryId));
  const focusedId = timeline.contains(document.activeElement) && document.activeElement.dataset.entryId;
  const fragment = document.createDocumentFragment();
  for (const [label, entries] of [["Session events", eventEntries], ["Runtime activity", runtimeEntries]]) {
    if (!entries.length) continue;
    const heading = document.createElement("h3");
    heading.className = "activity-source";
    heading.textContent = label;
    fragment.append(heading);
    const list = document.createElement("ol");
    list.className = "activity-list";
    entries.forEach((entry) => {
      const row = document.createElement("li");
      row.className = `activity-entry activity-${entry.kind} activity-level-${entry.level}`;
      row.dataset.entryId = entry.id;
      const header = document.createElement("div");
      header.className = "activity-entry-heading";
      const actor = document.createElement("strong");
      actor.textContent = entry.actor;
      const meta = document.createElement("span");
      meta.className = "activity-meta";
      // Preserve the original recorded time, including timezone if supplied.
      meta.textContent = `${entry.level === "info" ? "Update" : entry.level === "error" ? "Error" : "Warning"} · ${entry.timestamp || "No recorded time"}`;
      header.append(actor, meta);
      const description = document.createElement("p");
      description.textContent = entry.text;
      const detail = document.createElement("details");
      detail.dataset.entryId = entry.id;
      detail.open = openIds.has(entry.id);
      const summary = document.createElement("summary");
      summary.textContent = "Matching technical entry";
      summary.dataset.entryId = entry.id;
      const raw = document.createElement("pre");
      raw.textContent = entryText(entry, false);
      detail.append(summary, raw);
      row.append(header, description, detail);
      list.append(row);
    });
    fragment.append(list);
  }
  if (!runtimeEntries.length && !eventEntries.length) {
    const empty = document.createElement("p");
    empty.className = "activity-empty";
    empty.textContent = latestLogs.runtime.length + latestLogs.events.length ? "No updates match these filters. Try clearing the search or level filter." : "No activity has been recorded yet. Start ATLAS to see listening, artwork and response events.";
    fragment.append(empty);
  }
  timeline.replaceChildren(fragment);
  timeline.dataset.signature = signature;
  const focused = [...timeline.querySelectorAll("summary")].find(node => node.dataset.entryId === focusedId);
  if (focused) focused.focus({ preventScroll: true });
  timeline.scrollTop = $("chk-follow-activity").checked && !focusedId ? timeline.scrollHeight : oldScroll;
}

function renderLogSnapshot() {
  const guidedRuntime = logFormats.runtime === "human";
  const guidedEvents = logFormats.events === "human";
  const runtimeEntries = latestLogs.runtime.filter(logMatches);
  const eventEntries = latestLogs.events.filter(logMatches);
  $("runtime-log-view").classList.toggle("guided-log", guidedRuntime);
  $("event-log-view").classList.toggle("guided-log", guidedEvents);
  keepLogPosition($("runtime-log-view"), runtimeEntries.map(entry => entryText(entry, guidedRuntime)).join(guidedRuntime ? "\n\n" : "\n") || latestLogs.runtime_notice || "No matching runtime output.");
  keepLogPosition($("event-log-view"), eventEntries.map(entry => entryText(entry, guidedEvents)).join("\n\n") || "No matching events.");
  renderActivity(runtimeEntries, eventEntries);
  $("activity-count").textContent = `${runtimeEntries.length + eventEntries.length} of ${latestLogs.runtime.length + latestLogs.events.length} updates · shared snapshot${latestLogs.snapshot_id ? " " + latestLogs.snapshot_id.slice(0, 8) : " not yet loaded"}`;
  $("event-log-state").textContent = guidedEvents ? "Guided" : "Raw";

  const allEntries = [...latestLogs.runtime, ...latestLogs.events];
  $("log-runtime-count").textContent = String(latestLogs.runtime.length);
  $("log-event-count").textContent = String(latestLogs.events.length);
  $("log-warning-count").textContent = String(allEntries.filter(entry => entry.level === "warning").length);
  $("log-error-count").textContent = String(allEntries.filter(entry => entry.level === "error").length);
}

async function refreshLogs(force = false) {
  if (!adminUnlocked || logsRequestInFlight) return;
  if (!force && (document.hidden || document.body.dataset.adminView !== "logs")) return;
  if ($("chk-pause-logs").checked && !force) return;
  logsRequestInFlight = true;
  const generation = logRefreshGeneration;
  const requestToken = token();
  try {
    const snapshot = await api("/logs/snapshot?limit=250&event_limit=100", { cache: "no-store" }, true);
    if (!adminUnlocked || generation !== logRefreshGeneration || requestToken !== token()) return;
    if (!snapshot || !Array.isArray(snapshot.runtime) || !Array.isArray(snapshot.events) || !snapshot.snapshot_id) throw new Error("Incomplete activity snapshot.");
    latestLogs = snapshot;
    lastLogSync = Date.now();
    renderLogSnapshot();
    setIssue("logs-request", null);
    $("log-freshness").textContent = $("chk-pause-logs").checked ? "Paused · refreshed shared snapshot" : `Synced ${new Date().toLocaleTimeString()}`;
    $("runtime-log-state").textContent = snapshot.runtime_available ? "Synced" : "Unavailable";
    $("runtime-log-state").className = snapshot.runtime_available ? "ok" : "bad";
    const visibility = snapshot.text_visibility || {};
    $("activity-runtime-notice").textContent = snapshot.runtime_notice || "";
    $("activity-runtime-notice").classList.toggle("hidden", !snapshot.runtime_notice);
    $("activity-privacy").textContent = `Quoted text: user questions ${visibility.user_final ? "on" : "off"} · interim speech ${visibility.user_live ? "on" : "off"} · ATLAS responses ${visibility.atlas ? "on" : "off"}. Existing privacy switches apply; this view does not enable recording. Interim speech is not final. A written response is not proof of audible playback.`;
  } catch (_) {
    if (!adminUnlocked || generation !== logRefreshGeneration || requestToken !== token()) return;
    setIssue("logs-request", { title: "Live activity unavailable", detail: "Readable activity and technical logs are showing the same last known snapshot, not confirmed live. Check the connection and refresh.", severity: "warning", view: "logs" });
    $("log-freshness").textContent = "Offline · last shared snapshot";
    $("runtime-log-state").textContent = "Stale";
    $("runtime-log-state").className = "bad";
  } finally { logsRequestInFlight = false; }
}

async function applyExperience() {
  await api("/session/profile", { method: "POST", body: JSON.stringify({
    language: $("sel-language").value,
    profile: $("sel-profile").value,
    pack_id: $("sel-pack").value,
    accessibility_mode: $("chk-accessibility").checked,
  }) });
  experienceDirty = false;
}

function scheduleCameraRefresh(delayMs) {
  window.clearTimeout(cameraTimer);
  cameraTimer = window.setTimeout(refreshCamera, delayMs);
}

function showCameraImage(image, source) {
  return new Promise((resolve, reject) => {
    const finish = (error) => {
      window.clearTimeout(deadline);
      image.onload = image.onerror = null;
      if (error) reject(error); else resolve();
    };
    const deadline = window.setTimeout(() => finish(new Error("Preview decoding timed out.")), 5000);
    image.onload = () => finish();
    image.onerror = () => finish(new Error("Preview could not be displayed."));
    image.src = source;
  });
}

async function fetchPreview(path) {
  const accessGeneration = adminAccessGeneration;
  const requestToken = token();
  const controller = new AbortController();
  const deadline = window.setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(path, { cache: "no-store", headers: authRequired ? { "X-Atlas-Admin-Token": requestToken } : {}, signal: controller.signal });
    if (!adminUnlocked || accessGeneration !== adminAccessGeneration || requestToken !== token()) throw new AdminAccessChangedError();
    if (response.status === 401 && authRequired && requestToken === token()) {
      window.sessionStorage.removeItem("atlasAdminToken");
      setAdminLocked(true, "This token was not accepted. Try again.");
    }
    if (!response.ok) throw new Error("Preview unavailable.");
    const blob = await response.blob();
    if (!adminUnlocked || accessGeneration !== adminAccessGeneration || requestToken !== token()) throw new AdminAccessChangedError();
    return URL.createObjectURL(blob);
  } finally { window.clearTimeout(deadline); }
}

async function refreshCamera() {
  if (!adminUnlocked) return;
  if (document.hidden || !["main", "audio-vision"].includes(document.body.dataset.adminView)) {
    scheduleCameraRefresh(1000);
    return;
  }
  if (cameraRequestInFlight) return;
  const accessGeneration = adminAccessGeneration;
  const requestToken = token();
  cameraRequestInFlight = true;
  let nextUrl = null;
  try {
    nextUrl = await fetchPreview(`/camera/frame.jpg?t=${Date.now()}`);
    if (!adminUnlocked || accessGeneration !== adminAccessGeneration || requestToken !== token()) return;
    const image = $("admin-camera");
    const previousUrl = cameraObjectUrl;
    await showCameraImage(image, nextUrl);
    if (!adminUnlocked || accessGeneration !== adminAccessGeneration || requestToken !== token()) return;
    cameraObjectUrl = nextUrl;
    nextUrl = null;
    if (previousUrl) URL.revokeObjectURL(previousUrl);
    image.classList.remove("hidden");
    $("camera-empty").classList.add("hidden");
    setIssue("camera-preview", null);
    $("camera-state").textContent = "Live";
    $("camera-state").className = "status-pill ok";
    scheduleCameraRefresh(250);
  } catch (_) {
    if (!adminUnlocked || accessGeneration !== adminAccessGeneration || requestToken !== token()) return;
    if (cameraObjectUrl) {
      URL.revokeObjectURL(cameraObjectUrl);
      cameraObjectUrl = null;
    }
    $("admin-camera").removeAttribute("src");
    $("admin-camera").classList.add("hidden");
    $("camera-empty").classList.remove("hidden");
    $("camera-empty-detail").textContent = "No fresh preview. Voice conversation still works: ask about an artwork by name or select one manually. The camera retries automatically.";
    if (adminUnlocked) setIssue("camera-preview", { title: "Artwork preview unavailable", detail: "The dashboard cannot display a fresh image. Automatic retries are running.", severity: "warning", view: "audio-vision" });
    $("camera-state").textContent = "Unavailable";
    $("camera-state").className = "status-pill danger";
    scheduleCameraRefresh(1000);
  } finally {
    if (nextUrl) URL.revokeObjectURL(nextUrl);
    cameraRequestInFlight = false;
    // Unlock may have attempted a refresh while this old request was pending.
    if (adminUnlocked && (accessGeneration !== adminAccessGeneration || requestToken !== token())) scheduleCameraRefresh(0);
  }
}

function disablePanControls() {
  ["pan-left", "pan-right", "pan-center", "pan-position", "pan-pause", "pan-sweep"]
    .forEach(id => { $(id).disabled = true; });
}

function updatePanIssue(status) {
  setIssue("pan-status", status.enabled && !status.ready ? {
    title: "Camera movement needs attention", detail: status.detail,
    severity: status.mode === "fault" || status.emergency_stopped ? "danger" : "warning", view: "arducam",
  } : null);
}

function renderPanStatus(status) {
  latestPan = status;
  $("pan-state").textContent = `${status.simulated ? "Simulation · " : ""}${titleCase(status.mode)}`;
  $("pan-state").className = `status-pill ${status.mode === "fault" || status.emergency_stopped ? "danger" : status.ready ? "ok" : status.enabled ? "warning" : "neutral"}`;
  $("pan-angle").textContent = `${Number(status.commanded_angle).toFixed(1)}° commanded`;
  $("pan-connection").textContent = status.connection;
  if ($("pan-detail").textContent !== status.detail) $("pan-detail").textContent = status.detail;
  ["pan-left", "pan-right", "pan-center", "pan-position", "pan-pause", "pan-sweep"]
    .forEach(id => { $(id).disabled = !status.ready; });
  const slider = $("pan-position");
  slider.min = status.min_angle;
  slider.max = status.max_angle;
  if (document.activeElement !== slider) slider.value = status.commanded_angle;
  setIssue("pan-request", null);
  updatePanIssue(status);
  if (!status.ready) stopPanJog();
}

async function refreshPanStatus() {
  if (!adminUnlocked || document.hidden || document.body.dataset.adminView !== "arducam" || panStatusInFlight) return;
  panStatusInFlight = true;
  const generation = panGeneration;
  const requestToken = token();
  const sequence = panSequence;
  try {
    const status = await requestApi("/api/admin/arducam/pan/status", { cache: "no-store", timeoutMs: 1200 });
    if (adminUnlocked && generation === panGeneration && requestToken === token() && sequence === panSequence) renderPanStatus(status);
  } catch (_) {
    if (adminUnlocked && generation === panGeneration && requestToken === token() && sequence === panSequence) {
      stopPanJog();
      latestPan = null;
      disablePanControls();
      $("pan-state").textContent = "Unavailable";
      $("pan-state").className = "status-pill danger";
      $("pan-detail").textContent = "Connection lost. Held left/right movement expires automatically. Sweep or target motion may continue; cut servo power if needed.";
      setIssue("pan-request", { title: "Camera controls unavailable", detail: $("pan-detail").textContent, severity: "danger", view: "arducam" });
    }
  } finally { panStatusInFlight = false; }
}

async function sendPanCommand(action, fields = {}) {
  if (!adminUnlocked || !latestPan) return;
  const sequence = ++panSequence;
  const generation = panGeneration;
  const requestToken = token();
  try {
    // Release must be able to overtake a delayed renewal: no generic mutation lock.
    const status = await requestApi("/api/admin/arducam/pan/control", {
      method: "POST", cache: "no-store", timeoutMs: 1200,
      body: JSON.stringify({ action, client_id: panClientId, sequence,
        control_epoch: latestPan.control_epoch, ...fields }),
    });
    if (adminUnlocked && generation === panGeneration && requestToken === token() && sequence === panSequence) renderPanStatus(status);
  } catch (error) {
    if (adminUnlocked && generation === panGeneration && requestToken === token() && sequence === panSequence) {
      if (action === "jog") stopPanJog();
      notice(error.message, true);
    }
  }
}

function stopPanJog() {
  window.clearInterval(panJogTimer);
  panJogTimer = null;
  if (!panJogDirection) return;
  panJogDirection = 0;
  sendPanCommand("hold");
}

function startPanJog(direction) {
  if (!adminUnlocked || !latestPan?.ready || document.hidden || document.body.dataset.adminView !== "arducam" || panJogDirection === direction) return;
  stopPanJog();
  panJogDirection = direction;
  const renew = async () => {
    if (panJogRequestInFlight || !panJogDirection) return;
    panJogRequestInFlight = true;
    try { await sendPanCommand("jog", { direction: panJogDirection }); }
    finally { panJogRequestInFlight = false; }
  };
  renew();
  panJogTimer = window.setInterval(renew, 200);
}

for (const [id, direction] of [["pan-left", -1], ["pan-right", 1]]) {
  const button = $(id);
  button.addEventListener("pointerdown", event => {
    if (event.button !== 0 || button.disabled) return;
    event.preventDefault();
    button.setPointerCapture(event.pointerId);
    startPanJog(direction);
  });
  ["pointerup", "pointercancel", "lostpointercapture", "blur"].forEach(name => button.addEventListener(name, stopPanJog));
  button.addEventListener("keydown", event => {
    if ([" ", "Enter"].includes(event.key)) { event.preventDefault(); startPanJog(direction); }
  });
  button.addEventListener("keyup", event => {
    if ([" ", "Enter"].includes(event.key)) { event.preventDefault(); stopPanJog(); }
  });
}
window.addEventListener("blur", stopPanJog);
window.addEventListener("pagehide", stopPanJog);
document.addEventListener("visibilitychange", () => { if (document.hidden) stopPanJog(); });
for (const [id, action] of [["pan-center", "center"], ["pan-pause", "hold"], ["pan-sweep", "sweep"]]) {
  $(id).addEventListener("click", () => { stopPanJog(); sendPanCommand(action); });
}
$("pan-position").addEventListener("change", () => {
  stopPanJog();
  sendPanCommand("position", { angle: Number($("pan-position").value) });
});
$("pan-estop").addEventListener("click", async () => {
  stopPanJog();
  panGeneration++;
  disablePanControls();
  try {
    await requestApi("/hardware/emergency-stop", { method: "POST", timeoutMs: 1200 }, false);
    await refreshPanStatus();
    notice("Safety stop requested. Clear safety in Operations, then resume explicitly.");
  } catch (_) { notice("Stop unconfirmed. Cut servo power if motion continues.", true); }
});

function scheduleArducamRefresh(delayMs) {
  window.clearTimeout(arducamTimer);
  arducamTimer = window.setTimeout(refreshArducam, delayMs);
}

function renderArducamStatus(status) {
  const ready = Boolean(status.ready);
  setIssue("arducam-request", null);
  setIssue("arducam-status", status.enabled && (!ready || status.last_error) ? { title: "Arducam needs attention", detail: "The CSI camera is waiting or recovering. Check its connection and retry the preview.", severity: ready ? "warning" : "danger", view: "arducam" } : null);
  $("arducam-state").textContent = ready ? "Live" : (status.enabled ? "Waiting" : "Disabled");
  $("arducam-state").className = `status-pill ${ready ? "ok" : (status.enabled ? "warning" : "neutral")}`;
  $("arducam-source").textContent = status.source || "Jetson CSI / nvarguscamerasrc";
  $("arducam-sensor-id").textContent = status.sensor_id == null ? "--" : String(status.sensor_id);
  $("arducam-mode").textContent = `${status.configured_width || "--"}x${status.configured_height || "--"} @ ${status.configured_fps || "--"} fps`;
  $("arducam-fps").textContent = status.observed_fps == null ? "--" : `${Number(status.observed_fps).toFixed(1)} fps`;
  $("arducam-frame-age").textContent = status.last_frame_age_s == null ? "No frame" : `${Number(status.last_frame_age_s).toFixed(1)} s`;
  $("arducam-reconnects").textContent = String(status.reconnect_count || 0);
  $("arducam-pipeline").textContent = status.source && status.source.toLowerCase().includes("argus")
    ? "Argus CSI" : (status.source || "CSI camera");
  $("arducam-freshness").textContent = ready ? "Fresh frame" : (status.enabled ? "Waiting" : "Disabled");
  $("arducam-stability").textContent = status.reconnect_count
    ? `${status.reconnect_count} reconnect${status.reconnect_count === 1 ? "" : "s"}` : (ready ? "Stable" : "No samples");
  $("arducam-detail").textContent = status.last_error
    ? (status.operator_message || "Camera disconnected.")
    : (ready ? "Private live preview active. Frames are not stored." : "Opening the CSI camera.");
}

async function refreshArducamStatus() {
  if (!adminUnlocked || document.body.dataset.adminView !== "arducam") return;
  try {
    renderArducamStatus(await api("/api/admin/arducam/status", {}, true));
  } catch (error) {
    if (error instanceof AdminAccessChangedError) return;
    setIssue("arducam-request", { title: "Arducam status unavailable", detail: "CSI camera readiness cannot be confirmed. Check the connection.", severity: "danger", view: "arducam" });
    $("arducam-state").textContent = "Unavailable";
    $("arducam-state").className = "status-pill danger";
    $("arducam-detail").textContent = error.message;
  }
}

async function refreshArducam() {
  if (!adminUnlocked) return;
  if (document.hidden || document.body.dataset.adminView !== "arducam") {
    scheduleArducamRefresh(750);
    return;
  }
  if (arducamRequestInFlight) return;
  const accessGeneration = adminAccessGeneration;
  const requestToken = token();
  arducamRequestInFlight = true;
  let nextUrl = null;
  try {
    nextUrl = await fetchPreview(`/api/admin/arducam/frame.jpg?t=${Date.now()}`);
    if (!adminUnlocked || accessGeneration !== adminAccessGeneration || requestToken !== token()) return;
    const image = $("admin-arducam");
    const previousUrl = arducamObjectUrl;
    await showCameraImage(image, nextUrl);
    if (!adminUnlocked || accessGeneration !== adminAccessGeneration || requestToken !== token()) return;
    arducamObjectUrl = nextUrl;
    nextUrl = null;
    if (previousUrl) URL.revokeObjectURL(previousUrl);
    image.classList.remove("hidden");
    $("arducam-empty").classList.add("hidden");
    setIssue("arducam-preview", null);
    $("arducam-state").textContent = "Live";
    $("arducam-state").className = "status-pill ok";
    scheduleArducamRefresh(250);
  } catch (error) {
    if (!adminUnlocked || accessGeneration !== adminAccessGeneration || requestToken !== token()) return;
    if (arducamObjectUrl) {
      URL.revokeObjectURL(arducamObjectUrl);
      arducamObjectUrl = null;
    }
    $("admin-arducam").removeAttribute("src");
    $("admin-arducam").classList.add("hidden");
    $("arducam-empty").classList.remove("hidden");
    $("arducam-empty-detail").textContent = "No fresh preview. Check the CSI camera connection. Automatic retries are running.";
    if (adminUnlocked) setIssue("arducam-preview", { title: "Arducam preview unavailable", detail: "The dashboard cannot display a fresh CSI image. Automatic retries are running.", severity: "warning", view: "arducam" });
    $("arducam-state").textContent = "Unavailable";
    $("arducam-state").className = "status-pill danger";
    $("arducam-detail").textContent = "Preview unavailable. Check the CSI connection and retry.";
    scheduleArducamRefresh(1000);
  } finally {
    if (nextUrl) URL.revokeObjectURL(nextUrl);
    arducamRequestInFlight = false;
    if (adminUnlocked && (accessGeneration !== adminAccessGeneration || requestToken !== token())) scheduleArducamRefresh(0);
  }
}

$("btn-unlock").addEventListener("click", () => unlockAdmin()
  .catch((error) => notice(error.message, true)));
$("inp-token").addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    $("btn-unlock").click();
  }
});
$("config-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const result = await api("/admin/config", { method: "PUT", body: JSON.stringify(configPatch()) }, true);
    fillConfig(result);
    notice("Settings saved. Restart ATLAS to apply them.");
  } catch (error) { notice(error.message, true); }
});

$("btn-refresh").addEventListener("click", () => Promise.all([
  pollOnce("status", refreshStatus), pollOnce("health", refreshHealth), pollOnce("logs", () => refreshLogs(true)),
  pollOnce("visitor", refreshVisitorStatus), pollOnce("audio", refreshAudio), pollOnce("arducam", refreshArducamStatus),
]));
$("btn-clear-action-error").addEventListener("click", () => setIssue("action", null));
$("btn-show-issues").addEventListener("click", () => {
  $("issue-board").scrollIntoView({ block: "start" });
  $("issue-title").focus({ preventScroll: true });
});
$("chk-pause-logs").addEventListener("change", () => {
  logRefreshGeneration++;
  $("log-freshness").textContent = $("chk-pause-logs").checked ? "Paused · last snapshot" : "Resuming updates";
  if (!$("chk-pause-logs").checked) refreshLogs(true);
});
document.querySelectorAll("[data-admin-tab]").forEach((button) => {
  button.addEventListener("click", () => setAdminView(button.dataset.adminTab));
});
document.querySelectorAll("[data-audio-route]").forEach((button) => {
  button.addEventListener("click", async () => {
    try {
      await applyAudioChange({ route: button.dataset.audioRoute });
      notice(`Audio output changed to ${button.textContent}.`);
    } catch (error) { notice(error.message, true); }
  });
});
$("btn-refresh-arducam").addEventListener("click", () => {
  refreshArducamStatus();
  refreshArducam();
});
$("audio-volume").addEventListener("input", () => {
  const volume = Number($("audio-volume").value);
  $("audio-volume-value").textContent = `${volume}%`;
  window.clearTimeout(audioVolumeTimer);
  audioVolumeTimer = window.setTimeout(() => applyAudioChange({ volume_percent: volume })
    .catch((error) => notice(error.message, true)), 180);
});
$("btn-test-audio").addEventListener("click", async () => {
  try {
    const result = await api("/api/admin/audio/test", { method: "POST" }, true);
    renderAudioStatus(result.audio);
    notice("Test sound played through the selected output.");
  } catch (error) { notice(error.message, true); }
});
$("btn-start-demo").addEventListener("click", async () => {
  try {
    await api("/api/admin/demo/start", {
      method: "POST",
      body: JSON.stringify({
        language: $("sel-language").value,
        profile: $("sel-profile").value,
        pack_id: $("sel-pack").value || null,
        accessibility_mode: $("chk-accessibility").checked,
      }),
    }, true);
    experienceDirty = false;
    $("experience-state").textContent = "Demo active";
    notice("Demo mode active. ATLAS will continue until End is pressed.");
    await Promise.all([refreshStatus(), refreshVisitorStatus()]);
  } catch (error) { notice(error.message, true); }
});
$("btn-stop").addEventListener("click", () => api("/api/admin/session/stop", { method: "POST" }, true)
  .then(() => {
    experienceDirty = false;
    $("experience-state").textContent = "Ready";
    notice("Demo mode stopped.");
    return Promise.all([refreshStatus(), refreshVisitorStatus()]);
  })
  .catch((error) => notice(error.message, true)));
$("btn-apply-experience").addEventListener("click", () => applyExperience().then(() => { notice("Experience settings applied"); refreshStatus(); }).catch((error) => notice(error.message, true)));

["sel-language", "sel-profile", "sel-pack", "chk-accessibility"].forEach((id) => {
  $(id).addEventListener("change", markExperienceDirty);
});
document.querySelectorAll("[data-log-view]").forEach((button) => {
  button.addEventListener("click", () => {
    logFormats[button.dataset.logView] = button.dataset.logFormat;
    document.querySelectorAll(`[data-log-view="${button.dataset.logView}"]`).forEach((peer) => {
      peer.setAttribute("aria-pressed", String(peer === button));
      peer.classList.toggle("active", peer === button);
    });
    renderLogSnapshot();
  });
});
$("cfg-llm-provider").addEventListener("change", () => {
  const defaults = { gemini: "gemini-2.5-flash", openai: "gpt-5", kimi: "kimi-k2.5" };
  const provider = $("cfg-llm-provider").value;
  const model = $("cfg-llm-model");
  if (defaults[provider] && Object.values(defaults).includes(model.value.trim())) {
    model.value = defaults[provider];
  }
});

$("btn-override").addEventListener("click", () => api("/session/manual-artwork", { method: "POST", body: JSON.stringify({ artwork_id: $("sel-artwork").value }) }).then(refreshStatus).catch((error) => notice(error.message, true)));
$("btn-clear-override").addEventListener("click", () => api("/session/manual-artwork", { method: "DELETE" }).then(refreshStatus).catch((error) => notice(error.message, true)));
$("btn-capture").addEventListener("click", () => api("/session/capture", { method: "POST" }).then(() => notice("Artwork capture requested")).catch((error) => notice(error.message, true)));

$("btn-ingest").addEventListener("click", () => api("/content/ingest", { method: "POST", body: JSON.stringify({ pack_id: $("content-pack").value, reset: true }) }, true).then((result) => renderObject("content-result", result)).catch((error) => notice(error.message, true)));
$("btn-eval").addEventListener("click", () => api("/eval/rag", { method: "POST" }, true).then((result) => renderObject("content-result", result)).catch((error) => notice(error.message, true)));
$("btn-estop").addEventListener("click", () => api("/hardware/emergency-stop", { method: "POST" }, false).then(() => { notice("Emergency stop applied."); return Promise.all([refreshStatus(), refreshHealth()]); }).catch((error) => notice(error.message, true)));
$("btn-clear-estop").addEventListener("click", () => api("/hardware/clear-emergency-stop", { method: "POST" }, true).then(() => Promise.all([refreshStatus(), refreshHealth()])).catch((error) => notice(error.message, true)));
$("btn-refresh-logs").addEventListener("click", () => refreshLogs(true));
$("log-search").addEventListener("input", renderLogSnapshot);
$("log-severity").addEventListener("change", renderLogSnapshot);
$("btn-clear-log-filter").addEventListener("click", () => {
  $("log-search").value = "";
  $("log-severity").value = "all";
  renderLogSnapshot();
});
$("btn-export-logs").addEventListener("click", () => {
  const snapshot = [
    "ATLAS admin log snapshot",
    `Captured: ${latestLogs.captured_at || "No snapshot loaded"}`,
    `Shared snapshot: ${latestLogs.snapshot_id || "none"}`,
    "READABLE ACTIVITY",
    ...[...latestLogs.runtime, ...latestLogs.events].map(entry => entryText(entry, true)),
    "",
    "RUNTIME",
    ...latestLogs.runtime.map(entry => entryText(entry, false)),
    "",
    "EVENTS",
    ...latestLogs.events.map(entry => entryText(entry, false)),
  ].join("\n");
  const url = URL.createObjectURL(new Blob([snapshot], { type: "text/plain;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `atlas-logs-${new Date().toISOString().replaceAll(":", "-")}.txt`;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  // Revoking immediately can cancel the browser before it reads the download.
  window.setTimeout(() => URL.revokeObjectURL(url), 10000);
  notice("Log snapshot exported.");
});
document.querySelectorAll("[data-sim]").forEach((button) => {
  button.addEventListener("click", () => api("/demo/simulate", { method: "POST", body: JSON.stringify({ scenario: button.dataset.sim }) }, true).then((result) => { renderObject("content-result", result); refreshLogs(true); }).catch((error) => notice(error.message, true)));
});

$("btn-enable-help-alerts").addEventListener("click", () => {
  helpAlertsEnabled = true;
  $("btn-enable-help-alerts").textContent = "Help sound enabled";
  $("btn-enable-help-alerts").disabled = true;
  notice("One quiet tone will play for each new help request.");
});
$("btn-toggle-visitor-monitor").addEventListener("click", () => {
  setVisitorMonitorCollapsed(!visitorMonitorCollapsed);
});
$("btn-ack-help").addEventListener("click", async () => {
  if (!currentHelpRequestId) return;
  try {
    await api(`/api/admin/help/${currentHelpRequestId}/acknowledge`, { method: "POST" }, true);
    notice("Visitor help request acknowledged.");
    await refreshVisitorStatus();
  } catch (error) { notice(error.message, true); }
});
$("btn-visitor-stop").addEventListener("click", async () => {
  if (!window.confirm("Stop the visitor experience and clear its temporary profile?")) return;
  try {
    await api("/api/admin/session/stop", { method: "POST" }, true);
    notice("Visitor experience stopped and profile cleared.");
    await refreshVisitorStatus();
  } catch (error) { notice(error.message, true); }
});
$("btn-visitor-simulate").addEventListener("click", async () => {
  try {
    await api("/api/admin/visitor/simulate", {
      method: "POST",
      body: JSON.stringify({ scenario: $("sel-visitor-simulation").value }),
    }, true);
    await refreshVisitorStatus();
    notice("Visitor mock scenario applied.");
  } catch (error) { notice(error.message, true); }
});

async function initialize() {
  setAdminView(window.sessionStorage.getItem("atlasAdminView") || "main", { persist: false });
  setVisitorMonitorCollapsed(window.sessionStorage.getItem("atlasVisitorMonitorCollapsed") === "true", { persist: false });
  const access = await api("/admin/access", {}, false);
  authRequired = Boolean(access.auth_required);
  if (authRequired) {
    const remembered = window.sessionStorage.getItem("atlasAdminToken");
    if (!remembered) {
      setAdminLocked(true, "Enter the administrator token to continue.");
      return;
    }
    $("inp-token").value = remembered;
    try {
      await unlockAdmin({ quiet: true });
    } catch (_) {
      // The gate now explains the failed remembered token without exposing controls.
    }
  } else {
    $("local-mode").classList.remove("hidden");
    await unlockAdmin({ quiet: true });
  }
}

initialize().catch((error) => notice(error.message, true));
