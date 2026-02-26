
function showMsg(t) {
  document.getElementById("msg").textContent = t || "";
}

let __cfgCache = {};
const pageLoadTs = Date.now() / 1000;
let lastAIShown = false;


async function fetchJson(url, opts) {
  const r = await fetch(url, opts || {});
  let j = null;
  try { j = await r.json(); } catch(e) {}
  return {status: r.status, json: j};
}

async function refreshConfigForm() {
  const cfg = await fetchJson("/api/config");
  if (cfg.json) {
    document.getElementById("stream_fps").value = cfg.json.stream_fps;
    document.getElementById("jpeg_quality").value = cfg.json.jpeg_quality;
    document.getElementById("record_fps").value = cfg.json.record_fps;
    document.getElementById("segment_seconds").value = cfg.json.segment_seconds;
    document.getElementById("out_root").value = cfg.json.out_root;
    document.getElementById("cam_name").value = cfg.json.cam_name;
    document.getElementById("codec").value = cfg.json.codec;
    document.getElementById("autosave").value = cfg.json.autosave ? "true" : "false";
    __cfgCache = cfg.json || {};
  }

  const setVal = (id, v) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (el.type === "checkbox") el.checked = !!v;
    else el.value = (v ?? "");
  };

  setVal("ai_enabled", cfg.json.ai_enabled);
  setVal("ark_model", cfg.json.ark_model);
  setVal("ark_api_key", cfg.json.ark_api_key);
  setVal("ai_interval_observe", cfg.json.ai_interval_observe);
  setVal("ai_dwell_threshold_sec", cfg.json.ai_dwell_threshold_sec);
  setVal("ai_end_grace_sec", cfg.json.ai_end_grace_sec);
  setVal("motion_ratio_threshold", cfg.json.motion_ratio_threshold);
  setVal("motion_min_interval", cfg.json.motion_min_interval);
  setVal("ai_jpeg_quality", cfg.json.ai_jpeg_quality);
  setVal("ai_prompt_template", cfg.json.ai_prompt_template);
  setVal("ai_scene_profile", cfg.json.ai_scene_profile);
  setVal("ai_session_focus", cfg.json.ai_session_focus);
  setVal("ai_prompt_extra", cfg.json.ai_prompt_extra);

  syncAiUi();
}

function syncAiUi() {
  const btn = document.getElementById("aiToggleBtn");
  const cb = document.getElementById("ai_enabled");
  const panel = document.getElementById("aiPanel");
  if (!btn || !cb || !panel) return;

  const on = !!cb.checked;
  panel.style.display = on ? "" : "none";
  btn.textContent = on ? "Disable" : "Enable";
  btn.classList.remove("primary");
  btn.classList.remove("danger");

  if (on) {
    btn.classList.add("danger");
  } else {
    btn.classList.add("primary");
  }
}

function _secToHMS(sec){
  if (sec === null || sec === undefined) return "—";
  const s = Math.max(0, Math.floor(Number(sec)));
  const h = Math.floor(s/3600);
  const m = Math.floor((s%3600)/60);
  const r = s%60;
  if (h > 0) return `${h}h ${m}m ${r}s`;
  if (m > 0) return `${m}m ${r}s`;
  return `${r}s`;
}

function _pill(text, cls){
  return `<span class="pill ${cls}">${text}</span>`;
}

