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
async function call(path, init={}) {
  try {
    // Use the new central API client
    const data = await api(path);
    return { ok: true, status: 200, raw: JSON.stringify(data), body: data };
  } catch (e) {
    console.error("API call failed:", e);
    showToast(`Failed to load ${path} (${e.message})`, 'error');
    return { ok: false, status: 0, raw: e.message, body: null };
  }
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

// ---------- Status and Version Management ----------
let statusCheckInterval = null;
let lastStatusCheck = null;

async function checkStatus() {
  try {
    const response = await fetch('/v1/health');
    const isOnline = response.ok;
    updateStatusChip(isOnline);
    lastStatusCheck = new Date();
  } catch (error) {
    updateStatusChip(false);
    lastStatusCheck = new Date();
  }
}

function updateStatusChip(isOnline) {
  const statusChip = $('statusChip');
  const statusDot = statusChip.querySelector('.status-dot');
  const statusText = $('statusText');
  
  if (isOnline) {
    statusDot.classList.remove('offline');
    statusDot.classList.add('online');
    statusText.textContent = 'Online';
    statusChip.title = `Last checked: ${lastStatusCheck?.toLocaleTimeString() || 'Now'}`;
  } else {
    statusDot.classList.remove('online');
    statusDot.classList.add('offline');
    statusText.textContent = 'Offline';
    statusChip.title = `Last checked: ${lastStatusCheck?.toLocaleTimeString() || 'Now'}`;
  }
}

async function loadVersion() {
  try {
    const data = await api('/system');
    const versionText = $('versionText');
    versionText.textContent = `Version: ${data.version}`;
  } catch (error) {
    const versionText = $('versionText');
    versionText.textContent = 'Version: Unknown';
  }
}

function initAPIKey() {
  const keyInput = $('key');
  
  // Load saved API key
  const savedKey = localStorage.getItem('telemetry_api_key');
  if (savedKey) {
    keyInput.value = savedKey;
  }
  
  // Save API key on blur
  keyInput.addEventListener('blur', () => {
    const key = keyInput.value.trim();
    if (key) {
      localStorage.setItem('telemetry_api_key', key);
    }
  });
  
  // Save on Enter
  keyInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      keyInput.blur();
    }
  });
}

function startStatusPolling() {
  // Check immediately
  checkStatus();
  
  // Then every 30 seconds
  statusCheckInterval = setInterval(checkStatus, 30000);
}

// ---------- KPI state ----------
const state = {
  ring: Array(180).fill(null), // last 15 min at 5s sampling
  ringIdx: 0,
  prevIngest: undefined,
  chart: null,
  throughputChart: null,
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
    eventSource: null,
    selectedRequest: null
  }
};

function pushSpark(arr, v){ arr.push(v ?? 0); if(arr.length>30) arr.shift(); }
function renderSpark(elId, arr, color="#8b5cf6"){
  const w=120,h=28; const max=Math.max(1, ...arr);
  const points=arr.map((v,i)=>`${(i/(arr.length-1))*w},${h - (v/max)*h}`).join(" ");
  $(elId).setAttribute("viewBox", `0 0 ${w} ${h}`);

// Simple API test function
async function testAPI() {
  console.log('🧪 Testing API directly...');
  try {
    const system = await api('/system');
    console.log('✅ System:', system.version);
    
    const metrics = await api('/metrics');
    console.log('✅ Metrics:', metrics.eps, 'EPS');
    
    const requests = await api('/api/requests', { limit: 50, window: '15m' });
    console.log('✅ Requests:', requests.items ? requests.items.length : 0, 'items');
    
    // Update the UI directly
    if (requests.items && requests.items.length > 0) {
      const first = requests.items[0];
      console.log('✅ First request:', first.method, first.path, first.latency_ms + 'ms');
      
      // Force update the dashboard
      document.getElementById('queue-lag').textContent = requests.items.length;
      document.getElementById('avg-risk').textContent = '0.0';
      document.getElementById('threat-matches').textContent = '0';
      document.getElementById('error-rate').textContent = '0.0';
    }
    
    return true;
  } catch (error) {
    console.error('❌ API test failed:', error);
    return false;
  }
}

// Initialize throughput chart
function initThroughputChart() {
  try {
    const ctx = document.getElementById('throughput-chart');
    if (!ctx) {
      console.log('Throughput chart canvas not found, skipping initialization');
      return;
    }
    
    // Check if Chart.js is available
    if (typeof Chart === 'undefined') {
      console.log('Chart.js not loaded, skipping throughput chart initialization');
      return;
    }
    
    state.throughputChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: Array(15).fill('').map((_, i) => `${15-i}m ago`),
        datasets: [{
          label: 'Events/sec',
          data: Array(15).fill(0),
          borderColor: '#8b5cf6',
          backgroundColor: 'rgba(139, 92, 246, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          x: {
            display: true,
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            },
            ticks: {
              color: '#9fb3c8'
            }
          },
          y: {
            display: true,
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            },
            ticks: {
              color: '#9fb3c8'
            }
          }
        }
      }
    });
    console.log('✅ Throughput chart initialized successfully');
  } catch (error) {
    console.error('❌ Error initializing throughput chart:', error);
  }
}

