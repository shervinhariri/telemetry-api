const $ = (id) => document.getElementById(id);

// ---------- Hardened Tab Initialization ----------
function initTabs(){
  const tabs = document.querySelectorAll(".tab");
  const panels = document.querySelectorAll(".panel");
  if (!tabs.length || !panels.length) {
    console.warn("Tab init: no tabs/panels found");
    return;
  }
  tabs.forEach(t => {
    t.onclick = () => {
      tabs.forEach(x => x.classList.remove("active"));
      panels.forEach(x => x.classList.remove("active"));
      t.classList.add("active");
      const pane = document.getElementById("panel-" + t.dataset.tab);
      if (pane) pane.classList.add("active");
      // optional deep-link
      try { location.hash = "#tab=" + t.dataset.tab; } catch {}
    };
  });

  // activate from hash if present
  const m = location.hash.match(/#tab=([a-z0-9_-]+)/i);
  if (m) {
    const t = document.querySelector(`.tab[data-tab="${m[1]}"]`);
    if (t) t.click();
  }
}

// ---------- Helpers ----------
function authHeader() {
  const key = $("key").value.trim();
  return { "Authorization": `Bearer ${key}`, "Content-Type":"application/json" };
}

async function call(path, init={}) {
  const res = await fetch(path, init);
  const text = await res.text();
  let parsed = text;
  try { parsed = JSON.parse(text); parsed = JSON.stringify(parsed, null, 2); } catch {}
  return { ok: res.ok, status: res.status, raw: text, body: parsed };
}

// ---------- Prometheus parsing ----------
function parseProm(text) {
  const map = new Map();
  for (const line of text.split(/\r?\n/)) {
    if (!line || line.startsWith("#")) continue;
    const m = line.match(/^([a-zA-Z_:][a-zA-Z0-9_:]*)\s+([+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)/);
    if (m) map.set(m[1], Number(m[2]));
  }
  return map;
}

function n(x) { return (x===undefined || isNaN(x)) ? "—" : Intl.NumberFormat().format(x); }
function f2(x) { return (x===undefined || isNaN(x)) ? "—" : x.toFixed(2); }

// ---------- KPI state ----------
const state = {
  ring: Array(180).fill(null), // last 15 min at 5s sampling
  ringIdx: 0,
  prevIngest: undefined,
  chart: null,
  sparkData: {
    events: Array(30).fill(0),
    sources: Array(30).fill(0),
    batches: Array(30).fill(0),
    threats: Array(30).fill(0),
    risk: Array(30).fill(0),
    lag: Array(30).fill(0)
  }
};

function pushSpark(arr, v){ arr.push(v ?? 0); if(arr.length>30) arr.shift(); }
function renderSpark(elId, arr, color="#8b5cf6"){
  const w=120,h=28; const max=Math.max(1, ...arr);
  const points=arr.map((v,i)=>`${(i/(arr.length-1))*w},${h - (v/max)*h}`).join(" ");
  $(elId).setAttribute("viewBox", `0 0 ${w} ${h}`);
  $(elId).innerHTML = `<polyline fill="none" stroke="${color}" stroke-width="2" points="${points}" />`;
}

// ---------- Chart ----------
function ensureChart(){
  if (state.chart) return;
  const ctx = $("eventsChart").getContext("2d");
  state.chart = new Chart(ctx, {
    type: "line",
    data: { labels: Array(180).fill(""), datasets: [{ label: "Events/min", data: Array(180).fill(null) }] },
    options: {
      responsive: true,
      animation: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { display: false },
        y: { beginAtZero: true, ticks: { precision: 0 } }
      },
      plugins: { legend: { display: true } }
    }
  });
}

function updateChart(v){
  ensureChart();
  state.ring[state.ringIdx] = v;
  state.ringIdx = (state.ringIdx + 1) % state.ring.length;
  const ordered = state.ring.slice(state.ringIdx).concat(state.ring.slice(0, state.ringIdx));
  state.chart.data.datasets[0].data = ordered;
  state.chart.update();
}

// ---------- Refresh metrics loop ----------
async function refresh(){
  const mres = await call("/v1/metrics");
  if (!mres.ok) { $("metricsLog").textContent = `[${mres.status}] Failed to fetch`; return; }
  $("metricsLog").textContent = mres.raw;

  const m = parseProm(mres.raw);

  // Expected metric names (fallbacks safe)
  const ingestTotal = m.get("telemetry_ingest_total") ?? m.get("ingest_total");
  const threatsTotal = m.get("telemetry_threat_matches_total") ?? m.get("threat_matches_total");
  const riskSum = m.get("telemetry_risk_score_sum");
  const riskCount = m.get("telemetry_risk_score_count");
  const lag = m.get("telemetry_queue_lag_gauge") ?? m.get("queue_lag");
  const sourcesActive = m.get("telemetry_sources_active") ?? m.get("sources_active");
  const batchesTotal = m.get("telemetry_batches_total") ?? m.get("ingest_batches_total");

  // KPIs
  $("kpi-events").textContent  = n(ingestTotal);
  $("kpi-threats").textContent = n(threatsTotal);
  $("kpi-risk").textContent    = (riskSum!==undefined && riskCount>0) ? f2(riskSum / riskCount) : "—";
  $("kpi-lag").textContent     = n(lag);
  $("kpi-sources").textContent = n(sourcesActive);
  $("kpi-batches").textContent = n(batchesTotal);

  // Sparklines (push current)
  pushSpark(state.sparkData.events, ingestTotal || 0);
  pushSpark(state.sparkData.sources, sourcesActive || 0);
  pushSpark(state.sparkData.batches, batchesTotal || 0);
  pushSpark(state.sparkData.threats, threatsTotal || 0);
  pushSpark(state.sparkData.risk, (riskSum!==undefined&&riskCount>0)?(riskSum/riskCount):0);
  pushSpark(state.sparkData.lag, lag || 0);

  renderSpark("spark-events", state.sparkData.events);
  renderSpark("spark-sources", state.sparkData.sources, "#60a5fa");
  renderSpark("spark-batches", state.sparkData.batches, "#34d399");
  renderSpark("spark-threats", state.sparkData.threats, "#fb7185");
  renderSpark("spark-risk", state.sparkData.risk, "#f59e0b");
  renderSpark("spark-lag", state.sparkData.lag, "#9fb3c8");

  // Events/min
  if (state.prevIngest !== undefined && ingestTotal !== undefined) {
    const delta = Math.max(0, ingestTotal - state.prevIngest);
    const ratePerMin = (delta / 5) * 60; // 5s interval
    updateChart(ratePerMin);
  }
  state.prevIngest = ingestTotal;
}

// ---------- Button Handlers ----------
function initHandlers(){
  $("btnHealth").onclick = async () => {
    const r = await call("/v1/health");
    $("healthLog").textContent = `[${r.status}]\n${r.body}`;
  };

  $("btnMetrics").onclick = async () => {
    const r = await call("/v1/metrics");
    $("metricsLog").textContent = `[${r.status}]\n${r.raw}`;
  };

  $("btnIngest").onclick = async () => {
    let body = $("ingestBody").value;
    try { JSON.parse(body); } catch (e) { return $("ingestLog").textContent = "Invalid JSON body"; }
    const r = await call("/v1/ingest", { method:"POST", headers: authHeader(), body });
    $("ingestLog").textContent = `[${r.status}]\n${r.body}`;
  };

  $("btnIngestClear").onclick = () => { $("ingestLog").textContent = ""; };

  $("btnLookup").onclick = async () => {
    const value = $("lookupValue").value.trim();
    const type = $("lookupType").value;
    const r = await call("/v1/lookup", { method:"POST", headers: authHeader(), body: JSON.stringify({ type, value }) });
    $("lookupLog").textContent = `[${r.status}]\n${r.body}`;
  };

  $("btnSaveSplunk").onclick = async () => {
    const payload = { url: $("splunkUrl").value.trim(), token: $("splunkToken").value.trim() };
    const r = await call("/v1/outputs/splunk", { method:"POST", headers: authHeader(), body: JSON.stringify(payload) });
    $("splunkLog").textContent = `[${r.status}]\n${r.body}`;
  };

  $("btnTestSplunk").onclick = () => { $("splunkLog").textContent = "Tip: send a tiny ingest and check HEC events."; };

  $("btnSaveElastic").onclick = async () => {
    const payload = {
      url: $("esUrl").value.trim(),
      index: $("esIndex").value.trim() || "telemetry-events",
      username: $("esUser").value.trim(),
      password: $("esPass").value.trim()
    };
    const r = await call("/v1/outputs/elastic", { method:"POST", headers: authHeader(), body: JSON.stringify(payload) });
    $("elasticLog").textContent = `[${r.status}]\n${r.body}`;
  };

  $("btnTestElastic").onclick = () => { $("elasticLog").textContent = "Tip: run an ingest, then query the index in Elastic."; };

  // Logs tab handlers
  $("btnRefreshLogs").onclick = refreshLogs;
  $("btnClearLogs").onclick = () => { $("logsTail").textContent = ""; };
  $("btnDownloadLogs").onclick = downloadLogs;
  $("btnUploadLogs").onclick = () => { $("logFileInput").click(); };
  
  $("logFileInput").onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append("file", file);
    
    try {
      const res = await fetch("/v1/logs/upload", {
        method: "POST",
        body: formData
      });
      
      const result = await res.json();
      $("logsUpload").textContent = JSON.stringify(result, null, 2);
    } catch (e) {
      $("logsUpload").textContent = `Upload failed: ${e.message}`;
    }
  };
}