async function refreshStatusOnly() {
  const st = await fetchJson("/api/status");
  if (!st.json) return;
  const box = document.getElementById("status_readable");
  if (!box) return;
  const ingestOn = !!st.json.ingest_enabled;
  const recOn = !!st.json.recording;
  const ingestP = ingestOn ? _pill("ON", "ok") : _pill("OFF", "warn");
  const recP = recOn ? _pill("ON", "ok") : _pill("OFF", "warn");
  const lastAge = (st.json.last_frame_age_sec === null || st.json.last_frame_age_sec === undefined)
    ? "—"
    : `${st.json.last_frame_age_sec}s`;
  const uploadFps = (st.json.upload_fps === null || st.json.upload_fps === undefined)
    ? "—"
    : String(st.json.upload_fps);

  const recFile = st.json.recording_file || "—";
  const recElapsed = _secToHMS(st.json.recording_elapsed_sec);
  const segRemain = _secToHMS(st.json.segment_remaining_sec);
  const counts = st.json.upload_counts || {};
  const c200 = counts["200_ok"] ?? 0;
  const cMiss = counts["400_missing_image"] ?? 0;
  const cDec = counts["400_decode_failed"] ?? 0;
  const c503 = counts["503_ingest_disabled"] ?? 0;

  box.innerHTML = `
    <div class="status-grid">
      <div class="status-item"><span class="status-k">Ingest</span><div class="status-v">${ingestP}</div></div>
      <div class="status-item"><span class="status-k">Recording</span><div class="status-v">${recP}</div></div>

      <div class="status-item"><span class="status-k">Last frame age</span><div class="status-v">${lastAge}</div></div>
      <div class="status-item"><span class="status-k">Upload FPS</span><div class="status-v">${uploadFps}</div></div>

      <div class="status-item"><span class="status-k">Stream FPS / JPEG</span><div class="status-v">${st.json.stream_fps} / ${st.json.jpeg_quality}</div></div>
      <div class="status-item"><span class="status-k">Record FPS / Segment</span><div class="status-v">${st.json.record_fps} / ${st.json.segment_seconds}s</div></div>

      <div class="status-item"><span class="status-k">Output Root</span><div class="status-v">${st.json.out_root || "—"}</div></div>
      <div class="status-item"><span class="status-k">Cam / Codec</span><div class="status-v">${st.json.cam_name || "—"} / ${st.json.codec || "—"}</div></div>

      <div class="status-item" style="grid-column:1/-1;"><span class="status-k">Recording file</span><div class="status-v" style="font-weight:600;">${recFile}</div></div>
      <div class="status-item"><span class="status-k">Rec elapsed</span><div class="status-v">${recElapsed}</div></div>
      <div class="status-item"><span class="status-k">Seg remaining</span><div class="status-v">${segRemain}</div></div>

      <div class="status-item" style="grid-column:1/-1;">
        <span class="status-k">Upload counts</span>
        <div class="status-v" style="font-weight:600;">
          200_ok=${c200} | missing=${cMiss} | decode_failed=${cDec} | ingest_disabled=${c503}
        </div>
      </div>
    </div>
  `;
}

function _fmtAbs(tsSec){
  if (!tsSec || tsSec <= 0) return "—";
  const d = new Date(tsSec * 1000);
  const pad = (n)=> String(n).padStart(2,"0");
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}
function _fmtAgo(tsSec){
  if (!tsSec || tsSec <= 0) return "";
  const s = Math.max(0, Math.floor(Date.now()/1000 - tsSec));
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s/60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m/60);
  return `${h}h ago`;
}
function _clip(s, n){
  s = String(s ?? "");
  return s.length > n ? (s.slice(0, n) + "…") : s;
}

