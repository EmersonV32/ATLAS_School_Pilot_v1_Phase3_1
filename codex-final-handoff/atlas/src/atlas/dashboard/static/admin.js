/* ATLAS operations dashboard. No build step or external dependencies. */
"use strict";

const $ = (id) => document.getElementById(id);
let authRequired = true;
let adminUnlocked = false;
let cameraTimer = null;
let currentHelpRequestId = null;
let lastAlertedHelpRequestId = null;
let helpAlertsEnabled = false;

function token() {
  return $("inp-token").value.trim();
}

async function api(path, options = {}, protectedRoute = false) {
  if (protectedRoute && authRequired && !token()) throw new Error("Admin token required");
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (protectedRoute && authRequired) headers["X-Atlas-Admin-Token"] = token();
  const response = await fetch(path, { ...options, headers });
  let body = null;
  try { body = await response.json(); } catch (_) { /* no response body */ }
  if (!response.ok) {
    const detail = body && body.detail ? body.detail : response.statusText;
    throw new Error(String(detail));
  }
  return body;
}

function notice(message, bad = false) {
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
  return { under_13: "Under 13", "13_17": "13–17", "18_plus": "18+" }[value]
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
  const state = payload.state;
  const readiness = payload.readiness;
  const help = payload.help_request;
  const connected = state.connection === "online";
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
    $("visitor-help-badge").textContent = titleCase(help.status);
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
    $("visitor-live-state").textContent = "Unavailable";
    $("visitor-live-state").className = "status-pill danger";
  }
}

async function refreshStatus() {
  try {
    const status = await api("/status");
    $("admin-state").textContent = status.emergency_stopped ? "Emergency stop" : "Online";
    $("admin-state").className = `status-pill ${status.emergency_stopped ? "danger" : "ok"}`;
    $("metric-mode").textContent = status.mode;
    $("metric-session").textContent = status.session_active ? "Active" : "Idle";
    $("metric-artwork").textContent = status.artwork.label || "None";
    $("metric-latency").textContent = status.last_answer && status.last_answer.latency_ms != null
      ? `${Math.round(status.last_answer.latency_ms)} ms` : "--";
    $("vision-session").textContent = status.session_active ? "Active" : "Idle";
    $("vision-language").textContent = (status.experience && status.experience.language || "--").toUpperCase();
    $("vision-artwork").textContent = status.artwork.label || "None";
    $("vision-confidence").textContent = status.artwork.confidence == null
      ? "--" : `${Math.round(Number(status.artwork.confidence) * 100)}%`;
    $("vision-latency").textContent = status.last_answer && status.last_answer.latency_ms != null
      ? `${Math.round(status.last_answer.latency_ms)} ms` : "--";
    $("vision-last-answer").textContent = status.last_answer && status.last_answer.answer
      ? status.last_answer.answer : "No answer yet.";
    $("btn-start").disabled = status.session_active;
    $("btn-stop").disabled = !status.session_active;
    $("experience-state").textContent = status.session_active ? "Session active" : "Session idle";
    $("estop-status").textContent = status.emergency_stopped ? "STOP ACTIVE" : "Safety clear";
    $("estop-status").className = `status-pill ${status.emergency_stopped ? "danger" : "ok"}`;

    const experience = status.experience || {};
    $("sel-language").value = experience.language || "en";
    $("sel-profile").value = experience.profile || "adult_beginner";
    $("chk-accessibility").checked = Boolean(experience.accessibility_mode);
    if (experience.pack_id) $("sel-pack").value = experience.pack_id;

    const artwork = status.artwork || {};
    const confidence = artwork.confidence == null ? null : Number(artwork.confidence);
    $("camera-detection").textContent = artwork.label || "No artwork";
    $("camera-detection").className = `status-pill ${artwork.stable ? "ok" : "neutral"}`;
    $("camera-confidence").textContent = confidence == null ? "--" : `${Math.round(confidence * 100)}%`;
    $("camera-source").textContent = artwork.artwork_id
      ? `${artwork.stable ? "Stable" : "Detecting"} / ${artwork.source}` : "Camera stream";
  } catch (_) {
    $("admin-state").textContent = "Offline";
    $("admin-state").className = "status-pill danger";
  }
}

