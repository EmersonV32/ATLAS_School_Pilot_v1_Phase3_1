/* ATLAS visitor dashboard. No build step and no external dependencies. */
"use strict";

const $ = (id) => document.getElementById(id);
let currentLanguage = "en";
let cameraTimer = null;

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  const response = await fetch(path, { ...options, headers });
  let body = null;
  try { body = await response.json(); } catch (_) { /* no response body */ }
  if (!response.ok) {
    const detail = body && body.detail ? body.detail : response.statusText;
    throw new Error(String(detail));
  }
  return body;
}

function showNotice(message, bad = false) {
  const notice = $("notice");
  notice.textContent = message;
  notice.classList.toggle("bad", bad);
  notice.classList.remove("hidden");
  window.clearTimeout(showNotice.timer);
  showNotice.timer = window.setTimeout(() => notice.classList.add("hidden"), 4500);
}

function setLanguage(language) {
  currentLanguage = language;
  document.querySelectorAll("[data-language]").forEach((button) => {
    const selected = button.dataset.language === language;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
}

async function applyExperience() {
  await api("/session/profile", {
    method: "POST",
    body: JSON.stringify({
      language: currentLanguage,
      profile: $("sel-profile").value,
      accessibility_mode: $("chk-accessibility").checked,
    }),
  });
}

async function refreshStatus() {
  try {
    const status = await api("/status");
    const badge = $("connection-badge");
    badge.textContent = status.emergency_stopped
      ? "Emergency stop"
      : status.session_active ? "Session active" : "Ready";
    badge.className = `status-pill ${status.emergency_stopped ? "danger" : "ok"}`;

    $("session-label").textContent = status.session_active
      ? `Session ${status.session_id.slice(0, 8)}`
      : "No active session";
    $("btn-start").disabled = status.session_active;
    $("btn-stop").disabled = !status.session_active;

    const experience = status.experience || {};
    setLanguage(experience.language || currentLanguage);
    $("sel-profile").value = experience.profile || "adult_beginner";
    $("chk-accessibility").checked = Boolean(experience.accessibility_mode);

    const artwork = status.artwork || {};
    $("art-title").textContent = artwork.label || "Waiting for an artwork";
    $("art-state").textContent = artwork.artwork_id
      ? `${artwork.stable ? "Focused" : "Detecting"} - ${artwork.source}`
      : "No detection";
    const confidence = artwork.confidence == null ? 0 : artwork.confidence;
    $("art-confidence").textContent = artwork.confidence == null
      ? "--"
      : `${Math.round(confidence * 100)}%`;
    $("confidence-fill").style.width = `${Math.round(confidence * 100)}%`;

    if (status.last_answer) {
      $("answer-text").textContent = status.last_answer.answer;
      $("answer-detail").textContent = status.last_answer.fallback_used
        ? "Offline or safety fallback"
        : status.last_answer.grounded ? "Grounded in museum content" : "General response";
      $("latency-label").textContent = status.last_answer.latency_ms == null
        ? "--"
        : `${Math.round(status.last_answer.latency_ms)} ms`;
    }
  } catch (_) {
    const badge = $("connection-badge");
    badge.textContent = "Offline";
    badge.className = "status-pill danger";
  }
}

document.querySelectorAll("[data-language]").forEach((button) => {
  button.addEventListener("click", async () => {
    setLanguage(button.dataset.language);
    try { await applyExperience(); } catch (error) { showNotice(error.message, true); }
  });
});

$("sel-profile").addEventListener("change", () => {
  applyExperience().catch((error) => showNotice(error.message, true));
});
$("chk-accessibility").addEventListener("change", () => {
  applyExperience().catch((error) => showNotice(error.message, true));
});

$("btn-start").addEventListener("click", async () => {
  try {
    await applyExperience();
    await api("/session/start", { method: "POST" });
    await refreshStatus();
  } catch (error) { showNotice(error.message, true); }
});

$("btn-stop").addEventListener("click", async () => {
  try {
    await api("/session/stop", { method: "POST" });
    await refreshStatus();
  } catch (error) { showNotice(error.message, true); }
});

$("btn-capture").addEventListener("click", async () => {
  const button = $("btn-capture");
  button.disabled = true;
  button.textContent = "Capturing";
  try {
    const result = await api("/session/capture", { method: "POST" });
    showNotice(result.requested ? "Capture requested" : `Identified ${result.label}`);
    await refreshStatus();
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = "Capture artwork";
  }
});

$("btn-clear-artwork").addEventListener("click", async () => {
  try {
    await api("/session/manual-artwork", { method: "DELETE" });
    await refreshStatus();
  } catch (error) { showNotice(error.message, true); }
});

async function ask() {
  const input = $("inp-question");
  const question = input.value.trim();
  if (!question) return;
  const button = $("btn-ask");
  button.disabled = true;
  $("answer-text").textContent = "Thinking...";
  $("answer-detail").textContent = "";
  try {
    const result = await api("/ask", {
      method: "POST",
      body: JSON.stringify({
        question,
        language: currentLanguage,
        profile: $("sel-profile").value,
      }),
    });
    $("answer-text").textContent = result.answer;
    $("answer-detail").textContent = result.fallback_used
      ? "Offline or safety fallback"
      : result.grounded ? "Grounded in museum content" : "General response";
    $("latency-label").textContent = result.total_latency_ms == null
      ? "--"
      : `${Math.round(result.total_latency_ms)} ms`;
    input.value = "";
  } catch (error) {
    $("answer-text").textContent = "ATLAS could not answer right now.";
    showNotice(error.message, true);
  } finally {
    button.disabled = false;
    refreshStatus();
  }
}

function refreshCamera() {
  window.clearTimeout(cameraTimer);
  $("camera-feed").src = `/camera/frame.jpg?t=${Date.now()}`;
}

$("camera-feed").addEventListener("load", () => {
  $("camera-state").textContent = "Live";
  cameraTimer = window.setTimeout(refreshCamera, 125);
});
$("camera-feed").addEventListener("error", () => {
  $("camera-state").textContent = "Camera unavailable";
  cameraTimer = window.setTimeout(refreshCamera, 1000);
});

$("btn-ask").addEventListener("click", ask);
$("inp-question").addEventListener("keydown", (event) => {
  if (event.key === "Enter") ask();
});

setLanguage("en");
refreshStatus();
refreshCamera();
window.setInterval(refreshStatus, 2500);