async function refreshAI() {
  const r = await fetchJson("/api/ai/status");
  const rawPre = document.getElementById("ai_status_raw");
  const badge = document.getElementById("aiStateBadge");
  const elEvent = document.getElementById("aiEventId");
  const elDwell = document.getElementById("aiDwell");
  const elHealth = document.getElementById("aiHealth");
  const elLastLine = document.getElementById("aiLastLine");
  const elLastSummary = document.getElementById("aiLastSummary");
  const elTimes = document.getElementById("aiTimes");
  const elMetrics = document.getElementById("aiMetrics");

  if (!(r.json && r.json.ok)) {
    const errObj = r.json || {error: r.status};
    if (rawPre) rawPre.textContent = JSON.stringify(errObj, null, 2);
    if (badge) { badge.textContent = "STATE: ?"; badge.classList.remove("ok","warn","err"); }
    if (elHealth) elHealth.textContent = "Health: ERROR";
    return;
  }

  const data = r.json.data || {};
  if (rawPre) rawPre.textContent = JSON.stringify(data, null, 2);

  const state = String(data.state || "?");
  const eventId = data.event_id || "—";
  const dwell = !!data.dwell_confirmed;
  const lastErr = String(data.last_ai_error || "").trim();
  const lastAiCall = Number(data.last_ai_call_ts || 0);
  const observeInterval = Number(__cfgCache.ai_interval_observe || 5);
  const delayedThreshold = 2 * observeInterval + 1; // per our rule

  let healthText = "Fine";
  let healthClass = "ok";
  if (lastErr) {
    healthText = "ERROR";
    healthClass = "err";
  } else if (state === "OBSERVE" && lastAiCall > 0) {
    const dt = (Date.now()/1000) - lastAiCall;
    if (dt > delayedThreshold) {
      healthText = "AI call delayed";
      healthClass = "warn";
    }
  }
  if (badge) {
    badge.textContent = `STATE: ${state}`;
    badge.classList.remove("ok","warn","err");
    badge.classList.add(healthClass);
  }
  if (elEvent) elEvent.textContent = `Event: ${eventId}`;
  if (elDwell) elDwell.textContent = `Dwell: ${dwell ? "Yes" : "No"}`;
  if (elHealth) elHealth.textContent = `Health: ${healthText}${lastErr ? " (see Raw JSON)" : ""}`;

  const last = data.last_ai_json || null;
  if (!last) {
  } else {
    const ev = {
      kind: "ai_frame",
      ts: Number(data.last_ai_call_ts || 0) || (Date.now() / 1000),
      time_text: "",            // 可选：留空则用 ts 渲染
      ai: last
    };
    _updateLastAIFromEvent(ev);
  }


  const tTrig = Number(data.last_trigger_ts || 0);
  const tStart = Number(data.event_start_ts || 0);
  const lines = [];
  lines.push(`Last trigger: ${_fmtAbs(tTrig)}${tTrig ? ` (${_fmtAgo(tTrig)})` : ""}`);
  lines.push(`Last AI call: ${_fmtAbs(lastAiCall)}${lastAiCall ? ` (${_fmtAgo(lastAiCall)})` : ""}`);
  lines.push(`Event start:  ${_fmtAbs(tStart)}${tStart ? ` (${_fmtAgo(tStart)})` : ""}`);
  if (elTimes) elTimes.textContent = lines.join("\n");
  const acc = Number(data.person_present_acc_sec || 0);
  const accTxt = `${acc.toFixed(1)} s`;

  let durTxt = "—";
  if (tStart > 0) {
    const dur = Math.max(0, (Date.now()/1000) - tStart);
    durTxt = `${dur.toFixed(1)} s`;
  }
  if (elMetrics) {
    elMetrics.textContent =
      `Person present (acc): ${accTxt}\nEvent duration:      ${durTxt}`;
  }
}


function _eventTimeText(ev){
  if (ev && ev.time_text) return String(ev.time_text);
  const ts = Number(ev?.ts || 0);
  return ts > 0 ? _fmtAbs(ts) : "—";
}

function _renderHistoryItemAiFrame(ev){
  const ai = ev.ai || {};
  const hasPerson = !!ai.has_person;
  const count = (ai.person_count === null || ai.person_count === undefined) ? "—" : String(ai.person_count);
  const activity = String(ai.activity || "unknown");
  const risk = String(ai.risk_level || "info");
  const riskNorm = (risk === "warn" || risk === "critical" || risk === "info") ? risk : "info";
  const riskClass = `risk-${riskNorm}`;
  const conf = Math.round(Math.max(0, Math.min(1, Number(ai.confidence || 0))) * 100);
  const summary = _clip(ai.summary || "", 300);

  return `
    <div class="ai-hitem">
      <div class="ai-hrow">
        <span class="ai-htime">${_eventTimeText(ev)}</span>
        <span class="ai-htag">AI</span>
        <span class="ai-htag ${riskClass}">${riskNorm}</span>
      </div>
      <div class="ai-hmeta">Person: ${hasPerson ? "Yes" : "No"} | Count: ${count} | Activity: ${activity} | Risk: ${risk} | Conf: ${conf}%</div>
      ${summary ? `<div class="ai-hsummary">Summary: ${summary}</div>` : ``}
    </div>
  `;
}

