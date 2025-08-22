// Modern Telemetry Dashboard - Vanilla JavaScript with Tailwind CSS
console.log('app.js loaded');

// --- Early key bootstrap from URL fragment or query, then scrub URL ---
(function bootstrapKeyOnce() {
  try {
    const url = new URL(window.location.href);
    const hashParams = new URLSearchParams(url.hash.startsWith('#') ? url.hash.slice(1) : url.hash);
    const fromHash = hashParams.get('key');
    const fromQuery = url.searchParams.get('key');
    const k = (fromHash || fromQuery || '').trim();
    if (k) {
      localStorage.setItem('telemetry_api_key', k);
      url.searchParams.delete('key');
      hashParams.delete('key');
      const clean = url.pathname + (url.searchParams.toString() ? ('?' + url.searchParams.toString()) : '') + (hashParams.toString() ? ('#' + hashParams.toString()) : '');
      history.replaceState({}, document.title, clean);
    }
  } catch (_) {}
})();

// ---------- VALIDATION HELPERS ----------
function requireKeys(obj, keys, path = '') {
  const missing = [];
  for (const k of keys) {
    if (!(k in obj) || obj[k] === undefined || obj[k] === null || (typeof obj[k] === 'string' && obj[k].trim() === '')) {
      missing.push(path ? `${path}.${k}` : k);
    }
  }
  return missing;
}

function isNumberLike(v) {
  return typeof v === 'number' || (typeof v === 'string' && v.trim() !== '' && !isNaN(Number(v)));
}

// Minimal validators for MVP formats
function validateFlowsV1Record(r, idx) {
  const missing = requireKeys(r, ['ts','src_ip','dst_ip','src_port','dst_port','proto','bytes'], `records[${idx}]`);
  const typeErr = [];
  if (missing.length) return { ok:false, msg:`Missing fields: ${missing.join(', ')}` };
  if (!isNumberLike(r.ts)) typeErr.push(`records[${idx}].ts must be number (epoch seconds)`);
  if (!isNumberLike(r.src_port)) typeErr.push(`records[${idx}].src_port must be number`);
  if (!isNumberLike(r.dst_port)) typeErr.push(`records[${idx}].dst_port must be number`);
  if (!isNumberLike(r.bytes))    typeErr.push(`records[${idx}].bytes must be number`);
  if (!['tcp','udp','icmp','other'].includes(String(r.proto).toLowerCase())) {
    typeErr.push(`records[${idx}].proto must be one of tcp|udp|icmp|other`);
  }
  return typeErr.length ? { ok:false, msg:typeErr.join('; ') } : { ok:true };
}

function validateZeekConnRecord(r, idx) {
  // Keep it pragmatic for MVP; Zeek has many optional fields
  const missing = requireKeys(r, ['ts','uid','id.orig_h','id.resp_h','id.orig_p','id.resp_p','proto'], `records[${idx}]`);
  if (missing.length) return { ok:false, msg:`Missing fields: ${missing.join(', ')}` };
  const typeErr = [];
  if (!isNumberLike(r.ts)) typeErr.push(`records[${idx}].ts must be number (epoch seconds)`);
  if (!isNumberLike(r['id.orig_p'])) typeErr.push(`records[${idx}]['id.orig_p'] must be number`);
  if (!isNumberLike(r['id.resp_p'])) typeErr.push(`records[${idx}]['id.resp_p'] must be number`);
  return typeErr.length ? { ok:false, msg:typeErr.join('; ') } : { ok:true };
}

function validateIngestBody(body) {
  const rootMissing = requireKeys(body, ['collector_id','format','records']);
  if (rootMissing.length) return { ok:false, msg:`Missing fields: ${rootMissing.join(', ')}` };
  if (!Array.isArray(body.records) || body.records.length === 0) {
    return { ok:false, msg:`"records" must be a non-empty array` };
  }

  const fmt = String(body.format).toLowerCase();
  for (let i=0;i<body.records.length;i++){
    const r = body.records[i];
    if (fmt === 'flows.v1') {
      const res = validateFlowsV1Record(r, i); if (!res.ok) return res;
    } else if (fmt === 'zeek.conn') {
      const res = validateZeekConnRecord(r, i); if (!res.ok) return res;
    } else {
      return { ok:false, msg:`Unsupported format "${body.format}". Try "flows.v1" or "zeek.conn".` };
    }
  }
  return { ok:true };
}

// ---------- SAMPLE PAYLOADS ----------
function sampleFlowsV1() {
  const now = Math.floor(Date.now()/1000);
  return {
    collector_id: "tester",
    format: "flows.v1",
    records: [{
      ts: now + 0.123,
      src_ip: "10.0.0.5",
      dst_ip: "1.1.1.1",
      src_port: 51514,
      dst_port: 53,
      proto: "udp",
      bytes: 1200
    },{
      ts: now + 1.234,
      src_ip: "10.0.0.5",
      dst_ip: "142.250.74.36",
      src_port: 51514,
      dst_port: 443,
      proto: "tcp",
      bytes: 4820
    }]
  };
}

function sampleZeekConn() {
  const now = Math.floor(Date.now()/1000);
  return {
    collector_id: "tester",
    format: "zeek.conn",
    records: [{
      ts: now + 0.456,
      uid: "Ckvb3W1H1xZ",
      "id.orig_h": "10.0.0.8",
      "id.resp_h": "8.8.8.8",
      "id.orig_p": 54321,
      "id.resp_p": 53,
      proto: "udp",
      service: "dns",
      duration: 0.002,
      orig_bytes: 76,
      resp_bytes: 128
    }]
  };
}

// UI helpers for sample insertion
function insertSampleFlows() {
  const ta = document.getElementById('ingest-payload');
  if (ta) ta.value = JSON.stringify(sampleFlowsV1(), null, 2);
}
function insertSampleZeek() {
  const ta = document.getElementById('ingest-payload');
  if (ta) ta.value = JSON.stringify(sampleZeekConn(), null, 2);
}

// --- New helpers for the output box ---
function setOutput(textOrObj) {
  const out = document.querySelector('#api-output');
  if (!out) return;
  if (typeof textOrObj === 'string') {
    out.textContent = textOrObj;
  } else {
    out.textContent = JSON.stringify(textOrObj, null, 2);
  }
}
function appendOutputLine(line) {
  const out = document.querySelector('#api-output');
  if (!out) return;
  out.textContent += (out.textContent ? '\n' : '') + line;
}
function clearOutput() { setOutput(''); }
function copyOutput() {
  const out = document.querySelector('#api-output');
  if (!out) return;
  navigator.clipboard.writeText(out.textContent || '').catch(()=>{});
}

// ---------- TOASTS ----------
function showToast(type, message, title = null, timeoutMs = 4200) {
  const root = document.getElementById('toast-root');
  if (!root) return console[type === 'error' ? 'error' : 'log'](message);

  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `
    ${title ? `<span class="title">${escapeHtml(title)}</span>` : ''}
    <span class="msg">${escapeHtml(String(message))}</span>
    <button class="close" aria-label="Close">×</button>
  `;
  const remove = () => el.parentNode && el.parentNode.removeChild(el);
  el.querySelector('.close').addEventListener('click', remove);
  root.appendChild(el);
  if (timeoutMs) setTimeout(remove, timeoutMs);
}

// ---------- LOADING STATE ----------
function setLoading(btn, loading = true) {
  if (!btn) return;
  if (loading) {
    btn.setAttribute('aria-busy', 'true');
    btn.setAttribute('disabled', 'true');
  } else {
    btn.removeAttribute('aria-busy');
    btn.removeAttribute('disabled');
  }
}

// ---------- UTILITY FUNCTIONS ----------
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function clearError(panel) {
  const errorEl = document.getElementById(`${panel}-error`);
  if (errorEl) {
    errorEl.classList.add('hidden');
  }
}

function showError(panel, message) {
  const errorEl = document.getElementById(`${panel}-error`);
  if (errorEl) {
    errorEl.innerHTML = `<div>${escapeHtml(message)}</div>`;
    errorEl.classList.remove('hidden');
  }
}

function showWarmingUp(detail = "database not ready") {
  const dashboardEl = document.getElementById('dashboard-panel');
  if (dashboardEl) {
    const warmingEl = document.getElementById('warming-up-banner');
    if (warmingEl) {
      warmingEl.innerHTML = `<div class="bg-blue-500/20 border border-blue-500/30 text-blue-300 px-4 py-2 rounded-lg text-sm">
        <span class="animate-pulse">🔄</span> Warming up... ${escapeHtml(detail)}
      </div>`;
      warmingEl.classList.remove('hidden');
    }
  }
}

// --- Lookup action (/v1/lookup?q=...) ---
async function doLookup() {
  clearError('api');
  const qInput = document.querySelector('#lookup-value');
  const btn = document.querySelector('#btn-lookup');
  const qv = (qInput?.value || '').trim();
  if (!qv) { 
    showError('api','Enter a value to look up (IP, domain, hash, etc.)'); 
    showToast('info','Enter a value to look up'); 
    return; 
  }

  setLoading(btn, true);
  try {
    // If your API expects ?q=, keep as-is. If it expects JSON body, switch to POST.
    const { resp, data, text } = await apiCall(`/v1/lookup?q=${encodeURIComponent(qv)}`, {}, 'api');

    if (!resp.ok) {
      const snippet = (text || JSON.stringify(data || {})).slice(0, 500);
      throw new Error(`Lookup failed (HTTP ${resp.status}): ${snippet}`);
    }

    setOutput(data ?? { raw: text || 'No body' });
    showToast('success', `Lookup OK: ${qv}`, '/v1/lookup');
  } catch (e) {
    showError('api', e.message);
    showToast('error', e.message, '/v1/lookup failed');
  } finally {
    setLoading(btn, false);
  }
}

// ===== API KEY STATE (single source of truth) =====
const KEY_STORAGE = 'telemetry_api_key';

function maskKey(k) {
  if (!k) return '—';
  if (k.length <= 6) return k;
  return `${k.slice(0,3)}…${k.slice(-3)}`;
}

function   getApiKey() {
    const urlKey = new URLSearchParams(window.location.search).get('key');
    if (urlKey && urlKey.trim()) {
      localStorage.setItem(KEY_STORAGE, urlKey.trim());
      return urlKey.trim();
    }
    const stored = localStorage.getItem(KEY_STORAGE);
    return (stored && stored.trim()) || '';
  }

function setApiKey(k) {
  if (!k || !k.trim()) return;
  localStorage.setItem(KEY_STORAGE, k.trim());
  // notify all listeners (other tabs/pages) to refresh UI/client
  window.dispatchEvent(new CustomEvent('api-key-changed', { detail: { key: k.trim() }}));
}

// --- Auth/key helpers & resiliency ---
function promptForKey(msg = 'Unauthorized') {
  try {
    const proposed = getApiKey();
    const k = window.prompt(`API key required (${msg}). Paste key:`, proposed || '');
    if (k && k.trim()) {
      const trimmed = k.trim();
      setApiKey(trimmed);
      // Reload with ?key to propagate across code paths and tabs
      const url = new URL(window.location.href);
      url.searchParams.set('key', trimmed);
      window.location.replace(url.toString());
    }
  } catch (_) {}
}

function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }
async function withBackoff(fn, {retries=2, base=400}={}) {
  let err;
  for (let i=0;i<=retries;i++) {
    try { return await fn(); }
    catch(e){ err=e; if(i===retries) break; await sleep(base*Math.pow(2,i)); }
  }
  throw err;
}

