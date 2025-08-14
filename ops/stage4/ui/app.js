const $ = (id) => document.getElementById(id);

// ---------- Hardened Tab Initialization ----------
function initTabs(){
  console.log("Initializing tabs...");
  const tabs = document.querySelectorAll(".tab");
  const panels = document.querySelectorAll(".panel");
  console.log("Found tabs:", tabs.length, "panels:", panels.length);
  
  if (!tabs.length || !panels.length) {
    console.warn("Tab init: no tabs/panels found");
    return;
  }
  
  tabs.forEach(t => {
    console.log("Setting up tab:", t.dataset.tab);
    t.onclick = () => {
      console.log("Tab clicked:", t.dataset.tab);
      tabs.forEach(x => x.classList.remove("active"));
      panels.forEach(x => x.classList.remove("active"));
      t.classList.add("active");
      const pane = document.getElementById("panel-" + t.dataset.tab);
      if (pane) {
        pane.classList.add("active");
        console.log("Activated panel:", "panel-" + t.dataset.tab);
      } else {
        console.error("Panel not found:", "panel-" + t.dataset.tab);
      }
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
    lag: Array(30).fill(0),
    requests: Array(30).fill(0),
    latency: Array(30).fill(0),
    clients: Array(30).fill(0)
  },
  requests: {
    currentPage: 1,
    pageSize: 50,
    totalPages: 1,
    liveTail: false,
    eventSource: null
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
  try {
    console.log("=== REFRESH START ===");
    
    // Get requests summary for dashboard
    const requestsSummary = await refreshRequestsSummary();
    console.log("Requests summary:", requestsSummary);
    
    // Get metrics for additional data
    const mres = await call("/v1/metrics");
    console.log("Metrics response:", mres);
    let metrics = {};
    if (mres.ok) {
      try {
        metrics = JSON.parse(mres.raw);
        console.log("Parsed metrics:", metrics);
      } catch (e) {
        console.error("Failed to parse metrics JSON:", e);
      }
    }

    // Extract values from metrics
    const ingestTotal = metrics.records_processed || 0;
    const threatsTotal = metrics.totals?.threat_matches || 0;
    const riskSum = metrics.totals?.risk_sum || 0;
    const riskCount = metrics.totals?.risk_count || 0;
    const eps = metrics.rates?.eps_1m || 0;

    // KPIs - Minimal Dashboard (6 cards)
    $("kpi-events").textContent  = n(ingestTotal);
    $("kpi-threats").textContent = n(threatsTotal);
    $("kpi-risk").textContent    = (riskCount > 0) ? f2(riskSum / riskCount) : "—";
    $("kpi-requests").textContent = n(requestsSummary?.requests || 0);
    $("kpi-latency").textContent = requestsSummary?.p95_latency_ms ? `${requestsSummary.p95_latency_ms}ms` : "—";
    $("kpi-clients").textContent = n(requestsSummary?.active_clients || 0);

  // Sparklines (push current)
  pushSpark(state.sparkData.events, ingestTotal || 0);
  pushSpark(state.sparkData.threats, threatsTotal || 0);
  pushSpark(state.sparkData.risk, (riskCount > 0) ? (riskSum / riskCount) : 0);
  pushSpark(state.sparkData.requests, requestsSummary?.requests || 0);
  pushSpark(state.sparkData.latency, requestsSummary?.p95_latency_ms || 0);
  pushSpark(state.sparkData.clients, requestsSummary?.active_clients || 0);

  renderSpark("spark-events", state.sparkData.events);
  renderSpark("spark-threats", state.sparkData.threats, "#fb7185");
  renderSpark("spark-risk", state.sparkData.risk, "#f59e0b");
  renderSpark("spark-requests", state.sparkData.requests, "#8b5cf6");
  renderSpark("spark-latency", state.sparkData.latency, "#10b981");
  renderSpark("spark-clients", state.sparkData.clients, "#3b82f6");

  // Events/min - use the eps rate from metrics
  const ratePerMin = eps * 60; // Convert eps to epm
  updateChart(ratePerMin);
  
  // Update status codes display
  if (requestsSummary?.codes) {
    const codes = requestsSummary.codes;
    document.querySelector('.status-2xx').textContent = `2xx: ${codes['2xx'] || 0}`;
    document.querySelector('.status-4xx').textContent = `4xx: ${codes['4xx'] || 0}`;
    document.querySelector('.status-5xx').textContent = `5xx: ${codes['5xx'] || 0}`;
  } else {
    // Set defaults if no data
    document.querySelector('.status-2xx').textContent = '2xx: 0';
    document.querySelector('.status-4xx').textContent = '4xx: 0';
    document.querySelector('.status-5xx').textContent = '5xx: 0';
  }
  } catch (e) {
    console.error("Dashboard refresh failed:", e);
  }
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

  $("btnSystem").onclick = async () => {
    try {
      const r = await call("/v1/system");
      if (r.ok) {
        const jsonData = JSON.parse(r.body);
        $("systemLog").textContent = JSON.stringify(jsonData, null, 2);
      } else {
        $("systemLog").textContent = `[${r.status}]\n${r.body}`;
      }
    } catch (e) {
      $("systemLog").textContent = `Error loading system info: ${e.message}`;
    }
  };

  $("btnCopySystem").onclick = () => {
    navigator.clipboard.writeText($("systemLog").textContent);
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
  
  // Requests handlers
  $("btnLiveTail").onclick = toggleLiveTail;
  $("btnExportCSV").onclick = exportCSV;
  $("btnPrevPage").onclick = () => loadRequests(state.requests.currentPage - 1);
  $("btnNextPage").onclick = () => loadRequests(state.requests.currentPage + 1);
  
  // Filter change handlers
  $("filterMethod").onchange = () => loadRequests(1);
  $("filterStatus").onchange = () => loadRequests(1);
  $("filterEndpoint").onchange = () => loadRequests(1);
  $("filterIP").onchange = () => loadRequests(1);
  $("filterAPIKey").onchange = () => loadRequests(1);
  
  // Drawer handlers
  $("btnCloseDrawer").onclick = closeRequestDrawer;
  
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

// ---------- Requests Summary Function ----------
async function refreshRequestsSummary() {
  try {
    const response = await fetch('/v1/admin/requests/summary?window=15');
    if (response.ok) {
      const summary = await response.json();
      return summary;
    }
  } catch (error) {
    console.error('Failed to fetch requests summary:', error);
  }
  return null;
}

async function loadRequests(page = 1) {
  try {
    const filters = getRequestFilters();
    const params = new URLSearchParams({
      page: page,
      page_size: state.requests.pageSize,
      ...filters
    });
    
    const res = await fetch(`/v1/admin/requests?${params}`);
    const data = await res.json();
    
    // Update pagination
    state.requests.currentPage = data.page;
    state.requests.totalPages = data.pages;
    $("pageInfo").textContent = `Page ${data.page} of ${data.pages}`;
    $("btnPrevPage").disabled = data.page <= 1;
    $("btnNextPage").disabled = data.page >= data.pages;
    
    // Render table
    renderRequestsTable(data.items);
    
  } catch (e) {
    console.error("Failed to load requests:", e);
    $("requestsTableBody").innerHTML = `<tr><td colspan="10" style="text-align:center;color:var(--err)">Failed to load requests: ${e.message}</td></tr>`;
  }
}

function getRequestFilters() {
  const filters = {};
  const method = $("filterMethod").value;
  const status = $("filterStatus").value;
  const endpoint = $("filterEndpoint").value;
  const ip = $("filterIP").value;
  const apiKey = $("filterAPIKey").value;
  
  if (method) filters.method = method;
  if (status) filters.status = parseInt(status);
  if (endpoint) filters.endpoint = endpoint;
  if (ip) filters.client_ip = ip;
  if (apiKey) filters.api_key_prefix = apiKey;
  
  return filters;
}

function renderRequestsTable(requests) {
  const tbody = $("requestsTableBody");
  tbody.innerHTML = "";
  
  if (requests.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align:center;color:var(--muted)">No requests found</td></tr>`;
    return;
  }
  
  requests.forEach(req => {
    const row = document.createElement("tr");
    row.style.cursor = "pointer";
    row.onclick = () => showRequestDetails(req.id);
    row.innerHTML = `
      <td>${formatTime(req.ts)}</td>
      <td>${req.client_ip} ${req.geo_country ? `🇺🇸` : ''}</td>
      <td>${req.api_key_masked || 'anonymous'}</td>
      <td>${req.method}</td>
      <td>${req.path}</td>
      <td><span class="status-badge status-${req.status}">${req.status}</span></td>
      <td style="text-align:right;font-family:monospace">${req.duration_ms}ms</td>
      <td style="text-align:right;font-family:monospace">${req.bytes_in}/${req.bytes_out}</td>
      <td><span class="status-badge result-${req.result}">${req.result}</span></td>
      <td style="font-family:monospace;font-size:11px">${req.trace_id?.substring(0, 8)}...</td>
    `;
    tbody.appendChild(row);
  });
}

function formatTime(ts) {
  if (!ts) return "—";
  const date = new Date(ts);
  return date.toLocaleTimeString();
}

function toggleLiveTail() {
  if (state.requests.liveTail) {
    stopLiveTail();
  } else {
    startLiveTail();
  }
}

function startLiveTail() {
  if (state.requests.eventSource) {
    state.requests.eventSource.close();
  }
  
  const filters = getRequestFilters();
  const params = new URLSearchParams(filters);
  
  state.requests.eventSource = new EventSource(`/v1/admin/requests/stream?${params}`);
  
  state.requests.eventSource.onmessage = function(event) {
    if (event.type === 'message') {
      try {
        const data = JSON.parse(event.data);
        // Add new request to table
        const tbody = $("requestsTableBody");
        const row = document.createElement("tr");
        row.style.animation = "pulse 0.5s ease-in-out";
        row.innerHTML = `
          <td>${formatTime(data.ts)}</td>
          <td>${data.client_ip} ${data.geo_country ? `🇺🇸` : ''}</td>
          <td>${data.api_key_masked || 'anonymous'}</td>
          <td>${data.method}</td>
          <td>${data.path}</td>
          <td><span class="status-badge status-${data.status}">${data.status}</span></td>
          <td style="text-align:right;font-family:monospace">${data.duration_ms}ms</td>
          <td style="text-align:right;font-family:monospace">${data.bytes_in}/${data.bytes_out}</td>
          <td><span class="status-badge result-${data.result}">${data.result}</span></td>
          <td style="font-family:monospace;font-size:11px">${data.trace_id?.substring(0, 8)}...</td>
        `;
        tbody.insertBefore(row, tbody.firstChild);
        
        // Remove old rows if too many
        while (tbody.children.length > 100) {
          tbody.removeChild(tbody.lastChild);
        }
      } catch (e) {
        console.error("Failed to parse SSE data:", e);
      }
    }
  };
  
  state.requests.eventSource.onerror = function(event) {
    console.error("SSE error:", event);
    stopLiveTail();
  };
  
  state.requests.liveTail = true;
  $("btnLiveTail").textContent = "Stop Live Tail";
  $("btnLiveTail").classList.add("active");
}

function stopLiveTail() {
  if (state.requests.eventSource) {
    state.requests.eventSource.close();
    state.requests.eventSource = null;
  }
  
  state.requests.liveTail = false;
  $("btnLiveTail").textContent = "Live Tail";
  $("btnLiveTail").classList.remove("active");
}

async function closeRequestDrawer() {
  const drawer = $("requestDetailsDrawer");
  drawer.classList.remove("open");
  drawer.style.display = "none";
}

async function showRequestDetails(requestId) {
  try {
    const res = await fetch(`/v1/admin/requests/${requestId}`);
    const req = await res.json();
    
    const content = $("requestDetailsContent");
    content.innerHTML = `
      <h4>Request Information</h4>
      <pre>${JSON.stringify({
        id: req.id,
        timestamp: req.ts,
        method: req.method,
        path: req.path,
        status: req.status,
        duration_ms: req.duration_ms,
        client_ip: req.client_ip,
        user_agent: req.user_agent,
        geo_country: req.geo_country,
        asn: req.asn
      }, null, 2)}</pre>
      
      <h4>Operations Data</h4>
      <pre>${req.ops ? JSON.stringify(req.ops, null, 2) : 'No operations data available'}</pre>
      
      ${req.error ? `<h4>Error</h4><pre class="err">${req.error}</pre>` : ''}
      
      <h4>Full Request Data</h4>
      <pre>${JSON.stringify(req, null, 2)}</pre>
    `;
    
    const drawer = $("requestDetailsDrawer");
    drawer.style.display = "block";
    setTimeout(() => drawer.classList.add("open"), 10);
  } catch (e) {
    console.error("Failed to load request details:", e);
  }
}

async function exportCSV() {
  try {
    const filters = getRequestFilters();
    const params = new URLSearchParams({
      page_size: 1000, // Get more data for export
      ...filters
    });
    
    const res = await fetch(`/v1/admin/requests?${params}`);
    const data = await res.json();
    
    // Create CSV content
    const csv = [
      "Time,Client IP,API Key,Method,Path,Status,Duration (ms),Bytes In,Bytes Out,Result,Trace ID",
      ...data.items.map(req => [
        req.ts,
        req.client_ip,
        req.api_key_masked || 'anonymous',
        req.method,
        req.path,
        req.status,
        req.duration_ms,
        req.bytes_in,
        req.bytes_out,
        req.result,
        req.trace_id
      ].join(","))
    ].join("\n");
    
    // Download file
    const blob = new Blob([csv], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `requests-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
    
  } catch (e) {
    console.error("Failed to export CSV:", e);
    alert("Failed to export CSV: " + e.message);
  }
}

// ---------- Logs Functions ----------
async function refreshLogs() {
  try {
    const res = await fetch("/v1/logs/tail?max_bytes=1024&format=text");
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
  
  // Load initial requests data
  loadRequests(1);
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
  console.log("DOM Content Loaded - Starting initialization...");
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