function _updateLastAIFromEvent(ev) {
  const elLastLine = document.getElementById("aiLastLine");
  const elLastSummary = document.getElementById("aiLastSummary");

  if (!ev || ev.kind !== "ai_frame") {
    lastAIShown = false;
    if (elLastLine) elLastLine.textContent = "No AI result yet (waiting…)";
    if (elLastSummary) elLastSummary.textContent = "";
    return;
  }

  const evTs = Number(ev.ts || 0);
  if (!lastAIShown && evTs && evTs < pageLoadTs) {
    lastAIShown = false;
    if (elLastLine) elLastLine.textContent = "No AI result yet (waiting…)";
    if (elLastSummary) elLastSummary.textContent = "";
    return;
  }

  lastAIShown = true;

  const ai = ev.ai || {};
  const hasPerson = !!ai.has_person;
  const count = (ai.person_count === null || ai.person_count === undefined) ? "—" : String(ai.person_count);
  const activity = String(ai.activity || "unknown");
  const risk = String(ai.risk_level || "info");
  const conf = Math.round(Math.max(0, Math.min(1, Number(ai.confidence || 0))) * 100);
  const summary = _clip(ai.summary || "", 300);

  if (elLastLine) elLastLine.textContent =
    `Person: ${hasPerson ? "Yes" : "No"} | Count: ${count} | Activity: ${activity} | Risk: ${risk} | Conf: ${conf}%`;
  if (elLastSummary) {
    elLastSummary.innerHTML = summary ? `<div class="ai-hsummary">Summary: ${summary}</div>` : "";
  }
}



function _renderHistoryItemAiError(ev){
  const err = _clip(ev.error || "unknown error", 160);
  return `
    <div class="ai-hitem">
      <div class="ai-hrow">
        <span class="ai-htime">${_eventTimeText(ev)}</span>
        <span class="ai-htag err">AI ERROR</span>
      </div>
      <div class="ai-hsummary">${err}</div>
    </div>
  `;
}

async function refreshAIEvents() {
  const list = document.getElementById("aiHistoryList");
  if (!list) return;
  const r = await fetchJson("/api/ai/events?n=200");
  if (!(r.json && r.json.ok)) {
    list.innerHTML = `<div class="hint">failed to load: ${_clip(JSON.stringify(r.json || {error: r.status}), 200)}</div>`;
    _updateLastAIFromEvent(null);
    return;
  }

  const arr = Array.isArray(r.json.data) ? r.json.data : [];
  const filtered = arr.filter(ev => ev && (ev.kind === "ai_frame" || ev.kind === "ai_error"));
  filtered.sort((a, b) => Number(b.ts || 0) - Number(a.ts || 0));

  const top20 = filtered.slice(0, 20);
  if (top20.length === 0) {
    list.innerHTML = `<div class="hint">no history yet.</div>`;
    _updateLastAIFromEvent(null);
    return;
  }

  const newestFrame = top20.find(ev => ev && ev.kind === "ai_frame") || null;
  _updateLastAIFromEvent(newestFrame);
  const shouldSkipNewest = !!(lastAIShown && newestFrame);
  let skippedNewest = false;

  const html = top20.map(ev => {
    if (!ev) return "";
    if (shouldSkipNewest && !skippedNewest && ev === newestFrame) {
      skippedNewest = true;
      return "";
    }
    if (ev.kind === "ai_error") return _renderHistoryItemAiError(ev);
    return _renderHistoryItemAiFrame(ev);
  }).join("");
  list.innerHTML = html;
}

function refreshAIIfEnabled() {
  if (!isAiEnabledUi()) return;
  refreshAI();
}

function refreshAIEventsIfEnabled() {
  if (!isAiEnabledUi()) return;
  refreshAIEvents();
}

async function refreshLogTail() {
  const n = 50; // 只取近 50 条
  const r = await fetchJson("/api/log/tail?n=" + n);
  const pre = document.getElementById("log_tail");
  if (!pre) return;
  if (r.json && r.json.ok) {
    const lines = (r.json.data || []);
    pre.textContent = lines.slice().reverse().join("\n");
  } else {
    pre.textContent = JSON.stringify(r.json || {error: r.status}, null, 2);
  }
}

function isAiEnabledUi() {
  const cb = document.getElementById("ai_enabled");
  return !!(cb && cb.checked);
}

function toggleAiEnabled() {
  const cb = document.getElementById("ai_enabled");
  if (!cb) return;
  cb.checked = !cb.checked;
  syncAiUi();
}

let ingestOn = false;
let recordingOn = false;

function syncIngestBtn() {
  const btn = document.getElementById("ingestToggleBtn");
  if (!btn) return;
  btn.textContent = ingestOn ? "Disable Ingest" : "Enable Ingest";
  btn.classList.remove("primary", "danger");
  btn.classList.add(ingestOn ? "danger" : "primary");
}