// Update all visible key chips/badges
function refreshKeyChips() {
  const k = getApiKey();
  // API Tools chip
  const m = document.getElementById('api-key-mask');
  if (m) m.textContent = maskKey(k);
  // If your API client caches the key, update it here as well
  // e.g. window.API_CLIENT.setKey(k);
}

// ===== Set API Key Modal =====
function openKeyModal() {
  const modal = document.getElementById('key-modal');
  const input = document.getElementById('key-modal-input');
  const status = document.getElementById('key-modal-status');
  if (!modal || !input || !status) return;
  input.value = getApiKey();
  status.textContent = '';
  modal.classList.remove('hidden');
  setTimeout(() => input.focus(), 0);
}

function closeKeyModal() {
  const modal = document.getElementById('key-modal');
  if (modal) modal.classList.add('hidden');
}

async function testEnteredKey() {
  const input = document.getElementById('key-modal-input');
  const status = document.getElementById('key-modal-status');
  if (!input || !status) return;
  const key = (input.value || '').trim();
  if (!key) { status.textContent = 'Enter a key to test.'; return; }
  status.textContent = 'Testing…';
  try {
    const base = (window.telemetryDashboard && window.telemetryDashboard.apiBase) || window.location.origin;
    const resp = await fetch(`${base}/v1/system`, { headers: { 'Authorization': `Bearer ${key}` }});
    if (resp.ok) {
      status.textContent = '✓ Valid key. Saved.';
      setApiKey(key);
      refreshKeyChips();
      setTimeout(() => closeKeyModal(), 500);
    } else if (resp.status === 401 || resp.status === 403) {
      status.textContent = 'Invalid key (401/403). You can still Save to store it.';
    } else {
      status.textContent = `Test failed: HTTP ${resp.status}`;
    }
  } catch (e) {
    status.textContent = `Test error: ${e.message}`;
  }
}

function saveEnteredKey() {
  const input = document.getElementById('key-modal-input');
  const status = document.getElementById('key-modal-status');
  if (!input) return;
  const key = (input.value || '').trim();
  if (!key) { if (status) status.textContent = 'Key is empty.'; return; }
  setApiKey(key);
  refreshKeyChips();
  if (status) status.textContent = 'Saved.';
  setTimeout(() => closeKeyModal(), 300);
}

// ===== Inline API Key Editing =====
function initKeyPopover() {
  const container = document.getElementById('api-key-container');
  const display   = document.getElementById('api-key-display');
  const edit      = document.getElementById('api-key-edit');
  const input     = document.getElementById('api-key-input');
  const btnSave   = document.getElementById('api-key-save');
  const btnCan    = document.getElementById('api-key-cancel');

  if (!container || !display || !edit || !input || !btnSave || !btnCan) return;

  const open = () => {
    input.value = getApiKey();
    display.classList.add('hidden');
    edit.classList.remove('hidden');
    setTimeout(()=> input.focus(), 0);
  };
  const close = () => {
    display.classList.remove('hidden');
    edit.classList.add('hidden');
  };

  // Click on display mode to edit
  display.addEventListener('click', open);
  
  // Save button
  btnSave.addEventListener('click', () => {
    const val = input.value.trim();
    if (!val) return;
    setApiKey(val);
    refreshKeyChips();
    close();
    showToast?.('success', 'API key updated.');
  });

  // Cancel button
  btnCan.addEventListener('click', close);

  // Close on Esc
  document.addEventListener('keydown', (e)=>{ 
    if (e.key === 'Escape') close(); 
  });
}

// ===== Keep network client in sync on change =====
window.addEventListener('api-key-changed', (e) => {
  const k = e.detail?.key || getApiKey();
  // Update your API client (if using a wrapper)
  window.API_KEY = k; // if your apiCall() reads from this variable/localStorage
  refreshKeyChips();
  
  // Refresh requests data when API key changes
  if (window.telemetryDashboard) {
    window.telemetryDashboard.loadRequestsData();
  }
});



// === VEFIX: make handlers global so buttons can call them ===
window.openSourceDetails = async function (sourceId, mode = 'edit') {
  console.log('[UI] openSourceDetails', { sourceId, mode });
  try {
    const res = await fetch(`/v1/sources/${encodeURIComponent(sourceId)}`, { 
      headers: { 'Authorization': `Bearer ${getApiKey()}` }
    });
    if (!res.ok) throw new Error(`GET /v1/sources/${sourceId} -> ${res.status}`);
    const src = await res.json();
    // Always use our drawer
    window.showSourceDrawer(src, mode);
  } catch (e) {
    console.error('openSourceDetails failed', e);
    alert('Failed to open source (see console).');
  }
};

window.editSource = (sourceId) => window.openSourceDetails(sourceId, 'edit');

window.deleteSource = async function (sourceId) {
  console.log('[UI] deleteSource', { sourceId });
  
  // Show custom delete modal
  const backdrop = document.getElementById('delete-modal-backdrop');
  const modal = document.getElementById('delete-modal');
  const sourceName = document.getElementById('delete-source-name');
  
  if (!backdrop || !modal || !sourceName) {
    console.warn('[UI] delete modal elements missing');
    return;
  }
  
  // Set the source name in the modal
  sourceName.textContent = sourceId;
  
  // Show modal
  backdrop.classList.remove('hidden');
  modal.classList.remove('hidden');
  
  // Wire up the buttons
  const cancelBtn = document.getElementById('delete-modal-cancel');
  const confirmBtn = document.getElementById('delete-modal-confirm');
  
  const closeModal = () => {
    backdrop.classList.add('hidden');
    modal.classList.add('hidden');
  };
  
  const performDelete = async () => {
    try {
      closeModal();
      
      // Use the existing dashboard API call method if available
      if (window.telemetryDashboard?.apiCall) {
        await window.telemetryDashboard.apiCall(`/sources/${sourceId}`, { method: 'DELETE' });
        // Refresh the sources table
        if (window.telemetryDashboard?.loadSourcesData) {
          await window.telemetryDashboard.loadSourcesData();
        } else {
          location.reload();
        }
      } else {
        // Fallback: use the existing dashboard method directly
        if (window.telemetryDashboard?.deleteSource) {
          await window.telemetryDashboard.deleteSource(sourceId);
        } else {
          alert('Dashboard not available.');
        }
      }
    } catch (e) {
      console.error('deleteSource failed', e);
      alert('Delete failed (see console).');
    }
  };
  
  // Remove any existing listeners
  cancelBtn.replaceWith(cancelBtn.cloneNode(true));
  confirmBtn.replaceWith(confirmBtn.cloneNode(true));
  
  // Add new listeners
  document.getElementById('delete-modal-cancel').addEventListener('click', closeModal);
  document.getElementById('delete-modal-confirm').addEventListener('click', performDelete);
  
  // Close on backdrop click
  backdrop.addEventListener('click', (e) => {
    if (e.target === backdrop) closeModal();
  });
  
  // Close on ESC
  const escHandler = (e) => {
    if (e.key === 'Escape') {
      closeModal();
      document.removeEventListener('keydown', escHandler);
    }
  };
  document.addEventListener('keydown', escHandler);
};

// Add My IP functionality (defined before DOM ready)
async function addMyIpToAllowlist() {
    try {
        // Try backend helper first
        let ip;
        try {
            const response = await fetch('/v1/v1/utils/client-ip', { 
                headers: { 'Authorization': `Bearer ${getApiKey()}` }
            });
            if (response.ok) {
                const data = await response.json();
                ip = data.client_ip;
            }
        } catch (e) {
            console.log('Backend helper failed, trying fallback');
        }

        // Fallback to ipify if backend helper isn't available
        if (!ip) {
            try {
                const response = await fetch('https://api.ipify.org?format=json');
                const data = await response.json();
                ip = data.ip;
            } catch (e) {
                console.log('ipify fallback failed');
            }
        }

        if (!ip) {
            window.telemetryDashboard.showToast('Could not determine your IP', 'error');
            return;
        }

        const cidr = `${ip}/32`;
        
        // Add to the UI list
        const container = document.getElementById('allowed-ips-container');
        if (container) {
            // Check if already exists
            const existingChips = Array.from(container.children);
            const alreadyExists = existingChips.some(chip => 
                chip.querySelector('span').textContent === cidr
            );
            
            if (!alreadyExists) {
                // Create new chip
                const chip = document.createElement('div');
                chip.className = 'inline-flex items-center gap-2 px-3 py-1 bg-[#0F1116] text-zinc-300 rounded-lg text-sm';
                chip.innerHTML = `
                    <span>${cidr}</span>
                    <button onclick="this.parentElement.remove()" class="text-zinc-500 hover:text-red-400">×</button>
                `;
                container.appendChild(chip);
                
                window.telemetryDashboard.showToast(`Added ${cidr}`, 'success');
            } else {
                window.telemetryDashboard.showToast(`${cidr} already present`, 'info');
            }
        }
    } catch (error) {
        window.telemetryDashboard.showToast('Add My IP failed', 'error');
        console.error('Add My IP error:', error);
    }
}

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM ready, initializing dashboard...');
    
    refreshKeyChips();
    initKeyPopover();

    // Wire Set API Key modal controls
    const btnOpen = document.getElementById('btn-set-key');
    const btnClose = document.getElementById('key-modal-close');
    const btnCancel = document.getElementById('key-modal-cancel');
    const btnTest = document.getElementById('key-modal-test');
    const btnSave = document.getElementById('key-modal-save');
    const backdrop = document.getElementById('key-modal-backdrop');
    if (btnOpen) btnOpen.addEventListener('click', openKeyModal);
    if (btnClose) btnClose.addEventListener('click', closeKeyModal);
    if (btnCancel) btnCancel.addEventListener('click', closeKeyModal);
    if (backdrop) backdrop.addEventListener('click', closeKeyModal);
    if (btnTest) btnTest.addEventListener('click', testEnteredKey);
    if (btnSave) btnSave.addEventListener('click', saveEnteredKey);



    // Wire Add My IP button
    const addMyIpBtn = document.getElementById('btn-add-my-ip');
    if (addMyIpBtn) addMyIpBtn.addEventListener('click', addMyIpToAllowlist);

    // Ensure your apiCall() uses latest key:
    // In apiCall(), read from localStorage each time or from window.API_KEY
    window.API_KEY = getApiKey();
    
    // Create dashboard instance and make it globally accessible
    window.telemetryDashboard = new TelemetryDashboard();
    
    // === VEFIX: event delegation so re-renders don't break clicks ===
    document.addEventListener('click', function (e) {
      console.log('[vefix] Click event detected on:', e.target);
      const el = e.target.closest?.('[data-action]');
      console.log('[vefix] Closest data-action element:', el);
      if (!el) return;
      e.preventDefault();
      e.stopPropagation(); // prevents overlays swallowing the event
      const { action, id } = el.dataset || {};
      console.log('[vefix] Action and ID:', { action, id });
      
      if (action === 'add-source') {
        window.openCreateSourceDrawer();
        return;
      }
      
      if (!id) return console.warn('[vefix] missing data-id on action button');
      if (action === 'edit')   return window.openSourceDetails(id, 'edit');
      if (action === 'delete') return window.deleteSource(id);
    }, true);

