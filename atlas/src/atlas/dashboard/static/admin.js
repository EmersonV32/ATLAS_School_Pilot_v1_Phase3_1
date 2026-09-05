/* ATLAS operations dashboard. No build step or external dependencies. */
"use strict";

const $ = (id) => document.getElementById(id);
let authRequired = true;
let adminUnlocked = false;
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
let audioVolumeTimer = null;
const logFormats = { runtime: "human", events: "human" };
let latestStatus = null;
let latestHealth = null;
let latestAudio = null;
let latestConfig = null;
let latestLogs = { runtime: [], events: [] };

function token() {
  return $("inp-token").value.trim();
}

function setAdminLocked(locked, message = "") {
  document.body.classList.toggle("admin-locked", locked);
  document.body.classList.toggle("admin-unlocked", !locked);
  $("admin-unlock-gate").setAttribute("aria-hidden", String(!locked));
  $("admin-unlock-message").textContent = message;
  if (locked) window.setTimeout(() => $("inp-token").focus(), 0);
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
    if (protectedRoute && response.status === 401 && authRequired) {
      window.sessionStorage.removeItem("atlasAdminToken");
      setAdminLocked(true, "This token was not accepted. Try again.");
    }
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
  const helpRequested = Boolean(help && help.status === "requested");
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
    $("visitor-live-state").textContent = "Unavailable";
    $("visitor-live-state").className = "status-pill danger";
  }
}

function valueIsHealthy(value) {
  const normalized = String(value || "").toLowerCase();
  return Boolean(normalized) && !normalized.includes("error") && !normalized.includes("unavailable");
}