async function toggleIngest() {
  if (ingestOn) {
    await disableIngest();
  } else {
    await enableIngest();
  }
  ingestOn = !ingestOn;
  syncIngestBtn();
}

function syncRecordBtn() {
  const btn = document.getElementById("recordToggleBtn");
  if (!btn) return;
  btn.textContent = recordingOn ? "Stop Recording" : "Start Recording";
  btn.classList.remove("primary", "danger");
  btn.classList.add(recordingOn ? "danger" : "primary");
}

async function toggleRecording() {
  if (recordingOn) {
    await stopRec();
  } else {
    await startRec();
  }

  recordingOn = !recordingOn;
  syncRecordBtn();
}

async function snapshot() {
  const r = await fetchJson("/api/snapshot", {method:"POST"});
  if (r.status === 200 && r.json && r.json.ok) {
    showMsg("Snapshot saved: " + r.json.path);
  } else {
    showMsg("Snapshot failed: " + (r.json && r.json.error ? r.json.error : r.status));
  }
}

async function shutdownSystem(){
  const ok = confirm("Shutdown the system now?\n\nIt will:\n(1) Stop recording\n(2) Disable ingest\n(3) Stop the Python server");
  if(!ok) return;

  try { await fetch("/api/record/stop", {method:"POST"}); } catch(e) {}
  try { await fetch("/api/ingest/disable", {method:"POST"}); } catch(e) {}
  try { await fetch("/api/system/shutdown", {method:"POST"}); } catch(e) {}

  setTimeout(() => {
    try { window.open("", "_self"); } catch(e) {}
    try { window.close(); } catch(e) {}
    window.location.href = "about:blank";
  }, 150);
}


async function applyConfig() {
  showMsg("");
  const payload = {
    stream_fps: parseInt(document.getElementById("stream_fps").value),
    jpeg_quality: parseInt(document.getElementById("jpeg_quality").value),
    record_fps: parseInt(document.getElementById("record_fps").value),
    segment_seconds: parseInt(document.getElementById("segment_seconds").value),
    out_root: document.getElementById("out_root").value,
    cam_name: document.getElementById("cam_name").value,
    codec: document.getElementById("codec").value,
    autosave: document.getElementById("autosave").value === "true",

    ai_enabled: !!document.getElementById("ai_enabled")?.checked,
    ark_model: document.getElementById("ark_model")?.value || "",
    ark_api_key: document.getElementById("ark_api_key")?.value || "",

    ai_interval_observe: parseFloat(document.getElementById("ai_interval_observe")?.value || "5"),
    ai_dwell_threshold_sec: parseFloat(document.getElementById("ai_dwell_threshold_sec")?.value || "5"),
    ai_end_grace_sec: parseFloat(document.getElementById("ai_end_grace_sec")?.value || "3"),

    motion_ratio_threshold: parseFloat(document.getElementById("motion_ratio_threshold")?.value || "0.02"),
    motion_min_interval: parseFloat(document.getElementById("motion_min_interval")?.value || "1.0"),

    ai_jpeg_quality: parseInt(document.getElementById("ai_jpeg_quality")?.value || "85"),

    ai_prompt_template: document.getElementById("ai_prompt_template")?.value || "",
    ai_scene_profile: document.getElementById("ai_scene_profile")?.value || "",
    ai_session_focus: document.getElementById("ai_session_focus")?.value || "",
    ai_prompt_extra: document.getElementById("ai_prompt_extra")?.value || ""
  };

  const r = await fetchJson("/api/config", {
    method: "PUT",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  if (r.status !== 200) {
    showMsg("Apply failed: " + (r.json && r.json.error ? r.json.error : r.status));
  } else {
    showMsg("Applied.");
    if (r.json && r.json.note) showMsg(r.json.note);
  }

  await refreshConfigForm();
  await refreshStatusOnly();
}

async function saveConfig() {
  const r = await fetchJson("/api/config/save", {method:"POST"});
  showMsg(r.status === 200 ? "Saved to config.json" : "Save failed");
}

async function loadConfig() {
  const r = await fetchJson("/api/config/load", {method:"POST"});
  showMsg(r.status === 200 ? "Loaded from config.json" : "Load failed");
  await refreshConfigForm();
  await refreshStatusOnly();
}

async function enableIngest() {
  await fetchJson("/api/ingest/enable", {method:"POST"});
  await refreshStatusOnly();
}
async function disableIngest() {
  await fetchJson("/api/ingest/disable", {method:"POST"});
  await refreshStatusOnly();
}
async function startRec() {
  const r = await fetchJson("/api/record/start", {method:"POST"});
  if (r.json && r.json.note) showMsg(r.json.note);
  await refreshStatusOnly();
}
async function stopRec() {
  await fetchJson("/api/record/stop", {method:"POST"});
  await refreshStatusOnly();
}

setInterval(refreshStatusOnly, 1000);
setInterval(() => {
  if (isAiEnabledUi()) refreshAI();
}, 1000);
setInterval(() => {
  if (isAiEnabledUi()) refreshAIEvents();
}, 2000);
setInterval(refreshLogTail, 2000);

(function initSplitter(){
  const layout = document.querySelector(".layout");
  const right = document.getElementById("rightPane");
  const splitter = document.getElementById("splitter");
  if (!layout || !right || !splitter) return;

  let dragging = false;

  function setRightW(px){
    right.style.width = px + "px";
    right.style.flex = `0 0 ${px}px`;
    try { localStorage.setItem("rightPaneWidth", String(px)); } catch(e){}
  }

  try {
    const saved = parseInt(localStorage.getItem("rightPaneWidth") || "", 10);
    if (!Number.isNaN(saved) && saved > 0) setRightW(saved);
  } catch(e){}

  splitter.addEventListener("mousedown", (e) => {
    if (right.classList.contains("collapsed")) return; // 折叠时不允许拖
    dragging = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    e.preventDefault();
  });

  window.addEventListener("mousemove", (e) => {
    if (!dragging) return;

    const rect = layout.getBoundingClientRect();
    const splitW = splitter.getBoundingClientRect().width || 10;
    const x = e.clientX - rect.left;

    let w = rect.width - x - splitW;

    const minW = 280;
    const maxW = Math.floor(rect.width * 0.65);
    w = Math.max(minW, Math.min(maxW, w));

    setRightW(w);
  });

  window.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  });
})();