// Update throughput chart
function updateThroughputChart(eps) {
  if (!state.throughputChart) {
    console.log('Chart not initialized, skipping update');
    return;
  }
  
  try {
    const chart = state.throughputChart;
    chart.data.datasets[0].data.push(eps);
    chart.data.datasets[0].data.shift();
    chart.update('none');
  } catch (error) {
    console.error('Error updating throughput chart:', error);
  }
}

// Load requests data with enhanced API
async function loadRequests() {
  try {
    const windowSelect = $('windowSelect');
    const selectedWindow = windowSelect ? windowSelect.value : '24h';
    
    const res = await call('/api/requests', { limit: 500, window: selectedWindow });
    if (!res.ok) {
      console.error("Failed to load requests:", res.status);
      return;
    }
    
    const data = res.body;
    
    // Update state cards with debugging
    console.log('🔧 Updating request cards with data:', {
      total: data.total,
      succeeded: data.succeeded,
      failed: data.failed,
      avg_latency_ms: data.avg_latency_ms
    });
    console.log('🔧 Raw API response:', JSON.stringify(data, null, 2));
    
    const totalEl = $("#total-requests");
    const succeededEl = $("#succeeded-requests");
    const failedEl = $("#failed-requests");
    const latencyEl = $("#avg-latency");
    
    if (totalEl) {
      totalEl.textContent = n(data.total || 0);
      console.log('✅ Updated total-requests:', n(data.total || 0));
    } else {
      console.log('❌ total-requests element not found');
    }
    
    if (succeededEl) {
      succeededEl.textContent = n(data.succeeded || 0);
      console.log('✅ Updated succeeded-requests:', n(data.succeeded || 0));
    } else {
      console.log('❌ succeeded-requests element not found');
    }
    
    if (failedEl) {
      failedEl.textContent = n(data.failed || 0);
      console.log('✅ Updated failed-requests:', n(data.failed || 0));
    } else {
      console.log('❌ failed-requests element not found');
    }
    
    if (latencyEl) {
      latencyEl.textContent = f2(data.avg_latency_ms || 0);
      console.log('✅ Updated avg-latency:', f2(data.avg_latency_ms || 0));
    } else {
      console.log('❌ avg-latency element not found');
    }
    
    // Handle empty state
    const emptyState = $('emptyState');
    const tableContainer = $('requestsTable').closest('.table-container');
    
    if (!data.items || data.items.length === 0) {
      if (emptyState) emptyState.style.display = 'block';
      if (tableContainer) tableContainer.style.display = 'none';
    } else {
      if (emptyState) emptyState.style.display = 'none';
      if (tableContainer) tableContainer.style.display = 'block';
      updateRequestsTable(data.items);
    }
    
  } catch (e) {
    console.error("Error loading requests:", e);
  }
}