function renderDemoReadiness() {
  if (!latestStatus) return;
  const status = latestStatus;
  const components = latestHealth && latestHealth.components || {};
  const camera = status.camera || {};
  const audioReady = latestAudio && (
    latestAudio.route === "speaker" ? latestAudio.speaker_available : latestAudio.headset_available
  );
  const checks = [
    ["Runtime", !status.emergency_stopped, status.emergency_stopped ? "Stopped" : "Safety clear"],
    ["Speech input", valueIsHealthy(components.stt), providerLabel(components.stt)],
    ["Speech output", valueIsHealthy(components.tts), providerLabel(components.tts)],
    ["Artwork camera", Boolean(camera.ready), camera.ready ? "Frame ready" : "Disconnected"],
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
  const sessionActive = Boolean(status.session_active);
  const demoActive = Boolean(status.demo_active);

  $("demo-cycle-state").textContent = demoActive ? "Running" : "Waiting";
  $("demo-cycle-state").className = `status-pill ${demoActive ? "ok" : "neutral"}`;
  $("demo-stage-listen").textContent = sessionActive ? "Listening loop active" : "Idle";
  $("demo-stage-language").textContent = status.experience && status.experience.language
    ? status.experience.language.toUpperCase() : "No language";
  $("demo-stage-artwork").textContent = artwork.label || "No artwork";
  $("demo-stage-response").textContent = answer.answer ? "Answer delivered" : "No response";

  $("diag-camera").textContent = camera.ready ? "Connected" : "Disconnected";
  $("diag-yolo").textContent = latestConfig
    ? titleCase(latestConfig.hardware.yolo_backend)
    : providerLabel(components.vision);
  $("diag-stt").textContent = providerLabel(components.stt);
  $("diag-tts").textContent = providerLabel(components.tts);
  const criticalGood = camera.ready && valueIsHealthy(components.stt) && valueIsHealthy(components.tts);
  $("signal-state").textContent = criticalGood ? "Ready" : "Needs attention";
  $("signal-state").className = `status-pill ${criticalGood ? "ok" : "warning"}`;
  renderDemoReadiness();
}

function setAdminView(view, { persist = true } = {}) {
  const supported = new Set(["main", "demo", "audio-vision", "arducam", "visitor", "logs", "settings"]);
  const nextView = supported.has(view) ? view : "main";
  document.body.dataset.adminView = nextView;
  document.querySelectorAll("[data-admin-tab]").forEach((button) => {
    const active = button.dataset.adminTab === nextView;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  document.querySelectorAll("[data-admin-views]").forEach((panel) => {
    panel.classList.toggle("view-hidden", !panel.dataset.adminViews.split(" ").includes(nextView));
  });
  if (persist) window.sessionStorage.setItem("atlasAdminView", nextView);
  if (nextView === "arducam" && adminUnlocked) {
    refreshArducamStatus();
    refreshArducam();
  }
}

function providerLabel(provider) {
  if (typeof provider === "string") return provider;
  if (!provider || typeof provider !== "object") return "Unknown";
  return provider.active || provider.provider || provider.primary || "Fallback ready";
}

function renderAudioStatus(status) {
  latestAudio = status;
  const routeAvailable = status.route === "speaker" ? status.speaker_available : status.headset_available;
  document.querySelectorAll("[data-audio-route]").forEach((button) => {
    const active = button.dataset.audioRoute === status.route;
    button.setAttribute("aria-pressed", String(active));
  });
  $("audio-volume").value = status.volume_percent;
  $("audio-volume-value").textContent = `${status.volume_percent}%`;
  $("audio-output-name").textContent = status.output_device_name;
  $("audio-provider").textContent = providerLabel(status.provider);
  $("audio-state").textContent = routeAvailable ? `${titleCase(status.route)} active` : `${titleCase(status.route)} unavailable`;
  $("audio-state").className = `status-pill ${routeAvailable ? "ok" : "warning"}`;
  $("metric-audio").textContent = routeAvailable ? titleCase(status.route) : "Unavailable";
  $("diag-audio-output").textContent = status.output_device_name || "Unavailable";
  $("diag-audio-input").textContent = status.headset_name || "Shokz headset";
  const headset = document.querySelector('[data-audio-route="headset"]');
  const speaker = document.querySelector('[data-audio-route="speaker"]');
  headset.title = status.headset_available ? "Shokz output is available" : "Shokz output is not currently detected";
  speaker.title = status.speaker_available ? "Judge speaker is available" : "Judge speaker is not currently detected";
  renderOperationalDetails();
}

async function refreshAudio() {
  try {
    renderAudioStatus(await api("/api/admin/audio", {}, true));
  } catch (error) {
    $("audio-state").textContent = "Unavailable";
    $("audio-state").className = "status-pill danger";
    if (adminUnlocked) console.warn("Audio status unavailable", error);
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
    $("btn-stop").disabled = !status.session_active;
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
    $("camera-source").textContent = artwork.artwork_id
      ? `${artwork.stable ? "Stable" : "Detecting"} / ${artwork.source}` : "Camera stream";
    const camera = status.camera || {};
    $("metric-camera").textContent = camera.ready ? "Live" : "Disconnected";
    $("vision-camera-fps").textContent = camera.observed_fps != null
      ? `${Number(camera.observed_fps).toFixed(1)} fps` : "--";
    if (camera.last_error) {
      $("camera-source").textContent = `Recovering: ${camera.last_error}`;
    }
    renderOperationalDetails();
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
    latestHealth = health;
    $("vision-stt").textContent = health.components.stt || "Unavailable";
    $("vision-tts").textContent = health.components.tts || "Unavailable";
    Object.entries(health.components).forEach(([name, value]) => {
      appendStatus(list, name, value, String(value).startsWith("error"));
    });
    renderOperationalDetails();
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
    window.setInterval(refreshStatus, 2000),
    window.setInterval(refreshHealth, 12000),
    window.setInterval(refreshLogs, 1500),
    window.setInterval(refreshVisitorStatus, 1000),
    window.setInterval(refreshAudio, 5000),
    window.setInterval(refreshArducamStatus, 2000),
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

function logMatches(text) {
  const query = $("log-search").value.trim().toLowerCase();
  const level = $("log-severity").value;
  const normalized = String(text).toLowerCase();
  if (query && !normalized.includes(query)) return false;
  if (level === "warning" && !normalized.includes("warning") && !normalized.includes("warn")) return false;
  if (level === "error" && !normalized.includes("error") && !normalized.includes("failed") && !normalized.includes("exception")) return false;
  return true;
}

function eventText(event, guided) {
  if (!guided) return JSON.stringify(event, null, 2);
  return `${event.summary || "Event"}\n${event.details || ""}`.trim();
}

function renderLogSnapshot() {
  const guidedRuntime = logFormats.runtime === "human";
  const guidedEvents = logFormats.events === "human";
  const runtimeEntries = latestLogs.runtime.filter(logMatches);
  const eventEntries = latestLogs.events.map((event) => eventText(event, guidedEvents)).filter(logMatches);
  $("runtime-log-view").classList.toggle("guided-log", guidedRuntime);
  $("event-log-view").classList.toggle("guided-log", guidedEvents);
  keepLogPosition($("runtime-log-view"), runtimeEntries.join(guidedRuntime ? "\n\n" : "\n") || "No matching runtime output.");
  keepLogPosition($("event-log-view"), eventEntries.join(guidedEvents ? "\n\n" : "\n") || "No matching events.");

  const allText = [...latestLogs.runtime, ...latestLogs.events.map((event) => JSON.stringify(event))];
  $("log-runtime-count").textContent = String(latestLogs.runtime.length);
  $("log-event-count").textContent = String(latestLogs.events.length);
  $("log-warning-count").textContent = String(allText.filter((line) => /warn/i.test(line)).length);
  $("log-error-count").textContent = String(allText.filter((line) => /error|failed|exception/i.test(line)).length);
}

async function refreshLogs(force = false) {
  if ($("chk-pause-logs").checked && !force) return;
  try {
    const [runtime, events] = await Promise.all([
      api(`/logs/runtime${logFormats.runtime === "human" ? "/human" : ""}?limit=500`, {}, true),
      api(`/logs/recent${logFormats.events === "human" ? "/human" : ""}?limit=200`),
    ]);
    const guidedEvents = logFormats.events === "human";
    latestLogs = { runtime: runtime.lines, events };
    renderLogSnapshot();
    $("runtime-log-state").textContent = runtime.available ? "Live" : "Unavailable";
    $("runtime-log-state").className = runtime.available ? "ok" : "bad";
    $("event-log-state").textContent = guidedEvents ? "Guided" : "Raw";
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
  experienceDirty = false;
}

function scheduleCameraRefresh(delayMs) {
  window.clearTimeout(cameraTimer);
  cameraTimer = window.setTimeout(refreshCamera, delayMs);
}

function showCameraImage(image, source) {
  return new Promise((resolve, reject) => {
    image.onload = () => resolve();
    image.onerror = () => reject(new Error("camera image could not be displayed"));
    image.src = source;
  });
}

async function refreshCamera() {
  if (cameraRequestInFlight) return;
  cameraRequestInFlight = true;
  try {
    const response = await fetch(`/camera/frame.jpg?t=${Date.now()}`, {
      cache: "no-store",
    });
    if (!response.ok) throw new Error(`camera returned ${response.status}`);
    const nextUrl = URL.createObjectURL(await response.blob());
    const image = $("admin-camera");
    const previousUrl = cameraObjectUrl;
    cameraObjectUrl = nextUrl;
    await showCameraImage(image, nextUrl);
    if (previousUrl) URL.revokeObjectURL(previousUrl);
    $("camera-state").textContent = "Live";
    $("camera-state").className = "status-pill ok";
    scheduleCameraRefresh(120);
  } catch (_) {
    if (cameraObjectUrl) {
      URL.revokeObjectURL(cameraObjectUrl);
      cameraObjectUrl = null;
    }
    $("admin-camera").removeAttribute("src");
    $("camera-state").textContent = "Unavailable";
    $("camera-state").className = "status-pill danger";
    scheduleCameraRefresh(1000);
  } finally {
    cameraRequestInFlight = false;
  }
}

function scheduleArducamRefresh(delayMs) {
  window.clearTimeout(arducamTimer);
  arducamTimer = window.setTimeout(refreshArducam, delayMs);
}

function renderArducamStatus(status) {
  const ready = Boolean(status.ready);
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
    ? "Camera disconnected."
    : (ready ? "Private live preview active. Frames are not stored." : "Opening the CSI camera.");
}

async function refreshArducamStatus() {
  if (!adminUnlocked || document.body.dataset.adminView !== "arducam") return;
  try {
    renderArducamStatus(await api("/api/admin/arducam/status", {}, true));
  } catch (error) {
    $("arducam-state").textContent = "Unavailable";
    $("arducam-state").className = "status-pill danger";
    $("arducam-detail").textContent = error.message;
  }
}

async function refreshArducam() {
  if (!adminUnlocked || document.body.dataset.adminView !== "arducam") {
    scheduleArducamRefresh(750);
    return;
  }
  if (arducamRequestInFlight) return;
  arducamRequestInFlight = true;
  try {
    const headers = authRequired ? { "X-Atlas-Admin-Token": token() } : {};
    const response = await fetch(`/api/admin/arducam/frame.jpg?t=${Date.now()}`, {
      cache: "no-store",
      headers,
    });
    if (!response.ok) {
      const message = response.status === 503
        ? "Camera disconnected."
        : `Preview unavailable (${response.status}).`;
      throw new Error(message);
    }
    const nextUrl = URL.createObjectURL(await response.blob());
    const image = $("admin-arducam");
    const previousUrl = arducamObjectUrl;
    arducamObjectUrl = nextUrl;
    await showCameraImage(image, nextUrl);
    if (previousUrl) URL.revokeObjectURL(previousUrl);
    $("arducam-state").textContent = "Live";
    $("arducam-state").className = "status-pill ok";
    scheduleArducamRefresh(120);
  } catch (error) {
    if (arducamObjectUrl) {
      URL.revokeObjectURL(arducamObjectUrl);
      arducamObjectUrl = null;
    }
    $("admin-arducam").removeAttribute("src");
    $("arducam-state").textContent = "Unavailable";
    $("arducam-state").className = "status-pill danger";
    $("arducam-detail").textContent = error.message;
    scheduleArducamRefresh(1000);
  } finally {
    arducamRequestInFlight = false;
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
  refreshStatus(), refreshHealth(), refreshLogs(true), refreshVisitorStatus(), refreshAudio(), refreshArducamStatus(),
]));
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
    refreshLogs(true);
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
$("btn-estop").addEventListener("click", () => api("/hardware/emergency-stop", { method: "POST" }).then(() => Promise.all([refreshStatus(), refreshHealth()])));
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
    `Captured: ${new Date().toISOString()}`,
    "",
    "RUNTIME",
    ...latestLogs.runtime,
    "",
    "EVENTS",
    ...latestLogs.events.map((event) => JSON.stringify(event, null, 2)),
  ].join("\n");
  const url = URL.createObjectURL(new Blob([snapshot], { type: "text/plain;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `atlas-logs-${new Date().toISOString().replaceAll(":", "-")}.txt`;
  link.click();
  URL.revokeObjectURL(url);
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
  const access = await api("/admin/access");
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
