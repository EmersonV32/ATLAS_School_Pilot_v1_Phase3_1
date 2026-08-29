/* ATLAS teacher dashboard — vanilla JS, no build step. */
"use strict";

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = $("inp-token").value.trim();
  if (token) headers["X-Atlas-Admin-Token"] = token;
  const res = await fetch(path, { headers, ...options });
  let body = null;
  try { body = await res.json(); } catch (_) { /* empty body */ }
  if (!res.ok) {
    const detail = body && body.detail ? body.detail : res.statusText;
    throw new Error(`${res.status}: ${JSON.stringify(detail)}`);
  }
  return body;
}

function showAdminResult(data) {
  const box = $("admin-result");
  box.classList.remove("hidden");
  box.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

/* ---- status refresh ---- */
async function refreshStatus() {
  try {
    const s = await api("/status");
    $("mode-badge").textContent = `mode: ${s.mode}`;
    $("state-badge").textContent = s.session_active ? "state: session active" : "state: idle";
    $("session-id").textContent = s.session_id || "no session";
    $("estop-badge").classList.toggle("hidden", !s.emergency_stopped);

    const art = s.artwork || {};
    $("art-label").textContent = art.label || "—";
    $("art-conf").textContent = art.confidence != null ? `${Math.round(art.confidence * 100)}%` : "—";
    $("art-stable").textContent = art.artwork_id ? (art.stable ? "stable" : "unstable") : "—";
    $("art-source").textContent = art.source || "—";
    const warning = $("art-warning");
    if (art.warning) { warning.textContent = art.warning; warning.classList.remove("hidden"); }
    else warning.classList.add("hidden");

    const last = s.last_answer;
    $("last-answer").textContent = last ? last.answer : "—";
    $("last-fallback").textContent = last ? String(last.fallback_used) : "—";
    $("last-latency").textContent = last && last.latency_ms != null ? `${Math.round(last.latency_ms)} ms` : "—";

    $("transcript-state").textContent = s.privacy.transcript_logging ? "ON" : "off";
    const privacyRows = [
      ["Raw audio storage", s.privacy.store_raw_audio ? "ON" : "off (safe)", !s.privacy.store_raw_audio],
      ["Raw image storage", s.privacy.store_raw_images ? "ON" : "off (safe)", !s.privacy.store_raw_images],
      ["Face recognition", s.privacy.store_face_data ? "ON" : "disabled (safe)", !s.privacy.store_face_data],
      ["Anonymous session IDs", s.privacy.anonymous_session_ids ? "on (safe)" : "OFF", s.privacy.anonymous_session_ids],
      ["Cloud LLM", s.privacy.cloud_llm_enabled ? `enabled (${s.privacy.cloud_llm_provider})` : "disabled — mock/local only", true],
    ];
    $("privacy-list").innerHTML = privacyRows
      .map(([k, v, ok]) => `<li><span>${k}</span><span class="${ok ? "ok" : "bad"}">${v}</span></li>`)
      .join("");
  } catch (err) {
    $("state-badge").textContent = "state: unreachable";
  }
}

async function refreshHealth() {
  try {
    const h = await api("/health");
    const rows = Object.entries(h.components).map(
      ([k, v]) =>
        `<li><span>${k}</span><span class="${String(v).startsWith("error") ? "bad" : "ok"}">${v}</span></li>`
    );
    rows.push(
      `<li><span>emergency stop</span><span class="${h.emergency_stopped ? "bad" : "ok"}">${h.emergency_stopped ? "ACTIVE" : "clear"}</span></li>`
    );
    $("health-list").innerHTML = rows.join("");
  } catch (err) {
    $("health-list").innerHTML = `<li><span>dashboard</span><span class="bad">${err.message}</span></li>`;
  }
}

async function refreshPacksAndArtworks() {
  try {
    const packs = await api("/content/packs");
    $("sel-pack").innerHTML = packs
      .map((p) => `<option value="${p.pack_id}" ${p.selected ? "selected" : ""}>${p.name}</option>`)
      .join("");
    const artworks = await api("/artworks");
    $("sel-artwork").innerHTML = artworks
      .map((a) => `<option value="${a.artwork_id}">${a.title}</option>`)
      .join("");
  } catch (err) { /* leave dropdowns empty */ }
}

async function refreshLogs() {
  try {
    const logs = await api("/logs/recent?limit=30");
    $("log-view").textContent = logs.length
      ? logs.map((l) => JSON.stringify(l)).join("\n")
      : "(no logs yet)";
  } catch (err) {
    $("log-view").textContent = err.message;
  }
}

/* ---- wire up controls ---- */
$("btn-start").onclick = () => api("/session/start", { method: "POST" }).then(refreshStatus);
$("btn-stop").onclick = () => api("/session/stop", { method: "POST" }).then(refreshStatus);

$("btn-apply-experience").onclick = () =>
  api("/session/profile", {
    method: "POST",
    body: JSON.stringify({
      language: $("sel-language").value,
      profile: $("sel-profile").value,
      pack_id: $("sel-pack").value,
      accessibility_mode: $("chk-accessibility").checked,
    }),
  }).then(() => { refreshStatus(); refreshPacksAndArtworks(); });

$("btn-override").onclick = () =>
  api("/session/manual-artwork", {
    method: "POST",
    body: JSON.stringify({ artwork_id: $("sel-artwork").value }),
  }).then(refreshStatus).catch((e) => showAdminResult(e.message));

$("btn-clear-override").onclick = () =>
  api("/session/manual-artwork", { method: "DELETE" }).then(refreshStatus);

$("btn-ask").onclick = async () => {
  const question = $("inp-question").value.trim();
  if (!question) return;
  $("answer-box").classList.remove("hidden");
  $("answer-text").textContent = "…";
  $("answer-meta").textContent = "";
  try {
    const r = await api("/ask", { method: "POST", body: JSON.stringify({ question }) });
    $("answer-text").textContent = r.answer;
    $("answer-meta").textContent =
      `grounded=${r.grounded}  fallback=${r.fallback_used}  confidence=${r.confidence}` +
      (r.total_latency_ms != null ? `  ${Math.round(r.total_latency_ms)} ms` : "");
  } catch (err) {
    $("answer-text").textContent = `Error: ${err.message}`;
  }
  refreshStatus();
  refreshLogs();
};
$("inp-question").addEventListener("keydown", (e) => {
  if (e.key === "Enter") $("btn-ask").click();
});

document.querySelectorAll("#demo-buttons button").forEach((btn) => {
  btn.onclick = () =>
    api("/demo/simulate", {
      method: "POST",
      body: JSON.stringify({ scenario: btn.dataset.sim }),
    }).then((r) => { showAdminResult(r); refreshStatus(); })
      .catch((e) => showAdminResult(e.message));
});

$("btn-ingest").onclick = () =>
  api("/content/ingest", {
    method: "POST",
    body: JSON.stringify({ pack_id: $("sel-pack").value, reset: true }),
  }).then(showAdminResult).catch((e) => showAdminResult(e.message));

$("btn-eval").onclick = () =>
  api("/eval/rag", { method: "POST" })
    .then(showAdminResult).catch((e) => showAdminResult(e.message));

$("btn-estop").onclick = () =>
  api("/hardware/emergency-stop", { method: "POST" }).then(() => { refreshStatus(); refreshHealth(); });

$("btn-clear-estop").onclick = () =>
  api("/hardware/clear-emergency-stop", { method: "POST" })
    .then(() => { refreshStatus(); refreshHealth(); })
    .catch((e) => showAdminResult(e.message));

$("btn-refresh-logs").onclick = refreshLogs;

/* ---- boot ---- */
refreshStatus();
refreshHealth();
refreshPacksAndArtworks();
refreshLogs();
setInterval(refreshStatus, 5000);
setInterval(refreshHealth, 15000);