// Update requests table with new structure
function updateRequestsTable(requests) {
  const tbody = $("#requestsTableBody");
  if (!tbody) return;
  
  tbody.innerHTML = "";
  
  requests.forEach(req => {
    const row = document.createElement("tr");
    row.onclick = () => openRequestDrawer(req);
    row.style.cursor = "pointer";
    
    const time = new Date(req.ts || req.timestamp).toLocaleTimeString();
    const statusClass = req.status >= 400 ? 'status-' + req.status : 'status-200';
    
    row.innerHTML = `
      <td>${time}</td>
      <td>${req.method || '—'}</td>
      <td>${req.path || '—'}</td>
      <td><span class="status-badge ${statusClass}">${req.status || '—'}</span></td>
      <td>${f2(req.latency_ms || req.duration_ms || 0)}</td>
      <td>${req.source_ip || req.client_ip || '—'}</td>
      <td>${n(req.records || 0)}</td>
      <td>${f2(req.risk_avg || 0)}</td>
      <td><button onclick="openRequestDrawer(${JSON.stringify(req).replace(/"/g, '&quot;')})" class="mutebtn">Details</button></td>
    `;
    
    tbody.appendChild(row);
  });
}

// Open request details drawer
function openRequestDrawer(request) {
  state.requests.selectedRequest = request;
  
  // Populate drawer content
  $("#drawer-request-id").textContent = request.id || request.trace_id || '—';
  
  const timestamps = [];
  if (request.ts) timestamps.push(`Received: ${new Date(request.ts).toLocaleString()}`);
  if (request.enrichment_start) timestamps.push(`Enrichment Start: ${new Date(request.enrichment_start).toLocaleString()}`);
  if (request.enrichment_end) timestamps.push(`Enrichment End: ${new Date(request.enrichment_end).toLocaleString()}`);
  if (request.exported_at) timestamps.push(`Exported: ${new Date(request.exported_at).toLocaleString()}`);
  $("#drawer-timestamps").textContent = timestamps.join('\n') || '—';
  
  // Headers (redact Authorization)
  const headers = request.headers || {};
  const safeHeaders = { ...headers };
  if (safeHeaders.Authorization) {
    safeHeaders.Authorization = 'Bearer [REDACTED]';
  }
  $("#drawer-headers").textContent = JSON.stringify(safeHeaders, null, 2);
  
  // Payload summary
  const payload = {
    type: request.handler || 'unknown',
    count: request.records_processed || 0,
    parsing_errors: request.validation_errors || []
  };
  $("#drawer-payload").textContent = JSON.stringify(payload, null, 2);
  
  // Enrichment results
  const enrichment = {
    geo_enriched: request.geo_enriched || 0,
    asn_enriched: request.asn_enriched || 0,
    threat_matches: request.threat_matches || 0,
    risk_score: request.avg_risk || 0
  };
  $("#drawer-enrichment").textContent = JSON.stringify(enrichment, null, 2);
  
  // Export actions
  const exports = {
    splunk: request.splunk_export || { sent: 0, failed: 0 },
    elastic: request.elastic_export || { sent: 0, failed: 0 }
  };
  $("#drawer-exports").textContent = JSON.stringify(exports, null, 2);
  
  // Errors/exceptions
  const errors = request.error || request.exception || 'None';
  $("#drawer-errors").textContent = errors;
  
  // Open drawer
  $("#request-drawer").classList.add("open");
}

// Close request details drawer
function closeRequestDrawer() {
  $("#request-drawer").classList.remove("open");
  state.requests.selectedRequest = null;
}