// === Drawer controller ===
const _$ = (sel) => document.querySelector(sel);
function renderSourceSummary(src, mode){
  const ips = (() => {
    try { return JSON.parse(src.allowed_ips||'[]'); } catch { return []; }
  })();
  
  if (mode === 'view') {
    return `
      <div class="space-y-2">
        <div class="text-xs text-white/60">Mode: <span class="text-white">${mode}</span></div>
        <div><span class="text-white/70">ID:</span> ${src.id}</div>
        <div><span class="text-white/70">Display Name:</span> ${src.display_name||'-'}</div>
        <div><span class="text-white/70">Type:</span> ${src.type}</div>
        <div><span class="text-white/70">Tenant:</span> ${src.tenant_id}</div>
        <div><span class="text-white/70">Collector:</span> ${src.collector}</div>
        <div><span class="text-white/70">Status:</span> ${src.status}</div>
        <div><span class="text-white/70">Allowed IPs:</span> ${ips.length} ${ips.length ? `(${ips.join(', ')})` : ''}</div>
        <div><span class="text-white/70">Max EPS:</span> ${src.max_eps ?? 0}</div>
      </div>
      <div class="pt-4 flex gap-2">
        <button id="drawer-edit-btn" class="px-3 py-1 bg-white/10 hover:bg-white/20 rounded">Edit</button>
        <button id="drawer-close-btn" class="px-3 py-1 bg-white/5 hover:bg-white/10 rounded">Close</button>
      </div>
    `;
  } else {
    // Edit mode - show form fields
    return `
      <form id="edit-src-form" class="p-6 space-y-4 pb-28" onsubmit="return window.submitEditSource(event)">
        <div>
          <label class="text-sm text-white/70">Source ID</label>
          <input id="edit-src-id" value="${src.id}" readonly
                 class="mt-1 w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 outline-none focus:border-blue-500"/>
        </div>

        <div>
          <label class="text-sm text-white/70">Display Name</label>
          <input id="edit-src-display" value="${src.display_name || ''}" placeholder="Human-readable name"
                 class="mt-1 w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 outline-none focus:border-blue-500"/>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-sm text-white/70">Tenant</label>
            <input id="edit-src-tenant" value="${src.tenant_id}"
                   class="mt-1 w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 outline-none focus:border-blue-500"/>
          </div>
          <div>
            <label class="text-sm text-white/70">Type</label>
            <input id="edit-src-type" value="${src.type}" placeholder="e.g., cisco_asa / test"
                   class="mt-1 w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 outline-none focus:border-blue-500"/>
          </div>
        </div>

        <div>
          <label class="text-sm text-white/70">Collector</label>
          <input id="edit-src-collector" value="${src.collector}" placeholder="e.g., gw-local"
                 class="mt-1 w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 outline-none focus:border-blue-500"/>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-sm text-white/70">Status</label>
            <select id="edit-src-status"
                    class="mt-1 w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 outline-none focus:border-blue-500">
              <option value="enabled" ${src.status === 'enabled' ? 'selected' : ''}>Enabled</option>
              <option value="disabled" ${src.status === 'disabled' ? 'selected' : ''}>Disabled</option>
            </select>
          </div>
          <div>
            <label class="text-sm text-white/70">Max EPS (0 = unlimited)</label>
            <input id="edit-src-maxeps" type="number" min="0" value="${src.max_eps ?? 0}"
                   class="mt-1 w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 outline-none focus:border-blue-500"/>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <input id="edit-src-block" type="checkbox" class="accent-blue-500" ${src.block_on_exceed ? 'checked' : ''}>
          <label class="text-sm text-white/80">Block on exceed</label>
        </div>

        <div>
          <label class="text-sm text-white/70">Allowed IPs (CIDRs, one per line)</label>
          <textarea id="edit-src-ips" rows="4" placeholder="127.0.0.1/32&#10;203.0.113.0/24"
                    class="mt-1 w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 outline-none focus:border-blue-500">${ips.join('\n')}</textarea>
          <p class="mt-1 text-xs text-white/50">Leave empty to block all (whitelist-only).</p>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-end gap-3 sticky bottom-0 bg-[#0f1115]/90 backdrop-blur border-t border-white/10 px-6 py-4">
          <button type="button" onclick="window.hideSourceDrawer()" class="btn-secondary">
            Cancel
          </button>
          <button type="submit" class="btn-primary-glow">
            Save Changes
          </button>
        </div>
      </form>
    `;
  }
}

window.showSourceDrawer = function(src, mode='view'){
  const backdrop = _$('#drawer-backdrop');
  const drawer   = _$('#source-drawer');
  const title    = _$('#drawer-title');
  const body     = _$('#drawer-content');
  if (!backdrop || !drawer || !title || !body) {
    console.warn('[drawer] elements missing');
    return alert('Drawer elements missing from HTML.');
  }
  title.textContent = `Edit: ${src.display_name || src.id}`;
  body.innerHTML = renderSourceSummary(src, mode);
  // open
  backdrop.classList.remove('hidden');
  drawer.classList.remove('translate-x-full');
  // wire close/edit buttons inside
  _$('#drawer-close').onclick = window.hideSourceDrawer;
  _$('#drawer-close-btn')?.addEventListener('click', window.hideSourceDrawer);
  _$('#drawer-edit-btn')?.addEventListener('click', () => window.openSourceDetails(src.id, 'edit'));
  // backdrop click closes
  backdrop.onclick = (e) => { if (e.target === backdrop) window.hideSourceDrawer(); };
};

window.hideSourceDrawer = function(){
  const backdrop = _$('#drawer-backdrop');
  const drawer   = _$('#source-drawer');
  if (backdrop) backdrop.classList.add('hidden');
  if (drawer)   drawer.classList.add('translate-x-full');
};

// ESC to close
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') window.hideSourceDrawer();
});

// --- Create Source drawer controls ---
window.openCreateSourceDrawer = function () {
  const d = document.getElementById('create-src-drawer');
  const b = document.getElementById('create-src-backdrop');
  if (!d || !b) return console.warn('[UI] create drawer missing');
  d.classList.remove('hidden');
  b.classList.remove('hidden');
  // start translated -> slide in
  requestAnimationFrame(() => {
    d.classList.remove('translate-x-full');
  });
  // autofocus first field
  setTimeout(() => document.getElementById('create-src-id')?.focus(), 50);

  // initialize type toggles
  const help = document.getElementById('create-src-type-help');
  const ipsBlock = document.getElementById('create-src-ips-block');
  const toApi = () => { help.classList.remove('hidden'); ipsBlock.classList.add('hidden'); };
  const toUdp = () => { help.classList.add('hidden'); ipsBlock.classList.remove('hidden'); };
  const apiRadio = document.getElementById('create-src-type-api');
  const udpRadio = document.getElementById('create-src-type-udp');
  if (apiRadio && udpRadio) {
    // default to API
    apiRadio.checked = true; toApi();
    apiRadio.onchange = toApi;
    udpRadio.onchange = toUdp;
  }
};

window.closeCreateSourceDrawer = function () {
  const d = document.getElementById('create-src-drawer');
  const b = document.getElementById('create-src-backdrop');
  if (!d || !b) return;
  d.classList.add('translate-x-full');
  setTimeout(() => {
    d.classList.add('hidden');
    b.classList.add('hidden');
  }, 180);
};

// ESC closes
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') window.closeCreateSourceDrawer();
});