async function refreshHealth() {
  const list = $("health-list");
  list.replaceChildren();
  try {
    const health = await api("/health");
    $("vision-stt").textContent = health.components.stt || "Unavailable";
    $("vision-tts").textContent = health.components.tts || "Unavailable";
    Object.entries(health.components).forEach(([name, value]) => {
      appendStatus(list, name, value, String(value).startsWith("error"));
    });
  } catch (error) {
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
  setValue("cfg-cartesia-model", config.speech.cartesia_model);
  setValue("cfg-cartesia-voice", config.speech.cartesia_voice_id);
  setValue("cfg-vad-threshold", config.speech.silero_threshold);
  setValue("cfg-vad-silence", config.speech.silero_min_silence_ms);
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
}

async function loadConfig() {
  const payload = await api("/admin/config", {}, true);
  fillConfig(payload);
  adminUnlocked = true;
  if (authRequired) window.sessionStorage.setItem("atlasAdminToken", token());
  await refreshVisitorStatus();
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
      cartesia_model: $("cfg-cartesia-model").value.trim(),
      cartesia_voice_id: $("cfg-cartesia-voice").value.trim(),
      silero_threshold: numberValue("cfg-vad-threshold"),
      silero_min_silence_ms: numberValue("cfg-vad-silence"),
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

async function refreshLogs(force = false) {
  if ($("chk-pause-logs").checked && !force) return;
  try {
    const [runtime, events] = await Promise.all([
      api("/logs/runtime?limit=500", {}, true),
      api("/logs/recent?limit=200"),
    ]);
    keepLogPosition($("runtime-log-view"), runtime.lines.join("\n") || "No runtime output yet.");
    keepLogPosition($("event-log-view"), JSON.stringify(events, null, 2));
    $("runtime-log-state").textContent = runtime.available ? "Live" : "Unavailable";
    $("runtime-log-state").className = runtime.available ? "ok" : "bad";
  } catch (error) {
    $("runtime-log-state").textContent = "Error";
    keepLogPosition($("runtime-log-view"), error.message);
  }
}

async function applyExperience() {
  await api("/session/profile", { method: "POST", body: JSON.stringify({
    language: $("sel-language").value,
    profile: $("sel-profile").value,
    pack_id: $("sel-pack").value,
    accessibility_mode: $("chk-accessibility").checked,
  }) });
}

function refreshCamera() {
  window.clearTimeout(cameraTimer);
  $("admin-camera").src = `/camera/frame.jpg?t=${Date.now()}`;
}

$("admin-camera").addEventListener("load", () => {
  $("camera-state").textContent = "Live";
  $("camera-state").className = "status-pill ok";
  cameraTimer = window.setTimeout(refreshCamera, 200);
});
$("admin-camera").addEventListener("error", () => {
  $("camera-state").textContent = "Unavailable";
  $("camera-state").className = "status-pill danger";
  cameraTimer = window.setTimeout(refreshCamera, 1000);
});

$("btn-unlock").addEventListener("click", () => loadConfig()
  .then(() => notice("Admin controls unlocked"))
  .catch((error) => notice(error.message, true)));
$("config-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const result = await api("/admin/config", { method: "PUT", body: JSON.stringify(configPatch()) }, true);
    fillConfig(result);
    notice("Settings saved. Restart ATLAS to apply them.");
  } catch (error) { notice(error.message, true); }
});

$("btn-refresh").addEventListener("click", () => Promise.all([
  refreshStatus(), refreshHealth(), refreshLogs(true), refreshVisitorStatus(),
]));
$("btn-start").addEventListener("click", async () => {
  try { await applyExperience(); await api("/session/start", { method: "POST" }); await refreshStatus(); }
  catch (error) { notice(error.message, true); }
});
$("btn-stop").addEventListener("click", () => api("/session/stop", { method: "POST" }).then(refreshStatus).catch((error) => notice(error.message, true)));
$("btn-apply-experience").addEventListener("click", () => applyExperience().then(() => { notice("Experience settings applied"); refreshStatus(); }).catch((error) => notice(error.message, true)));

$("btn-override").addEventListener("click", () => api("/session/manual-artwork", { method: "POST", body: JSON.stringify({ artwork_id: $("sel-artwork").value }) }).then(refreshStatus).catch((error) => notice(error.message, true)));
$("btn-clear-override").addEventListener("click", () => api("/session/manual-artwork", { method: "DELETE" }).then(refreshStatus).catch((error) => notice(error.message, true)));
$("btn-capture").addEventListener("click", () => api("/session/capture", { method: "POST" }).then(() => notice("Artwork capture requested")).catch((error) => notice(error.message, true)));

$("btn-ingest").addEventListener("click", () => api("/content/ingest", { method: "POST", body: JSON.stringify({ pack_id: $("content-pack").value, reset: true }) }, true).then((result) => renderObject("content-result", result)).catch((error) => notice(error.message, true)));
$("btn-eval").addEventListener("click", () => api("/eval/rag", { method: "POST" }, true).then((result) => renderObject("content-result", result)).catch((error) => notice(error.message, true)));
$("btn-estop").addEventListener("click", () => api("/hardware/emergency-stop", { method: "POST" }).then(() => Promise.all([refreshStatus(), refreshHealth()])));
$("btn-clear-estop").addEventListener("click", () => api("/hardware/clear-emergency-stop", { method: "POST" }, true).then(() => Promise.all([refreshStatus(), refreshHealth()])).catch((error) => notice(error.message, true)));
$("btn-refresh-logs").addEventListener("click", () => refreshLogs(true));
document.querySelectorAll("[data-sim]").forEach((button) => {
  button.addEventListener("click", () => api("/demo/simulate", { method: "POST", body: JSON.stringify({ scenario: button.dataset.sim }) }, true).then((result) => { renderObject("content-result", result); refreshLogs(true); }).catch((error) => notice(error.message, true)));
});

$("btn-enable-help-alerts").addEventListener("click", () => {
  helpAlertsEnabled = true;
  $("btn-enable-help-alerts").textContent = "Help sound enabled";
  $("btn-enable-help-alerts").disabled = true;
  notice("One quiet tone will play for each new help request.");
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
  const access = await api("/admin/access");
  authRequired = Boolean(access.auth_required);
  if (authRequired) {
    $("auth-controls").classList.remove("hidden");
    const remembered = window.sessionStorage.getItem("atlasAdminToken");
    if (remembered) $("inp-token").value = remembered;
  } else {
    $("local-mode").classList.remove("hidden");
  }
  await Promise.all([
    refreshStatus(), refreshHealth(), refreshContentChoices(), refreshVisitorStatus(),
  ]);
  if (!authRequired || token()) {
    try { await loadConfig(); } catch (error) { if (!authRequired) throw error; }
  }
  await refreshLogs(true);
  refreshCamera();
}

initialize().catch((error) => notice(error.message, true));
window.setInterval(refreshStatus, 2000);
window.setInterval(refreshHealth, 12000);
window.setInterval(refreshLogs, 1500);
window.setInterval(refreshVisitorStatus, 1000);