// Open raw JSON in new window
function openRawJson() {
  if (!state.requests.selectedRequest) return;
  
  const jsonStr = JSON.stringify(state.requests.selectedRequest, null, 2);
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  
  const win = window.open(url, '_blank');
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
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
    const mres = await call("/metrics");
    console.log("Metrics response:", mres);
    let metrics = {};
    if (mres.ok) {
      console.log("Raw metrics:", JSON.stringify(mres.body, null, 2));
      metrics = normalizeMetrics(mres.body);
      console.log("Normalized metrics:", metrics);
    }

    // Extract values from metrics
    const ingestTotal = metrics.records_processed || 0;
    const threatsTotal = metrics.totals?.threat_matches || 0;
    const riskSum = metrics.totals?.risk_sum || 0;
    const riskCount = metrics.totals?.risk_count || 0;
    const eps = metrics.rates?.eps_1m || 0;

    // Legacy KPIs (hidden by default) - with null checks
    const kpiEvents = $("kpi-events");
    const kpiThreats = $("kpi-threats");
    const kpiRisk = $("kpi-risk");
    const kpiRequests = $("kpi-requests");
    const kpiLatency = $("kpi-latency");
    const kpiClients = $("kpi-clients");
    
    if (kpiEvents) kpiEvents.textContent = n(ingestTotal);
    if (kpiThreats) kpiThreats.textContent = n(threatsTotal);
    if (kpiRisk) kpiRisk.textContent = (riskCount > 0) ? f2(riskSum / riskCount) : "—";
    if (kpiRequests) kpiRequests.textContent = n(requestsSummary?.total || 0);
    if (kpiLatency) kpiLatency.textContent = requestsSummary?.avg_latency_ms ? `${Math.round(requestsSummary.avg_latency_ms)}ms` : "—";
    if (kpiClients) kpiClients.textContent = n(requestsSummary?.active_clients || 0);
    
    // New Dashboard State Cards - with null checks and proper property mapping
    const queueLag = $("#queue-lag");
    const avgRisk = $("#avg-risk");
    const threatMatches = $("#threat-matches");
    
    // Use normalized metrics data
    const queueDepth = metrics.queueLag || 0;
    const avgRiskValue = metrics.avgRisk || 0;
    const threatMatchesCount = metrics.threatMatches || 0;
    
    console.log('🔧 Dashboard metrics mapping:', {
      queueDepth,
      avgRiskValue,
      threatMatchesCount,
      riskCount,
      riskSum
    });
    
    if (queueLag) {
      queueLag.textContent = safeNumber(queueDepth);
      console.log('✅ Updated queue-lag:', queueDepth);
    }
    if (avgRisk) {
      avgRisk.textContent = avgRiskValue ? avgRiskValue.toFixed(1) : "0.0";
      console.log('✅ Updated avg-risk:', avgRiskValue ? avgRiskValue.toFixed(1) : "0.0");
    }
    if (threatMatches) {
      threatMatches.textContent = safeNumber(threatMatchesCount);
      console.log('✅ Updated threat-matches:', threatMatchesCount);
    }
    
    // Calculate error rate with proper property mapping
    const totalRequests = requestsSummary?.total || 0;
    const failedRequests = requestsSummary?.failed || 0;
    const errorRate = totalRequests > 0 ? (failedRequests / totalRequests * 100) : 0;
    const errorRateEl = $("#error-rate");
    if (errorRateEl) {
      errorRateEl.textContent = safePercentage(errorRate);
      console.log('✅ Updated error-rate:', safePercentage(errorRate));
    }
    
    // Update throughput chart
    updateThroughputChart(eps || 0);

  // Sparklines (push current)
  pushSpark(state.sparkData.events, ingestTotal || 0);
  pushSpark(state.sparkData.threats, threatsTotal || 0);
  pushSpark(state.sparkData.risk, (riskCount > 0) ? (riskSum / riskCount) : 0);
  pushSpark(state.sparkData.requests, requestsSummary?.total || 0);
  pushSpark(state.sparkData.latency, requestsSummary?.avg_latency_ms || 0);
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
  
  // Update status codes display - calculate from requests data
  const succeeded = requestsSummary?.succeeded || 0;
  const failed = requestsSummary?.failed || 0;
  const total = requestsSummary?.total || 0;
  const other = total - succeeded - failed;
  
  const status2xx = document.querySelector('.status-2xx');
  const status4xx = document.querySelector('.status-4xx');
  const status5xx = document.querySelector('.status-5xx');
  
  if (status2xx) status2xx.textContent = `2xx: ${succeeded}`;
  if (status4xx) status4xx.textContent = `4xx: ${failed}`;
  if (status5xx) status5xx.textContent = `5xx: ${other}`;
  } catch (e) {
    console.error("Dashboard refresh failed:", e);
  }
}