// ---------- Logs Functions ----------
async function refreshLogs() {
  try {
    const res = await fetch("/v1/logs/tail?max_bytes=65536&format=text");
    const text = await res.text();
    $("logsTail").textContent = text;
    
    // Auto-scroll to bottom
    const tail = $("logsTail");
    tail.scrollTop = tail.scrollHeight;
  } catch (e) {
    $("logsTail").textContent = `Failed to load logs: ${e.message}`;
  }
}

async function downloadLogs() {
  try {
    const res = await fetch("/v1/logs/download?max_bytes=2000000");
    const blob = await res.blob();
    
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `app_log_${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.log`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  } catch (e) {
    alert(`Download failed: ${e.message}`);
  }
}

// ---------- Start Refresh Loop ----------
function startRefresh(){
  ensureChart();
  refresh();
  setInterval(refresh, 5000);
}

// ---------- Minimal Version Dot ----------
async function initVersionDot() {
  const dot = document.getElementById("versionDot");
  const text = document.getElementById("versionText");

  try {
    const verRes = await fetch("/v1/version");
    const ver = await verRes.json();

    const updateRes = await fetch("/v1/updates/check");
    const update = await updateRes.json();

    text.textContent = `v${ver.version}`;

    if (update.enabled && update.update_available) {
      dot.classList.add("update-available");
      dot.title = `Update available: ${update.latest}`;
    } else {
      dot.classList.remove("update-available");
      dot.title = "Up to date";
    }
  } catch (e) {
    text.textContent = "v0.6.0";
    dot.title = "Version check failed";
  }

  setInterval(async () => {
    try {
      const res = await fetch("/v1/updates/check");
      const update = await res.json();
      if (update.enabled && update.update_available) {
        dot.classList.add("update-available");
        dot.title = `Update available: ${update.latest}`;
      } else {
        dot.classList.remove("update-available");
        dot.title = "Up to date";
      }
    } catch (e) { /* Silently fail on update checks */ }
  }, 60000);
}

// ---------- DOM Ready Initialization ----------
document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initHandlers();
  startRefresh();
  initVersionDot();
  
  // simple runtime diag
  window.__uiDiag = () => ({
    tabs: document.querySelectorAll(".tab").length,
    panels: document.querySelectorAll(".panel").length,
    appJsLoaded: true,
    scriptSrcOk: Array.from(document.scripts).some(s => (s.src||"").includes("/ui/app.js"))
  });
  
  // Update diagnostics display
  const d = window.__uiDiag();
  const el = document.getElementById("diagLine");
  if (el) el.textContent = `diag → tabs:${d.tabs} panels:${d.panels} appJsLoaded:${d.appJsLoaded}`;
});