function toggleSettings(forceState) {
  const layout = document.querySelector(".layout");
  const right = document.getElementById("rightPane");
  const splitter = document.getElementById("splitter");
  const btn = document.getElementById("toggleSettingsBtn");

  const collapsed = (forceState !== undefined)
    ? forceState
    : !right.classList.contains("collapsed");

  if (collapsed) {
    right.classList.add("collapsed");
    splitter.classList.add("collapsed");
    layout.classList.add("collapsed");

    if (btn) btn.textContent = "Expand";
    if (!document.getElementById("floatingExpandBtn")) {
      const fb = document.createElement("button");
      fb.id = "floatingExpandBtn";
      fb.className = "floating-toggle";
      fb.textContent = "Expand Settings";
      fb.onclick = () => toggleSettings(false);
      document.body.appendChild(fb);
    }

    try { localStorage.setItem("settingsCollapsed", "true"); } catch(e){}
  } else {
    right.classList.remove("collapsed");
    splitter.classList.remove("collapsed");
    layout.classList.remove("collapsed");

    if (btn) btn.textContent = "Collapse";

    const fb = document.getElementById("floatingExpandBtn");
    if (fb) fb.remove();

    try { localStorage.setItem("settingsCollapsed", "false"); } catch(e){}
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("aiToggleBtn");
  const ingestBtn = document.getElementById("ingestToggleBtn");
  const recordBtn = document.getElementById("recordToggleBtn");
  const shutdownBtn = document.getElementById("shutdownBtn");

  if (btn) btn.addEventListener("click", toggleAiEnabled);
  if (ingestBtn) ingestBtn.addEventListener("click", toggleIngest);
  if (recordBtn) recordBtn.addEventListener("click", toggleRecording);
  if (shutdownBtn) shutdownBtn.addEventListener("click", shutdownSystem);

  setTimeout(syncAiUi, 0);
  syncAiUi();
  syncIngestBtn();
  syncRecordBtn();
});

(function restoreCollapsed(){
  try {
    const v = localStorage.getItem("settingsCollapsed");
    if (v === "true") toggleSettings(true);
  } catch(e){}
})();

refreshConfigForm();
refreshStatusOnly();
if (isAiEnabledUi()) {
  refreshAI();
  refreshAIEvents();
}
refreshLogTail();