// ---------- Button Handlers ----------
function initHandlers(){
  // Health button removed - replaced with status chip

  $("btnMetrics").onclick = async () => {
    try {
      const r = await call("/metrics");
      if (r.ok) {
        console.log('Raw metrics data:', JSON.stringify(r.body, null, 2));
        const normalized = normalizeMetrics(r.body);
        console.log('Normalized metrics data:', normalized);
        $("metricsLog").textContent = JSON.stringify(normalized, null, 2);
      } else {
        $("metricsLog").textContent = `[${r.status}]\n${r.body}`;
      }
    } catch (e) {
      $("metricsLog").textContent = `Error loading metrics: ${e.message}`;
    }
  };

  $("btnSystem").onclick = async () => {
    try {
      const r = await call("/system");
      if (r.ok) {
        console.log('Raw system data:', JSON.stringify(r.body, null, 2));
        const normalized = normalizeSystem(r.body);
        console.log('Normalized system data:', normalized);
        $("systemLog").textContent = JSON.stringify(normalized, null, 2);
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
    console.log('🔍 Calling refreshRequestsSummary...');
    const response = await call('/api/requests', { limit: 50, window: '15m' });
    console.log('🔍 Response:', response);
    
    if (response.ok) {
      const data = response.body;
      console.log('🔍 Raw data received:', JSON.stringify(data, null, 2));
      
      // Use normalization utility
      const normalized = normalizeRequests(data);
      console.log('🔍 Normalized requests:', normalized);
      
      // Create summary from normalized data
      const summary = {
        total: normalized.length,
        succeeded: normalized.filter(item => item.status >= 200 && item.status < 300).length,
        failed: normalized.filter(item => item.status >= 400).length,
        avg_latency_ms: normalized.length > 0 ? 
          normalized.reduce((sum, item) => sum + item.latencyMs, 0) / normalized.length : 0
      };
      console.log('🔍 Summary created:', summary);
      return summary;
    }
    console.log('🔍 Response not ok:', response);
    return null;
  } catch (error) {
    console.error('❌ Error refreshing requests summary:', error);
    return null;
  }
}

async function loadRequests(page = 1) {
  try {
    const windowSelect = $('windowSelect');
    const selectedWindow = windowSelect ? windowSelect.value : '24h';
    
    const res = await call('/api/requests', { limit: 500, window: selectedWindow });
    if (!res.ok) {
      console.error("Failed to load requests:", res.status);
      return;
    }
    
    const data = res.body;
    
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
  
  state.requests.eventSource = new EventSource(`${window.__CFG__.API_BASE_URL}/v1/admin/requests/stream?${params}`);
  
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
    // Don't let SSE errors break the main functionality
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
  initThroughputChart(); // Initialize the throughput chart
  refresh();
  setInterval(refresh, 5000);
  
  // Load initial requests data
  loadRequests();
  
  // Load requests data every 5 seconds
  setInterval(loadRequests, 5000);
}

// ---------- Minimal Version Dot ----------
async function initVersionDot() {
  const dot = document.getElementById("versionDot");
  const text = document.getElementById("versionText");

  try {
    const ver = await api('/version');
    const update = await api('/updates/check');

    text.textContent = `v${ver.version}`;

    if (update.enabled && update.update_available) {
      dot.classList.add("update-available");
      dot.title = `Update available: ${update.latest}`;
    } else {
      dot.classList.remove("update-available");
      dot.title = "Up to date";
    }
  } catch (e) {
    text.textContent = "v0.7.9";
    dot.title = "Version check failed";
  }

  setInterval(async () => {
    try {
      const update = await api('/updates/check');
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
  initAPIKey();
  startStatusPolling();
  loadVersion();
  startRefresh();
  
  // Add window select change handler
  const windowSelect = $('windowSelect');
  if (windowSelect) {
    windowSelect.addEventListener('change', loadRequests);
  }
  
  // Add test button
  const testButton = document.createElement('button');
  testButton.textContent = '🧪 Test API';
  testButton.style.cssText = 'position:fixed;top:10px;left:10px;z-index:10000;background:red;color:white;padding:10px;border:none;border-radius:5px;cursor:pointer;';
  testButton.onclick = testAPI;
  document.body.appendChild(testButton);
  
  // Run initial API test
  setTimeout(() => {
    console.log('🔍 Running initial API test...');
    testAPI();
  }, 1000);
  
  // Force update dashboard with real data
  setTimeout(async () => {
    console.log('🔧 Force updating dashboard...');
    try {
      // Test all three APIs and log raw responses
      console.log('📡 Testing /v1/metrics...');
      const metricsResponse = await fetch('http://localhost:8080/v1/metrics', {
        headers: { 'Authorization': 'Bearer TEST_KEY' }
      });
      const metrics = await metricsResponse.json();
      console.log('📊 Raw /v1/metrics response:', JSON.stringify(metrics, null, 2));
      
      console.log('📡 Testing /v1/system...');
      const systemResponse = await fetch('http://localhost:8080/v1/system', {
        headers: { 'Authorization': 'Bearer TEST_KEY' }
      });
      const system = await systemResponse.json();
      console.log('📊 Raw /v1/system response:', JSON.stringify(system, null, 2));
      
      console.log('📡 Testing /v1/api/requests...');
      const requestsResponse = await fetch('http://localhost:8080/v1/api/requests?limit=50&window=15m', {
        headers: { 'Authorization': 'Bearer TEST_KEY' }
      });
      const requests = await requestsResponse.json();
      console.log('📊 Raw /v1/api/requests response:', JSON.stringify(requests, null, 2));
      
      // Use normalization utilities
      const normalizedMetrics = normalizeMetrics(metrics);
      const normalizedRequests = normalizeRequests(requests);
      
      const normalizedData = {
        queueLag: normalizedMetrics.queueLag,
        avgRisk: normalizedMetrics.avgRisk,
        threatMatches: normalizedMetrics.threatMatches,
        errorRate: normalizedMetrics.errorRate,
        requestCount: normalizedRequests.length,
        totalRequests: requests.total || 0,
        succeeded: requests.succeeded || 0,
        failed: requests.failed || 0,
        avgLatency: requests.avg_latency_ms || 0
      };
      
      console.log('🔧 Normalized data:', normalizedData);
      
      // Update the dashboard cards with normalized data
      const queueLag = document.getElementById('queue-lag');
      const avgRisk = document.getElementById('avg-risk');
      const threatMatches = document.getElementById('threat-matches');
      const errorRate = document.getElementById('error-rate');
      
      if (queueLag) {
        queueLag.textContent = normalizedData.queueLag || '0';
        console.log('✅ Updated queue-lag:', normalizedData.queueLag || '0');
      } else {
        console.log('❌ queue-lag element not found');
      }
      
      if (avgRisk) {
        avgRisk.textContent = normalizedData.avgRisk ? normalizedData.avgRisk.toFixed(1) : '0.0';
        console.log('✅ Updated avg-risk:', normalizedData.avgRisk ? normalizedData.avgRisk.toFixed(1) : '0.0');
      } else {
        console.log('❌ avg-risk element not found');
      }
      
      if (threatMatches) {
        threatMatches.textContent = normalizedData.threatMatches || '0';
        console.log('✅ Updated threat-matches:', normalizedData.threatMatches || '0');
      } else {
        console.log('❌ threat-matches element not found');
      }
      
      if (errorRate) {
        errorRate.textContent = normalizedData.errorRate ? normalizedData.errorRate.toFixed(1) : '0.0';
        console.log('✅ Updated error-rate:', normalizedData.errorRate ? normalizedData.errorRate.toFixed(1) : '0.0');
      } else {
        console.log('❌ error-rate element not found');
      }
      
      // Also update the summary cards if they exist
      const kpiRequests = document.getElementById('kpi-requests');
      const kpiLatency = document.getElementById('kpi-latency');
      const kpiClients = document.getElementById('kpi-clients');
      
      if (kpiRequests) {
        kpiRequests.textContent = normalizedData.requestCount || '0';
        console.log('✅ Updated kpi-requests:', normalizedData.requestCount || '0');
      }
      
      if (kpiLatency) {
        kpiLatency.textContent = normalizedData.avgLatency ? `${Math.round(normalizedData.avgLatency)}ms` : '0ms';
        console.log('✅ Updated kpi-latency:', normalizedData.avgLatency ? `${Math.round(normalizedData.avgLatency)}ms` : '0ms');
      }
      
      if (kpiClients) {
        kpiClients.textContent = '1'; // Default to 1 client
        console.log('✅ Updated kpi-clients: 1');
      }
      
      console.log('✅ Dashboard updated with real data!');
    } catch (error) {
      console.error('❌ Force update failed:', error);
    }
  }, 2000);
  
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