// Submit handler
window.submitCreateSource = async function (evt) {
  evt.preventDefault();
  
  // Check feature flag first
  if (!(window.FEATURES && window.FEATURES.sources === true)) {
    showToast('error', 'Source management is not available in this build.');
    return false;
  }
  
  try {
    const id        = document.getElementById('create-src-id').value.trim();
    const display   = document.getElementById('create-src-display').value.trim();
    const tenant    = document.getElementById('create-src-tenant').value.trim() || 'default';
    const typeRadio = document.querySelector('input[name="create-src-type"]:checked');
    const type      = (typeRadio?.value || 'http').trim();
    const collector = document.getElementById('create-src-collector').value.trim() || 'gw-local';
    const status    = document.getElementById('create-src-status').value;
    const max_eps   = parseInt(document.getElementById('create-src-maxeps').value || '0', 10);
    const block     = document.getElementById('create-src-block').checked;
    const ipsRaw    = document.getElementById('create-src-ips').value.trim();

    // API expects stringified JSON for allowed_ips (backward-compat)
    const ipsArray = ipsRaw
      ? ipsRaw.split('\n').map(s => s.trim()).filter(Boolean)
      : [];
    const allowed_ips = JSON.stringify(ipsArray);

    const payload = {
      id, tenant_id: tenant, type,
      display_name: display || id,
      collector, status,
      allowed_ips, max_eps, block_on_exceed: block
    };

    const res = await fetch('/v1/sources', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${window.getApiKey?.() || ''}`,
      },
      body: JSON.stringify(payload),
    });

    if (res.status === 501) {
      showToast('error', 'Not implemented in this build.');
      return false;
    }
    
    if (!res.ok) {
      const t = await res.text();
      console.error('[create source] failed', res.status, t);
      showToast('error', `Create failed (${res.status}): ${t}`);
      return false;
    }

    // success: close drawer, refresh table, and open details in edit mode
    window.closeCreateSourceDrawer();
    
    // Refresh the sources table to show the new source
    if (window.telemetryDashboard?.loadSourcesData) {
      await window.telemetryDashboard.loadSourcesData();
    } else {
      // Fallback: reload the page
      location.reload();
    }
    
    return false;
  } catch (e) {
    console.error(e);
    alert('Unexpected error creating source');
    return false;
  }
};

// Edit Source submit handler
window.submitEditSource = async function (evt) {
  evt.preventDefault();
  try {
    const id        = document.getElementById('edit-src-id').value.trim();
    const display   = document.getElementById('edit-src-display').value.trim();
    const tenant    = document.getElementById('edit-src-tenant').value.trim() || 'default';
    const type      = document.getElementById('edit-src-type').value.trim() || 'test';
    const collector = document.getElementById('edit-src-collector').value.trim() || 'gw-local';
    const status    = document.getElementById('edit-src-status').value;
    const max_eps   = parseInt(document.getElementById('edit-src-maxeps').value || '0', 10);
    const block     = document.getElementById('edit-src-block').checked;
    const ipsRaw    = document.getElementById('edit-src-ips').value.trim();

    // API expects stringified JSON for allowed_ips (backward-compat)
    const ipsArray = ipsRaw
      ? ipsRaw.split('\n').map(s => s.trim()).filter(Boolean)
      : [];
    const allowed_ips = JSON.stringify(ipsArray);

    const payload = {
      display_name: display || id,
      tenant_id: tenant,
      type,
      collector,
      status,
      allowed_ips, 
      max_eps, 
      block_on_exceed: block
    };

    const res = await fetch(`/v1/sources/${encodeURIComponent(id)}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${window.getApiKey?.() || ''}`,
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const t = await res.text();
      console.error('[edit source] failed', res.status, t);
      alert(`Update failed (${res.status}): ${t}`);
      return false;
    }

    // success: close drawer and refresh table
    window.hideSourceDrawer();
    
    // Refresh the sources table to show updated data
    if (window.telemetryDashboard?.loadSourcesData) {
      await window.telemetryDashboard.loadSourcesData();
    } else {
      // Fallback: reload the page
      location.reload();
    }
    return false;
  } catch (e) {
    console.error(e);
    alert('Unexpected error updating source');
    return false;
  }
};
});

class TelemetryDashboard {
    constructor() {
        console.log('TelemetryDashboard constructor called');
        this.apiBase = window.location.origin; // Use the current domain
        this.apiKey = getApiKey();
        this.currentRequestsData = [];
        this.logsEventSource = null;
        this.logsInterval = null;
        this.autoRefreshInterval = null;
        
        console.log('API Base URL:', this.apiBase);
        console.log('API Key:', this.apiKey);
        
        this.init();
    }

    init() {
        console.log('Initializing TelemetryDashboard...');
        this.setupEventListeners();
        this.loadInitialData();
        this.startAutoRefresh();
        console.log('TelemetryDashboard initialized');
    }

    setupEventListeners() {
        // Tab navigation - Fixed event handling
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const tabName = e.target.id.replace('tab-', '');
                console.log('Tab clicked:', tabName);
                this.switchTab(tabName);
            });
        });

        // API KEY input
        const apiKeyPill = document.getElementById('api-key-pill');
        const apiKeyValue = document.getElementById('api-key-value');
        if (apiKeyPill && apiKeyValue) {
            apiKeyValue.textContent = this.apiKey;
            apiKeyPill.addEventListener('click', async () => {
                const val = prompt('Enter API KEY', this.apiKey || '');
                if (val != null) {
                    this.apiKey = val.trim() || 'DEV_ADMIN_KEY_c84a4e33bd';
                    apiKeyValue.textContent = this.apiKey;
                }
            });
        }

        // Dashboard actions
        const refreshBtn = document.getElementById('refresh-requests');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadRequestsData();
            });
        }

        // Logs actions
        const startLogsBtn = document.getElementById('start-logs');
        const stopLogsBtn = document.getElementById('stop-logs');
        const downloadLogsBtn = document.getElementById('download-logs');
        
        if (startLogsBtn) startLogsBtn.addEventListener('click', () => this.startLogs());
        if (stopLogsBtn) stopLogsBtn.addEventListener('click', () => this.stopLogs());
        if (downloadLogsBtn) downloadLogsBtn.addEventListener('click', () => this.downloadLogs());

        // API actions
        const btnSystem = document.getElementById('btn-system');
        const btnMetrics = document.getElementById('btn-metrics');
        const btnSendIngest = document.getElementById('btn-send-ingest');
        const btnLookup = document.getElementById('btn-lookup');
        const btnCopyOutput = document.getElementById('btn-copy-output');
        const btnClearOutput = document.getElementById('btn-clear-output');
        
        console.log('API buttons found:', {
            btnSystem: !!btnSystem,
            btnMetrics: !!btnMetrics,
            btnSendIngest: !!btnSendIngest,
            btnLookup: !!btnLookup,
            btnCopyOutput: !!btnCopyOutput,
            btnClearOutput: !!btnClearOutput
        });
        
        if (btnSystem) {
            btnSystem.addEventListener('click', () => {
                console.log('System button clicked');
                this.fetchSystem();
            });
        }
        if (btnMetrics) {
            btnMetrics.addEventListener('click', () => {
                console.log('Metrics button clicked');
                this.fetchMetrics();
            });
        }
        if (btnSendIngest) {
            btnSendIngest.addEventListener('click', () => {
                console.log('Send ingest button clicked');
                this.sendIngest();
            });
        }
        if (btnLookup) {
            btnLookup.addEventListener('click', () => {
                console.log('Lookup button clicked');
                doLookup();
            });
        }
        if (btnCopyOutput) {
            btnCopyOutput.addEventListener('click', () => {
                console.log('Copy output button clicked');
                copyOutput();
            });
        }
        if (btnClearOutput) {
            btnClearOutput.addEventListener('click', () => {
                console.log('Clear output button clicked');
                clearOutput();
            });
        }

        // Sample buttons
        const sampleFlowsBtn = document.getElementById('btn-sample-flows');
        const sampleZeekBtn = document.getElementById('btn-sample-zeek');
        
        if (sampleFlowsBtn) {
            sampleFlowsBtn.addEventListener('click', () => {
                console.log('Sample flows button clicked');
                insertSampleFlows();
            });
        }
        if (sampleZeekBtn) {
            sampleZeekBtn.addEventListener('click', () => {
                console.log('Sample zeek button clicked');
                insertSampleZeek();
            });
        }

        // Slide-over
        const closeSlideOverBtn = document.getElementById('close-slide-over');
        const slideOverBackdrop = document.getElementById('slide-over-backdrop');
        
        if (closeSlideOverBtn) closeSlideOverBtn.addEventListener('click', () => this.closeSlideOver());
        if (slideOverBackdrop) slideOverBackdrop.addEventListener('click', () => this.closeSlideOver());

        // ESC key to close slide-over
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeSlideOver();
            }
        });
    }

    switchTab(tabName) {
        console.log('Switching to tab:', tabName);
        
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.className = 'tab-btn px-4 py-2 rounded-2xl text-sm ring-1 bg-[#0F1116] ring-white/5 text-zinc-400 hover:text-zinc-200';
        });
        
        const activeTab = document.getElementById(`tab-${tabName.toLowerCase()}`);
        if (activeTab) {
            activeTab.className = 'tab-btn active px-4 py-2 rounded-2xl text-sm ring-1 bg-[#14151B] ring-indigo-500/40 text-zinc-100';
        }

        // Update panels
        document.querySelectorAll('.panel').forEach(panel => {
            panel.classList.add('hidden');
        });
        
        const targetPanel = document.getElementById(`panel-${tabName.toLowerCase()}`);
        if (targetPanel) {
            targetPanel.classList.remove('hidden');
            console.log('Panel shown:', `panel-${tabName.toLowerCase()}`);
        } else {
            console.error('Panel not found:', `panel-${tabName.toLowerCase()}`);
        }

        // Load data for the selected tab
        if (tabName.toLowerCase() === 'dashboard') {
            this.loadInitialData();
        } else if (tabName.toLowerCase() === 'requests') {
            this.loadRequestsData();
        } else if (tabName.toLowerCase() === 'logs') {
            this.loadInitialLogs();
        } else if (tabName.toLowerCase() === 'sources') {
            this.loadSourcesData();
        }
    }

    async apiCall(endpoint, options = {}) {
        try {
            const url = `${this.apiBase}/v1${endpoint}`;
            const apiKey = getApiKey(); // Read from localStorage at call time
            const headers = {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`,
                ...options.headers
            };

            console.log('API call:', url);
            console.log('Headers:', headers);
            const response = await fetch(url, { ...options, headers });
            console.log('Response status:', response.status);
            console.log('Response headers:', response.headers);
            
            if (!response.ok) {
                if (response.status === 503) {
                    // Handle warming up state
                    const text = await response.text();
                    let detail = "database not ready";
                    try {
                        const json = JSON.parse(text);
                        detail = json.detail || detail;
                    } catch (e) {
                        // Use default detail if JSON parsing fails
                    }
                    this.showWarmingUp?.(detail);
                    throw new Error(`HTTP 503: ${detail}`);
                }
                if (response.status === 401 || response.status === 403) {
                    this.showError?.('dashboard', `HTTP ${response.status}: Unauthorized`);
                    promptForKey(`HTTP ${response.status}`);
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const text = await response.text();
            console.log('Response text length:', text.length);
            console.log('Response text preview:', text.substring(0, 100));
            
            if (!text.trim()) {
                console.log('Empty response received');
                return { message: 'Empty response' };
            }
            
            try {
                const json = JSON.parse(text);
                console.log('JSON parsed successfully');
                return json;
            } catch (parseError) {
                console.error('JSON parse error:', parseError);
                console.error('Raw response:', text);
                return { raw_response: text, parse_error: parseError.message };
            }
        } catch (error) {
            console.error(`API call failed (${endpoint}):`, error);
            throw error;
        }
    }

    async loadInitialData() {
        try {
            console.log('Loading initial data...');
            
            // Initialize error ring with default value
            const errorRing = document.getElementById('error-ring');
            if (errorRing) {
                errorRing.innerHTML = this.createErrorRing(0);
            }
            
            const k = getApiKey();
            if (!k) { this.showError('dashboard','API key required.'); promptForKey('no key found'); return; }
            
            // Load system info first (with backoff for 503)
            let system;
            try {
                system = await withBackoff(() => this.apiCall('/system'), {retries:5, base:1000});
                console.log('System info loaded:', system);
            } catch (error) {
                console.error('Failed to load system info:', error);
                if (error.message.includes('HTTP 503')) {
                    // Don't show error for 503, just keep retrying
                    return;
                }
                system = { version: '0.8.6' }; // Set default version
            }
            
            this.updateSystemInfo(system);
            
            // Apply feature gates based on system info
            this.applyFeatureGates(system?.features || {});
            
            // Start UDP head status polling
            this.loadUdpHeadStatus();
            setInterval(() => this.loadUdpHeadStatus(), 3000);

            // Load metrics (with backoff for 503)
            try {
                const metrics = await withBackoff(() => this.apiCall('/metrics'), {retries:5, base:1000});
                console.log('Metrics loaded:', metrics);
                this.updateDashboardMetrics(metrics);
            } catch (error) {
                console.error('Failed to load metrics:', error);
                if (error.message.includes('HTTP 503')) {
                    // Don't show error for 503, just keep retrying
                    return;
                }
                this.showError('dashboard', error.message);
            }
            
        } catch (error) {
            console.error('Failed to load initial data:', error);
            // Only show error if it's not a 503
            if (!error.message.includes('HTTP 503')) {
                this.showError('dashboard', error.message);
            }
        }
    }

    updateSystemInfo(system) {
        console.log('Updating system info:', system);
        
        // Always display backend version (no hardcode)
        const version = system?.version || 'dev';
        console.log('Version to display:', version);
        
        // Update version in dashboard and system panels
        const versionElement = document.getElementById('version');
        if (versionElement) {
            versionElement.textContent = version;
            versionElement.title = 'Click to open Swagger UI documentation';
        }
        const versionElement2 = document.getElementById('version-system');
        if (versionElement2) versionElement2.textContent = version;

        // Update uptime
        let uptime = '—';
        if (system?.uptime_s) {
            const hours = Math.floor(system.uptime_s / 3600);
            const minutes = Math.floor((system.uptime_s % 3600) / 60);
            uptime = `${hours}h ${minutes}m`;
        }
        
        const uptimeElement = document.getElementById('uptime');
        if (uptimeElement) {
            uptimeElement.textContent = uptime;
        }
        const uptime2 = document.getElementById('uptime-system');
        if (uptime2) uptime2.textContent = uptime;

        // CPU/Memory tiles removed from UI
    }

    applyFeatureGates(features) {
        console.log('Applying feature gates:', features);
        
        // Feature flags (default false if missing)
        const allowSources = features.sources === true;
        
        // Disable Create Source form/button if not enabled
        const form = document.getElementById('form-create-source');
        const btn = document.getElementById('btn-create-source');
        
        if (form) {
            form.addEventListener('submit', (e) => {
                if (!allowSources) {
                    e.preventDefault();
                    this.showToast('error', 'Source management is not available in this build.');
                }
            });
            form.classList.toggle('disabled', !allowSources);
        }
        
        if (btn) {
            btn.disabled = !allowSources;
            if (!allowSources) {
                btn.title = 'Disabled in this build';
                btn.classList.add('opacity-50', 'cursor-not-allowed');
            } else {
                btn.title = '';
                btn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        }
        
        // Store features globally for other functions to access
        window.FEATURES = features;
    }

    async loadUdpHeadStatus() {
        const el = document.querySelector('[data-field="udp-head-status"]');
        if (!el) return;
        try {
            const r = await fetch('http://localhost:8081/health');
            if (!r.ok) throw new Error("bad status");
            const j = await r.json();
            el.textContent = (j.status === 'ok') ? 'Running' : 'Unknown';
        } catch {
            el.textContent = 'Stopped';
        }
    }

    updateDashboardMetrics(metrics) {
        console.log('Updating dashboard metrics:', metrics);
        
        // Queue Lag (p50)
        const queueLag = metrics?.queue?.lag_ms_p50 ?? 0;
        const queueLagElement = document.getElementById('queue-lag');
        if (queueLagElement) {
            queueLagElement.textContent = queueLag;
        }
        
        // Average Risk
        const riskSum = metrics?.totals?.risk_sum ?? 0;
        const riskCount = metrics?.totals?.risk_count ?? 0;
        const avgRisk = riskCount > 0 ? Math.round((riskSum / riskCount) * 10) / 10 : 0;
        const avgRiskElement = document.getElementById('avg-risk');
        if (avgRiskElement) {
            avgRiskElement.textContent = avgRisk;
        }
        
        // Threat Matches
        const threatMatches = metrics?.totals?.threat_matches ?? 0;
        const threatMatchesElement = document.getElementById('threat-matches');
        if (threatMatchesElement) {
            threatMatchesElement.textContent = threatMatches;
        }
        
        // Error Rate
        const totalRequests = metrics?.requests_total ?? 0;
        const failedRequests = metrics?.requests_failed ?? 0;
        const errorRate = totalRequests > 0 ? Math.round((failedRequests / totalRequests) * 100 * 10) / 10 : 0;
        const errorRing = document.getElementById('error-ring');
        if (errorRing) {
            errorRing.innerHTML = this.createErrorRing(errorRate);
        }
        
        console.log('Metrics updated:', {
            queueLag,
            avgRisk,
            threatMatches,
            errorRate: `${errorRate}%`
        });
    }

    async loadRequestsData() {
        try {
            console.log('Loading requests data...');
            
            // Always use /v1/api/requests since it doesn't require admin authentication
            // and works with any valid API key
            let requestsData = null;
            
            try {
                requestsData = await this.apiCall('/api/requests?limit=30');
                console.log('API requests loaded:', requestsData);
            } catch (error) {
                console.error('API requests failed:', error);
                throw error;
            }
            
            if (requestsData && requestsData.items) {
                this.currentRequestsData = requestsData.items;
                this.updateRequestsTable(requestsData.items);
                this.updateRequestsSummary(requestsData.items); // Update summary after loading data
                console.log('Requests table updated with', requestsData.items.length, 'items');
            } else {
                console.log('No requests data found');
                this.currentRequestsData = [];
                this.updateRequestsTable([]);
                this.updateRequestsSummary([]); // Update summary when no data
            }
            
        } catch (error) {
            console.error('Failed to load requests data:', error);
            this.showError('requests', error.message);
            this.currentRequestsData = [];
            this.updateRequestsTable([]);
            this.updateRequestsSummary([]); // Update summary on error
        }
    }

    updateRequestsSummary(requests = []) {
        console.log('Updating requests summary with', requests.length, 'items');
        
        if (requests.length === 0) {
            // Set default values when no data
            const successPercentageElement = document.getElementById('success-percentage');
            const avgLatencyElement = document.getElementById('avg-latency');
            const successRing = document.getElementById('success-ring');
            
            if (successPercentageElement) successPercentageElement.textContent = '0%';
            if (avgLatencyElement) avgLatencyElement.textContent = '0ms';
            if (successRing) successRing.innerHTML = this.createSuccessRing(0);
            return;
        }
        
        // Calculate success rate
        const totalRequests = requests.length;
        const successfulRequests = requests.filter(req => (req.status || 0) < 400).length;
        const successRate = totalRequests > 0 ? Math.round((successfulRequests / totalRequests) * 100 * 10) / 10 : 0;
        
        // Calculate average latency
        const latencies = requests.map(req => req.latency_ms || req.duration_ms || 0).filter(lat => lat > 0);
        const avgLatency = latencies.length > 0 ? Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length) : 0;
        
        // Update success rate percentage
        // remove standalone percentage label; ring shows number
        
        // Update circular progress ring (SVG)
        const successRing = document.getElementById('success-ring');
        if (successRing) successRing.innerHTML = this.createSuccessRing(successRate);
        
        // Update average latency
        const avgLatencyElement = document.getElementById('avg-latency');
        if (avgLatencyElement) {
            avgLatencyElement.textContent = `${avgLatency}ms`;
        }
        
        console.log('Requests summary updated:', { successRate, avgLatency, totalRequests, successfulRequests });
    }

    createSuccessRing(percentage) {
        const size = 80; // smaller to fit the new compact box
        const stroke = 4; // thinner stroke like refresh button
        const radius = (size - stroke) / 2;
        const circumference = 2 * Math.PI * radius;
        const dash = Math.max(0, Math.min(100, percentage)) / 100 * circumference;
        let color = '#ef4444'; // red
        let glowColor = 'rgba(239,68,68,0.6)'; // red glow
        if (percentage >= 90) {
            color = '#22c55e'; // green
            glowColor = 'rgba(34,197,94,0.7)'; // brighter green glow
        } else if (percentage >= 60) {
            color = '#f59e0b'; // amber
            glowColor = 'rgba(245,158,11,0.7)'; // brighter amber glow
        }
        
        return `
          <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" style="display:block;filter:drop-shadow(0 0 8px ${glowColor})">
            <defs>
              <filter id="glow-${Math.round(percentage)}">
                <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                <feMerge> 
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>
            <circle cx="${size/2}" cy="${size/2}" r="${radius}" stroke="rgba(255,255,255,0.08)" stroke-width="${stroke}" fill="none"/>
            <circle cx="${size/2}" cy="${size/2}" r="${radius}" stroke="${color}" stroke-width="${stroke}" stroke-linecap="round"
                    stroke-dasharray="${dash} ${circumference - dash}" transform="rotate(-90 ${size/2} ${size/2})"
                    filter="url(#glow-${Math.round(percentage)})" style="box-shadow: 0 0 12px ${glowColor}"/>
            <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#fff"
                  style="font-size:${size*0.2}px;font-weight:700;letter-spacing:-0.02em">${Math.round(percentage)}%</text>
          </svg>`;
    }

    createErrorRing(percentage) {
        const size = 80; // same size as success ring
        const stroke = 4; // same thin stroke
        const radius = (size - stroke) / 2;
        const circumference = 2 * Math.PI * radius;
        const dash = Math.max(0, Math.min(100, percentage)) / 100 * circumference;
        let color = '#22c55e'; // green (good - low error rate)
        let glowColor = 'rgba(34,197,94,0.7)'; // green glow
        if (percentage > 80) {
            color = '#ef4444'; // red (bad - high error rate)
            glowColor = 'rgba(239,68,68,0.7)'; // red glow
        } else if (percentage > 50) {
            color = '#f59e0b'; // orange (warning - medium error rate)
            glowColor = 'rgba(245,158,11,0.7)'; // orange glow
        }
        
        return `
          <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" style="display:block;filter:drop-shadow(0 0 8px ${glowColor})">
            <defs>
              <filter id="error-glow-${Math.round(percentage)}">
                <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                <feMerge> 
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>
            <circle cx="${size/2}" cy="${size/2}" r="${radius}" stroke="rgba(255,255,255,0.08)" stroke-width="${stroke}" fill="none"/>
            <circle cx="${size/2}" cy="${size/2}" r="${radius}" stroke="${color}" stroke-width="${stroke}" stroke-linecap="round"
                    stroke-dasharray="${dash} ${circumference - dash}" transform="rotate(-90 ${size/2} ${size/2})"
                    filter="url(#error-glow-${Math.round(percentage)})" style="box-shadow: 0 0 12px ${glowColor}"/>
            <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#fff"
                  style="font-size:${size*0.2}px;font-weight:700;letter-spacing:-0.02em">${Math.round(percentage)}%</text>
          </svg>`;
    }

    updateRequestsTable(requests = []) {
        console.log('Updating requests table with', requests.length, 'items');
        
        const tbody = document.getElementById('requests-table');
        if (!tbody) {
            console.error('Requests table tbody not found');
            return;
        }
        
        // Ensure Health column exists and add legend
        ensureRequestsHealthColumn();
        addHealthLegend();
        
        if (requests.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="px-5 py-6 text-center text-zinc-500">No requests found</td></tr>';
            return;
        }
        
        tbody.innerHTML = requests.map((request, index) => {
            const time = request.ts ? new Date(request.ts).toLocaleTimeString() : '—';
            const method = request.method || '—';
            const path = request.path || '—';
            const status = request.status !== undefined && request.status !== null ? request.status : '—';
            const latency = request.latency_ms ? `${request.latency_ms.toFixed(1)}ms` : '—';
            const records = request.summary?.records || 0;
            const clientIp = request.client_ip || '—';
            const fitness = request.fitness || 0;
            
            const statusColor = (status >= 500) ? 'bg-rose-500/20 text-rose-300 border-rose-400/30' :
                               (status >= 400) ? 'bg-amber-500/20 text-amber-300 border-amber-400/30' :
                               'bg-emerald-500/20 text-emerald-300 border-emerald-400/30';
            
            // Create health gauge
            const healthGauge = this.createHealthGauge(fitness, request);
            
            return `
                <tr class="hover:bg-white/[0.04] cursor-pointer" data-index="${index}">
                    <td class="px-5 py-3">${healthGauge}</td>
                    <td class="px-5 py-3 text-sm text-zinc-300">${time}</td>
                    <td class="px-5 py-3 text-sm text-white">
                        <span class="text-zinc-400 mr-2">${method}</span>${path}
                    </td>
                    <td class="px-5 py-3">
                        <span class="inline-flex items-center gap-2 px-2.5 py-1 rounded-lg text-xs border ${statusColor}">
                            ${status}
                        </span>
                    </td>
                    <td class="px-5 py-3 text-sm text-zinc-300">${latency}</td>
                    <td class="px-5 py-3 text-sm text-zinc-300">${records}</td>
                    <td class="px-5 py-3 text-sm text-zinc-300">${clientIp}</td>
                </tr>
            `;
        }).join('');
        // Attach click handlers after render to be safe across browsers
        tbody.querySelectorAll('tr').forEach(tr => {
            tr.addEventListener('click', () => {
                const idx = Number(tr.getAttribute('data-index'));
                if (!Number.isNaN(idx)) this.showRequestDetails(idx);
            });
        });
        console.log('Requests table updated successfully');
    }

    showRequestDetails(index) {
        const request = this.currentRequestsData[index];
        if (!request) return;

        const content = document.getElementById('slide-over-content');
        
        // Create summary chips
        const chips = this.createSummaryChips(request);
        
        // Create JSON viewer
        const jsonViewer = `
            <div class="mt-6">
                <div class="flex items-center justify-between mb-2">
                    <div class="text-sm font-medium text-zinc-300">Raw JSON</div>
                    <button onclick="navigator.clipboard.writeText(JSON.stringify(${JSON.stringify(request)}, null, 2))" 
                            class="px-3 py-1.5 text-sm rounded-md bg-white/5 hover:bg-white/10 text-zinc-200">
                        Copy
                    </button>
                </div>
                <pre class="bg-black/40 border border-white/10 rounded-xl p-4 overflow-auto text-xs leading-relaxed text-zinc-300">
${(function(){ try { return JSON.stringify(request, null, 2).slice(0,20000); } catch { return String(request); } })()}
                </pre>
            </div>
        `;

        content.innerHTML = `
            <div class="space-y-6">
                <div class="flex flex-wrap gap-2">
                    ${chips}
                </div>
                ${jsonViewer}
            </div>
        `;

        this.openSlideOver();
    }

    createSummaryChips(request) {
        const chips = [];
        
        // Status chip
        const status = request.status ?? 0;
        let statusTone = 'ok';
        if (status >= 500) statusTone = 'danger';
        else if (status >= 400) statusTone = 'warn';
        
        chips.push(this.createChip('Status', String(status), statusTone));
        chips.push(this.createChip('Method', request.method ?? '—'));
        chips.push(this.createChip('Latency', request.latency_ms ? `${request.latency_ms}ms` : (request.duration_ms ? `${request.duration_ms}ms` : '—')));
        chips.push(this.createChip('Records', String(request.records ?? 0)));
        chips.push(this.createChip('Endpoint', request.path ?? '—'));
        chips.push(this.createChip('Source IP', `${this.getCountryFlag(request.geo_country)} ${request.client_ip ?? '—'}`));
        chips.push(this.createChip('Country', request.geo_country ?? '—'));
        chips.push(this.createChip('ASN', String(request.asn ?? '—')));
        chips.push(this.createChip('Tenant', request.tenant_id ?? '—'));
        chips.push(this.createChip('API Key', (request.api_key_hash ?? '—').slice(0, 8)));
        chips.push(this.createChip('Trace ID', request.trace_id ?? '—'));
        
        if (request.risk_avg != null) {
            chips.push(this.createChip('Avg Risk', String(request.risk_avg)));
        }

        return chips.join('');
    }

    createChip(label, value, tone = 'default') {
        const styles = {
            default: 'bg-white/5 text-zinc-200 border-white/10',
            ok: 'bg-emerald-500/15 text-emerald-300 border-emerald-400/20',
            warn: 'bg-amber-500/15 text-amber-300 border-amber-400/20',
            danger: 'bg-rose-500/15 text-rose-300 border-rose-400/20',
        }[tone];

        return `
            <div class="px-3 py-1.5 rounded-lg border ${styles}">
                <span class="mr-2 text-xs uppercase tracking-wide text-zinc-400">${label}</span>
                <span class="text-sm font-medium">${value}</span>
            </div>
        `;
    }

    openSlideOver() {
        const b = document.getElementById('slide-over-backdrop');
        const p = document.getElementById('slide-over');
        if (b) { b.style.opacity = '1'; b.classList.remove('pointer-events-none'); }
        if (p) { p.style.transform = 'translateX(0)'; }
    }

    closeSlideOver() {
        const b = document.getElementById('slide-over-backdrop');
        const p = document.getElementById('slide-over');
        if (b) { b.style.opacity = '0'; b.classList.add('pointer-events-none'); }
        if (p) { p.style.transform = 'translateX(100%)'; }
    }

    getCountryFlag(cc) {
        if (!cc) return '🏳️';
        const code = cc.trim().toUpperCase();
        if (code.length !== 2) return '🏳️';
        const A = 0x1f1e6; // regional indicator A
        return String.fromCodePoint(...[...code].map(c => A + (c.charCodeAt(0) - 65)));
    }

    createHealthGauge(fitness, request) {
        const clamped = Math.max(0, Math.min(1, fitness || 0));
        const percentage = Math.round(clamped * 100);
        
        // Determine color based on fitness
        let color = '#ef4444'; // red
        if (clamped >= 0.9) color = '#22c55e'; // green
        else if (clamped >= 0.6) color = '#f59e0b'; // amber
        
        // Create tooltip text
        let tooltip = 'Healthy';
        if (request.status >= 400) tooltip = `HTTP ${request.status}`;
        else if (request.timeline) {
            const v = request.timeline.find(x => x.event === 'validated');
            if (v && v.meta && v.meta.ok === false) tooltip = 'Validation failed';
            const e = request.timeline.find(x => x.event === 'exported');
            if (e && e.meta) {
                const bad = [];
                for (const k of ['splunk', 'elastic']) {
                    const v = e.meta[k];
                    if (v && String(v).toLowerCase() !== 'ok' && String(v).toLowerCase() !== 'success') bad.push(k);
                }
                if (bad.length) tooltip = `Export failure: ${bad.join(', ')}`;
            }
        }
        
        // Create SVG gauge with improved design
        const size = 32; // Slightly larger for better readability
        const strokeWidth = 2.5; // Thinner stroke for cleaner look
        const radius = (size - strokeWidth) / 2;
        const circumference = 2 * Math.PI * radius;
        const progress = circumference * clamped;
        
        return `
            <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" class="shrink-0" 
                 title="${tooltip}" role="img" aria-label="health ${percentage}%">
                <circle cx="${size/2}" cy="${size/2}" r="${radius}" 
                        stroke="#374151" stroke-width="${strokeWidth}" fill="none"/>
                <circle cx="${size/2}" cy="${size/2}" r="${radius}" 
                        stroke="${color}" stroke-width="${strokeWidth}" fill="none"
                        stroke-dasharray="${progress} ${circumference}"
                        stroke-linecap="round"
                        transform="rotate(-90 ${size/2} ${size/2})"/>
                <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle"
                      font-size="${size * 0.28}" font-weight="500" fill="#ffffff" font-family="Inter, system-ui, sans-serif">
                    ${percentage}
                </text>
            </svg>
        `;
    }

    startLogs() {
        try {
            this.hideError('logs');
            const logsContent = document.getElementById('logs-content');
            if (logsContent) {
                logsContent.innerHTML = 'Starting live logs...\n';
            }
            
            // Load initial logs first
            this.loadInitialLogs();
            
            // Since SSE is not available, we'll poll the logs endpoint
            this.logsInterval = setInterval(async () => {
                try {
                    const response = await fetch(`${this.apiBase}/v1/logs/tail?max_bytes=50000&format=text`, {
                        headers: { 'Authorization': `Bearer ${this.apiKey}` }
                    });
                    
                    if (response.ok) {
                        const text = await response.text();
                        if (logsContent && text.trim()) {
                            // Split into lines and show the last 100 lines
                            const lines = text.split('\n').filter(line => line.trim());
                            const recentLines = lines.slice(-100);
                            logsContent.innerHTML = recentLines.join('\n');
                        }
                    } else {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                } catch (error) {
                    console.error('Logs polling error:', error);
                    this.showError('logs', `Failed to fetch logs: ${error.message}`);
                }
            }, 2000); // Poll every 2 seconds
            
        } catch (error) {
            this.showError('logs', error.message);
        }
    }

    async loadInitialLogs() {
        try {
            const logsContent = document.getElementById('logs-content');
            if (!logsContent) return;
            
            const response = await fetch(`${this.apiBase}/v1/logs/tail?max_bytes=50000&format=text`, {
                headers: { 'Authorization': `Bearer ${this.apiKey}` }
            });
            
            if (response.ok) {
                const text = await response.text();
                if (text.trim()) {
                    const lines = text.split('\n').filter(line => line.trim());
                    const recentLines = lines.slice(-50); // Show last 50 lines initially
                    logsContent.innerHTML = recentLines.join('\n');
                } else {
                    logsContent.innerHTML = 'No logs available yet.';
                }
            } else {
                logsContent.innerHTML = `Failed to load logs: HTTP ${response.status}`;
            }
        } catch (error) {
            console.error('Initial logs loading error:', error);
            const logsContent = document.getElementById('logs-content');
            if (logsContent) {
                logsContent.innerHTML = `Error loading logs: ${error.message}`;
            }
        }
    }

    stopLogs() {
        if (this.logsInterval) {
            clearInterval(this.logsInterval);
            this.logsInterval = null;
        }
        if (this.logsEventSource) {
            this.logsEventSource.close();
            this.logsEventSource = null;
        }
        const logsContent = document.getElementById('logs-content');
        if (logsContent) {
            logsContent.innerHTML = 'Live logs stopped.';
        }
    }

    async downloadLogs() {
        try {
            const response = await fetch(`${this.apiBase}/v1/logs/download?max_bytes=2000000`, {
                headers: { 'Authorization': `Bearer ${this.apiKey}` }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const blob = await response.blob();
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `telemetry-logs-${Date.now()}.txt`;
            a.click();
        } catch (error) {
            this.showError('logs', error.message);
        }
    }

    async fetchSystem() {
        try {
            this.hideError('api');
            const btn = document.querySelector('#btn-system');
            setLoading(btn, true);
            
            let system;
            try {
                system = await this.apiCall('/system');
            } catch {
                system = await this.apiCall('/version');
            }
            setOutput(system);
            showToast('success', 'System info loaded.', '/v1/system');
        } catch (error) {
            this.showError('api', error.message);
            showToast('error', error.message, '/v1/system failed');
        } finally {
            const btn = document.querySelector('#btn-system');
            setLoading(btn, false);
        }
    }

    async fetchMetrics() {
        try {
            this.hideError('api');
            const btn = document.querySelector('#btn-metrics');
            setLoading(btn, true);
            
            const metrics = await this.apiCall('/metrics');
            setOutput(metrics);
            showToast('success', 'Metrics refreshed.', '/v1/metrics');
        } catch (error) {
            this.showError('api', error.message);
            showToast('error', error.message, '/v1/metrics failed');
        } finally {
            const btn = document.querySelector('#btn-metrics');
            setLoading(btn, false);
        }
    }

    async sendIngest() {
        try {
            this.hideError('api');
            const data = document.getElementById('ingest-payload').value;
            const btn = document.querySelector('#btn-send-ingest');
            
            // Parse JSON with detailed error reporting
            let bodyObj;
            try {
                bodyObj = JSON.parse(data);
            } catch (parseError) {
                throw new Error(`Invalid JSON: ${parseError.message}`);
            }
            
            // Validate payload
            const check = validateIngestBody(bodyObj);
            if (!check.ok) {
                throw new Error(`Invalid payload: ${check.msg}`);
            }
            
            setLoading(btn, true);
            
            // Make API call
            const result = await this.apiCall('/ingest', {
                method: 'POST',
                body: JSON.stringify(bodyObj)
            });
            
            setOutput(result);
            showToast('success', 'Ingest accepted.', '/v1/ingest');
            
            // Optionally refresh metrics after successful ingest
            try { 
                await this.fetchMetrics(); 
            } catch (_) {}
            
        } catch (error) {
            this.showError('api', error.message);
            showToast('error', error.message, '/v1/ingest failed');
        } finally {
            const btn = document.querySelector('#btn-send-ingest');
            setLoading(btn, false);
        }
    }

    async runLookup() {
        try {
            this.hideError('api');
            const value = document.getElementById('lookup-value').value;
            const result = await this.apiCall('/lookup', {
                method: 'POST',
                body: JSON.stringify({ value })
            });
            document.getElementById('api-output').textContent = JSON.stringify(result, null, 2);
        } catch (error) {
            this.showError('api', error.message);
        }
    }

    showError(panel, message) {
        console.log(`Showing error for panel: ${panel}, message: ${message}`);
        const errorEl = document.getElementById(`${panel}-error`);
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.classList.remove('hidden');
        } else {
            console.error(`Error element not found for panel: ${panel}`, message);
            // Try to show error in api-output if it's an API error
            if (panel === 'api') {
                const apiOutput = document.getElementById('api-output');
                if (apiOutput) {
                    apiOutput.textContent = `Error: ${message}`;
                }
            }
        }
    }

    hideError(panel) {
        const errorEl = document.getElementById(`${panel}-error`);
        if (errorEl) {
            errorEl.classList.add('hidden');
        }
    }

    formatNumber(n, decimals = 0) {
        if (n === null || n === undefined || Number.isNaN(n)) return '—';
        const nf = new Intl.NumberFormat(undefined, { maximumFractionDigits: decimals });
        return nf.format(n);
    }

    startAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        this.autoRefreshInterval = setInterval(() => {
            this.loadInitialData();
        }, 5000);
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }
}

// ====== HEALTH COLUMN BOOTSTRAP ======
function ensureRequestsHealthColumn() {
    // Try multiple selectors to find the table
    const table = document.querySelector('#requests-table, table.requests, table#requests, table');
    if (!table) {
        console.log('No table found for health column');
        return;
    }

    const thead = table.querySelector('thead');
    if (!thead) {
        console.log('No thead found');
        return;
    }

    const headerRow = thead.querySelector('tr');
    if (!headerRow) {
        console.log('No header row found');
        return;
    }

    const hasHealth = Array.from(headerRow.querySelectorAll('th'))
        .some(th => th.textContent.trim().toLowerCase() === 'health');
    
    if (!hasHealth) {
        console.log('Adding Health column to table');
        const th = document.createElement('th');
        th.textContent = 'Health';
        th.className = 'px-5 py-3 text-left whitespace-nowrap';
        headerRow.insertBefore(th, headerRow.firstChild);
    } else {
        console.log('Health column already exists');
    }
}

function addHealthLegend() {
    // Add legend if it doesn't exist
    const existingLegend = document.querySelector('.health-legend');
    if (existingLegend) return;

    const table = document.querySelector('#requests-table, table.requests, table#requests');
    if (!table) return;

    const legend = document.createElement('div');
    legend.className = 'health-legend mt-6 mb-2 flex items-center justify-center gap-6 text-xs text-zinc-500';
    legend.innerHTML = `
        <span class="flex items-center gap-1">
            <div class="w-3 h-3 rounded-full bg-emerald-500"></div>
            <span class="font-medium">≥90%</span>
        </span>
        <span class="flex items-center gap-1">
            <div class="w-3 h-3 rounded-full bg-amber-500"></div>
            <span class="font-medium">≥60%</span>
        </span>
        <span class="flex items-center gap-1">
            <div class="w-3 h-3 rounded-full bg-red-500"></div>
            <span class="font-medium">&lt;60%</span>
        </span>
    `;
    
    table.parentNode.insertBefore(legend, table.nextSibling);
}

// ====== SOURCES FUNCTIONALITY ======
function addSourcesFunctionality() {
    const dashboard = window.telemetryDashboard;
    if (!dashboard) return;

    // Add Sources methods to dashboard
    dashboard.sourcesData = [];
    dashboard.sourcesFilters = {
        tenant: '',
        type: '',
        status: '',
        page: 1,
        page_size: 30
    };
    dashboard.sourcesPollingInterval = null;

    dashboard.loadSourcesData = async function() {
        try {
            console.log('Loading sources data...');
            this.hideError('sources');
            
            const params = new URLSearchParams();
            if (this.sourcesFilters.tenant) params.append('tenant', this.sourcesFilters.tenant);
            if (this.sourcesFilters.type) params.append('type', this.sourcesFilters.type);
            if (this.sourcesFilters.status) params.append('status', this.sourcesFilters.status);
            params.append('page', this.sourcesFilters.page.toString());
            params.append('page_size', this.sourcesFilters.page_size.toString());

            const response = await this.apiCall(`/sources?${params.toString()}`);
            console.log('Sources response:', response);
            
            const items = response.items || response.sources || [];
            if (Array.isArray(items)) {
                this.sourcesData = items;
                this.renderSourcesTable();
                this.updateSourcesPagination(response);
                this.startSourcesPolling();
            } else {
                throw new Error('Invalid response format');
            }
        } catch (error) {
            console.error('Failed to load sources:', error);
            this.showError('sources', error.message);
        }
    };

    dashboard.renderSourcesTable = function() {
        const tbody = document.getElementById('sources-table');
        if (!tbody) return;

        if (this.sourcesData.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" class="px-6 py-8 text-center text-zinc-400">No sources found</td></tr>';
            return;
        }

        tbody.innerHTML = this.sourcesData.map(source => {
            // Parse allowed_ips
            let allowedIps = [];
            try {
                allowedIps = typeof source.allowed_ips === 'string' ? JSON.parse(source.allowed_ips) : source.allowed_ips || [];
            } catch (e) {
                allowedIps = [];
            }
            
            const typeBadge = (t) => {
                const type = String(t || '').toLowerCase();
                const base = 'inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ring-1';
                // UDP: orange/amber tone
                if (type === 'udp') return `<span class="${base} bg-amber-500/15 text-amber-300 ring-amber-500/40">UDP</span>`;
                // API: pink/fuchsia tone
                if (type === 'http' || type === 'api') return `<span class="${base} bg-fuchsia-500/15 text-fuchsia-300 ring-fuchsia-500/40">API</span>`;
                return `<span class="${base} bg-zinc-500/15 text-zinc-300 ring-zinc-500/40">${type || '—'}</span>`;
            };

            return `
                <tr class="hover:bg-white/5 transition-colors">
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ring-1 ${getStatusBadgeClass(source.status)}">
                            ${source.status.charAt(0).toUpperCase() + source.status.slice(1)}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-white font-medium cursor-pointer" onclick="window.telemetryDashboard.openSourceDetails('${source.id}')">${source.display_name}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-zinc-300">${typeBadge(source.type)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-zinc-300">${source.tenant_id}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-zinc-300">${allowedIps.length} IPs</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-zinc-300">${source.max_eps || 0}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-zinc-300">—</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-zinc-300">${source.last_seen ? new Date(source.last_seen).toLocaleString() : '—'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-zinc-300">—</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-zinc-300">
                        <div class="flex items-center space-x-3 text-sm">
                            <button class="text-white/80 hover:text-white" data-action="edit" data-id="${source.id}">Edit</button>
                            <span class="text-white/20">|</span>
                            <button class="text-rose-400 hover:text-rose-300" data-action="delete" data-id="${source.id}">Delete</button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    };

    dashboard.updateSourcesPagination = function(response) {
        const pagination = document.getElementById('sources-pagination');
        const rangeStart = document.getElementById('sources-range-start');
        const rangeEnd = document.getElementById('sources-range-end');
        const totalEl = document.getElementById('sources-total');
        const page = document.getElementById('sources-page');
        const prevBtn = document.getElementById('sources-prev');
        const nextBtn = document.getElementById('sources-next');

        const total = response.total ?? 0;
        const pageNum = response.page ?? this.sourcesFilters.page;
        const pageSize = response.page_size ?? this.sourcesFilters.page_size;
        const itemsCount = (response.items || response.sources || []).length;

        if (pagination && total > 0) {
            pagination.classList.remove('hidden');
            const start = (pageNum - 1) * pageSize + 1;
            const end = Math.min(pageNum * pageSize, total);
            if (rangeStart) rangeStart.textContent = start;
            if (rangeEnd) rangeEnd.textContent = end;
            if (totalEl) totalEl.textContent = total;
            if (page) page.textContent = pageNum;
            if (prevBtn) prevBtn.disabled = pageNum <= 1;
            if (nextBtn) nextBtn.disabled = (pageNum * pageSize) >= total || itemsCount < pageSize;
        } else if (pagination) {
            pagination.classList.add('hidden');
        }
    };

    dashboard.startSourcesPolling = function() {
        if (this.sourcesPollingInterval) {
            clearInterval(this.sourcesPollingInterval);
        }
        
        this.sourcesPollingInterval = setInterval(async () => {
            // Update metrics for visible sources without full reload
            for (const source of this.sourcesData) {
                try {
                    const metrics = await this.apiCall(`/sources/${source.id}/metrics?window=900`);
                    if (metrics) {
                        // Update the source row with new metrics
                        this.updateSourceMetrics(source.id, metrics);
                    }
                } catch (error) {
                    console.error(`Failed to update metrics for ${source.id}:`, error);
                }
            }
        }, 10000); // 10 seconds
    };

    dashboard.updateSourceMetrics = function(sourceId, metrics) {
        const row = document.querySelector(`tr[onclick*="${sourceId}"]`);
        if (!row) return;

        const cells = row.querySelectorAll('td');
        if (cells.length >= 10) {
            // Update EPS (1m)
            cells[5].textContent = this.formatNumber(metrics.eps_1m, 2);
            // Update Records (24h)
            cells[6].textContent = this.formatNumber(metrics.records_24h);
            // Update Error %
            cells[8].textContent = this.formatNumber(metrics.error_pct_15m, 1) + '%';
            // Update Avg Risk
            cells[9].textContent = this.formatNumber(metrics.avg_risk_15m, 2);
        }
    };

    dashboard.openSourceDetails = async function(sourceId) {
        try {
            // Fetch fresh source data from API
            const source = await this.apiCall(`/sources/${sourceId}`);
            if (!source) {
                this.showToast('Source not found', 'error');
                return;
            }

            // Store current source for updates
            this.currentSource = source;

            // Populate modal with source data
            document.getElementById('source-id').value = source.id;
            document.getElementById('source-display-name').value = source.display_name || '';
            const typeWrap = document.getElementById('source-type-badge');
            const originWrap = document.getElementById('source-origin-badge');
            if (typeWrap) {
                const t = (source.type || '').toLowerCase();
                const o = (source.origin || '').toLowerCase();
                const base = 'inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ring-1';
                
                // Type badge (declared intent)
                const typeHtml = t === 'udp'
                    ? `<span class="${base} bg-amber-500/15 text-amber-300 ring-amber-500/40">UDP</span>`
                    : `<span class="${base} bg-fuchsia-500/15 text-fuchsia-300 ring-fuchsia-500/40">API</span>`;
                typeWrap.innerHTML = typeHtml;
                
                // Origin badge (actual traffic)
                if (originWrap && o) {
                    const originHtml = o === 'udp'
                        ? `<span class="${base} bg-amber-500/15 text-amber-300 ring-amber-500/40">UDP</span>`
                        : o === 'http'
                        ? `<span class="${base} bg-fuchsia-500/15 text-fuchsia-300 ring-fuchsia-500/40">HTTP</span>`
                        : `<span class="${base} bg-gray-500/15 text-gray-300 ring-gray-500/40">Unknown</span>`;
                    originWrap.innerHTML = originHtml;
                    
                    // Add mismatch indicator if type != origin
                    if (t !== o) {
                        typeWrap.innerHTML += `<span class="ml-2 text-xs text-red-400">⚠️ Mismatch</span>`;
                    }
                }
            }
            document.getElementById('source-tenant').value = source.tenant_id;
            document.getElementById('source-status').value = source.status || 'enabled';
            document.getElementById('source-max-eps').value = source.max_eps || 0;
            document.getElementById('source-block-on-exceed').checked = source.block_on_exceed !== false;

            // Parse and display allowed IPs (normalize to array for UI editing)
            let allowedIps = [];
            try {
                allowedIps = Array.isArray(source.allowed_ips) 
                    ? source.allowed_ips 
                    : JSON.parse(source.allowed_ips || '[]');
            } catch (e) {
                console.error('Failed to parse allowed_ips:', e);
                allowedIps = [];
            }
            this.renderAllowedIPs(JSON.stringify(allowedIps));

            // Show admin controls if user has admin scope
            const isAdmin = this.hasAdminScope();
            document.getElementById('admin-controls').classList.toggle('hidden', !isAdmin);

            // Clear test results
            document.getElementById('test-result').classList.add('hidden');
            document.getElementById('sync-result').classList.add('hidden');

            // Show modal
            document.getElementById('source-modal').classList.remove('hidden');
        } catch (error) {
            this.showToast(`Failed to load source: ${error.message}`, 'error');
        }
    };

    dashboard.renderAllowedIPs = function(allowedIpsJson) {
        const container = document.getElementById('allowed-ips-container');
        container.innerHTML = '';

        try {
            const ips = JSON.parse(allowedIpsJson);
            ips.forEach(ip => {
                const chip = document.createElement('div');
                chip.className = 'inline-flex items-center gap-2 px-3 py-1 bg-[#0F1116] text-zinc-300 rounded-lg text-sm';
                chip.innerHTML = `
                    <span>${ip}</span>
                    <button onclick="this.parentElement.remove()" class="text-zinc-500 hover:text-red-400">×</button>
                `;
                container.appendChild(chip);
            });
        } catch (e) {
            console.error('Failed to parse allowed IPs:', e);
        }
    };

    dashboard.hasAdminScope = function() {
        // Check if current API key has admin scope
        // This is a simplified check - in a real implementation, you'd check the actual scopes
        return true; // For now, assume admin access
    };

    dashboard.saveSourceChanges = async function() {
        const sourceId = document.getElementById('source-id').value;
        const displayName = document.getElementById('source-display-name').value;
        const status = document.getElementById('source-status').value;
        const maxEps = parseInt(document.getElementById('source-max-eps').value) || 0;
        const blockOnExceed = document.getElementById('source-block-on-exceed').checked;

        // Collect allowed IPs from chips
        const allowedIps = Array.from(document.getElementById('allowed-ips-container').children)
            .map(chip => chip.querySelector('span').textContent);

        const updateData = {
            display_name: displayName,
            status: status,
            allowed_ips: allowedIps, // Send as array, backend will handle JSON conversion
            max_eps: maxEps,
            block_on_exceed: blockOnExceed
        };

        try {
            const response = await this.apiCall(`/sources/${sourceId}`, {
                method: 'PUT',
                body: JSON.stringify(updateData)
            });

            // Update local data
            const sourceIndex = this.sourcesData.findIndex(s => s.id === sourceId);
            if (sourceIndex !== -1) {
                this.sourcesData[sourceIndex] = { ...this.sourcesData[sourceIndex], ...updateData };
                this.renderSourcesTable();
            }

            this.showToast('Source updated successfully', 'success');
            this.closeSourceModal();
        } catch (error) {
            this.showToast(`Failed to update source: ${error.message}`, 'error');
        }
    };

    dashboard.testAdmission = async function() {
        const sourceId = document.getElementById('source-id').value;
        const testIp = document.getElementById('test-ip-input').value.trim();
        const resultDiv = document.getElementById('test-result');

        if (!testIp) {
            this.showToast('Please enter an IP address to test', 'error');
            return;
        }

        try {
            const response = await this.apiCall(`/sources/${sourceId}/admission/test`, {
                method: 'POST',
                body: JSON.stringify({ client_ip: testIp })
            });

            resultDiv.classList.remove('hidden');
            if (response.allowed) {
                resultDiv.className = 'mt-2 text-sm text-green-400';
                resultDiv.textContent = `✅ Allowed: ${response.reason || 'IP is allowed'}`;
            } else {
                resultDiv.className = 'mt-2 text-sm text-red-400';
                resultDiv.textContent = `❌ Blocked: ${response.reason || 'IP is not allowed'}`;
            }
        } catch (error) {
            resultDiv.classList.remove('hidden');
            resultDiv.className = 'mt-2 text-sm text-red-400';
            resultDiv.textContent = `❌ Error: ${error.message}`;
        }
    };

    dashboard.syncFirewall = async function() {
        const resultDiv = document.getElementById('sync-result');

        try {
            const response = await this.apiCall('/admin/security/sync-allowlist', {
                method: 'POST'
            });

            resultDiv.classList.remove('hidden');
            resultDiv.className = 'mt-2 text-sm text-green-400';
            resultDiv.textContent = `✅ Firewall synced: ${response.ipv4_added} IPv4, ${response.ipv6_added} IPv6 CIDRs`;
        } catch (error) {
            resultDiv.classList.remove('hidden');
            resultDiv.className = 'mt-2 text-sm text-red-400';
            resultDiv.textContent = `❌ Sync failed: ${error.message}`;
        }
    };

    dashboard.closeSourceModal = function() {
        document.getElementById('source-modal').classList.add('hidden');
        document.getElementById('test-result').classList.add('hidden');
        document.getElementById('sync-result').classList.add('hidden');
    };

    dashboard.addAllowedIP = function() {
        const input = document.getElementById('new-ip-input');
        const ip = input.value.trim();
        
        if (!ip) return;

        // Basic CIDR validation
        const cidrRegex = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/;
        if (!cidrRegex.test(ip)) {
            this.showToast('Please enter a valid CIDR (e.g., 192.168.1.0/24)', 'error');
            return;
        }

        // Check if IP already exists
        const existingIps = Array.from(document.getElementById('allowed-ips-container').children)
            .map(chip => chip.querySelector('span').textContent);
        
        if (existingIps.includes(ip)) {
            this.showToast('IP already exists in the list', 'error');
            return;
        }

        // Add IP chip
        const container = document.getElementById('allowed-ips-container');
        const chip = document.createElement('div');
        chip.className = 'inline-flex items-center gap-2 px-3 py-1 bg-[#0F1116] text-zinc-300 rounded-lg text-sm';
        chip.innerHTML = `
            <span>${ip}</span>
            <button onclick="this.parentElement.remove()" class="text-zinc-500 hover:text-red-400">×</button>
        `;
        container.appendChild(chip);

        input.value = '';
    };

    dashboard.showToast = function(message, type = 'info') {
        // Simple toast implementation
        const toast = document.createElement('div');
        toast.className = `fixed top-4 right-4 px-4 py-2 rounded-lg text-white text-sm z-50 ${
            type === 'success' ? 'bg-green-600' : 
            type === 'error' ? 'bg-red-600' : 'bg-blue-600'
        }`;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    };

    dashboard.deleteSource = async function(sourceId) {
        if (!confirm('Are you sure you want to delete this source? This action cannot be undone.')) {
            return;
        }

        try {
            await this.apiCall(`/sources/${sourceId}`, {
                method: 'DELETE'
            });

            // Remove from local data
            this.sourcesData = this.sourcesData.filter(s => s.id !== sourceId);
            this.renderSourcesTable();

            this.showToast('Source deleted successfully', 'success');
        } catch (error) {
            this.showToast(`Failed to delete source: ${error.message}`, 'error');
        }
    };

    // Wire up filter event listeners
    const tenantFilter = document.getElementById('sources-tenant-filter');
    const typeFilter = document.getElementById('sources-type-filter');
    const statusFilter = document.getElementById('sources-status-filter');
    const sizeFilter = document.getElementById('sources-size-filter');

    if (tenantFilter) {
        tenantFilter.addEventListener('change', (e) => {
            dashboard.sourcesFilters.tenant = e.target.value;
            dashboard.sourcesFilters.page = 1;
            dashboard.loadSourcesData();
        });
    }

    if (typeFilter) {
        typeFilter.addEventListener('change', (e) => {
            dashboard.sourcesFilters.type = e.target.value;
            dashboard.sourcesFilters.page = 1;
            dashboard.loadSourcesData();
        });
    }

    if (statusFilter) {
        statusFilter.addEventListener('change', (e) => {
            dashboard.sourcesFilters.status = e.target.value;
            dashboard.sourcesFilters.page = 1;
            dashboard.loadSourcesData();
        });
    }

    if (sizeFilter) {
        sizeFilter.addEventListener('change', (e) => {
            dashboard.sourcesFilters.page_size = parseInt(e.target.value);
            dashboard.sourcesFilters.page = 1;
            dashboard.loadSourcesData();
        });
    }

    // Wire up pagination
    const prevBtn = document.getElementById('sources-prev');
    const nextBtn = document.getElementById('sources-next');

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (dashboard.sourcesFilters.page > 1) {
                dashboard.sourcesFilters.page--;
                dashboard.loadSourcesData();
            }
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            dashboard.sourcesFilters.page++;
            dashboard.loadSourcesData();
        });
    }

    // Wire up Source Details modal event listeners
    const sourceModal = document.getElementById('source-modal');
    const sourceModalBackdrop = document.getElementById('source-modal-backdrop');
    const sourceModalClose = document.getElementById('source-modal-close');
    const sourceCancelBtn = document.getElementById('source-cancel-btn');
    const sourceSaveBtn = document.getElementById('source-save-btn');
    const addIpBtn = document.getElementById('add-ip-btn');
    const testAdmissionBtn = document.getElementById('test-admission-btn');
    const syncFirewallBtn = document.getElementById('sync-firewall-btn');

    if (sourceModalBackdrop) {
        sourceModalBackdrop.addEventListener('click', () => dashboard.closeSourceModal());
    }

    if (sourceModalClose) {
        sourceModalClose.addEventListener('click', () => dashboard.closeSourceModal());
    }

    if (sourceCancelBtn) {
        sourceCancelBtn.addEventListener('click', () => dashboard.closeSourceModal());
    }

    if (sourceSaveBtn) {
        sourceSaveBtn.addEventListener('click', () => dashboard.saveSourceChanges());
    }

    if (addIpBtn) {
        addIpBtn.addEventListener('click', () => dashboard.addAllowedIP());
    }

    if (testAdmissionBtn) {
        testAdmissionBtn.addEventListener('click', () => dashboard.testAdmission());
    }

    if (syncFirewallBtn) {
        syncFirewallBtn.addEventListener('click', () => dashboard.syncFirewall());
    }

    // Allow Enter key to add IP
    const newIpInput = document.getElementById('new-ip-input');
    if (newIpInput) {
        newIpInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                dashboard.addAllowedIP();
            }
        });
    }

    // Allow Enter key to test admission
    const testIpInput = document.getElementById('test-ip-input');
    if (testIpInput) {
        testIpInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                dashboard.testAdmission();
            }
        });
    }
}

function getStatusBadgeClass(status) {
    // Map Enabled/Disabled to green/gray; keep legacy health fallbacks
    const s = (status || '').toLowerCase();
    if (s === 'enabled') return 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/40';
    if (s === 'disabled') return 'bg-zinc-500/15 text-zinc-300 ring-zinc-500/40';
    const classes = {
        healthy: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/40',
        degraded: 'bg-amber-500/15 text-amber-300 ring-amber-500/40',
        stale: 'bg-zinc-500/15 text-zinc-300 ring-zinc-500/40'
    };
    return classes[s] || classes.stale;
}

// Initialize Sources functionality when dashboard is ready
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(addSourcesFunctionality, 100);
});
