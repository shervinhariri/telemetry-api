// Modern Telemetry Dashboard - Vanilla JavaScript with Tailwind CSS
class TelemetryDashboard {
    constructor() {
        this.apiBase = 'http://localhost';
        this.apiKey = 'TEST_KEY'; // Change this to your desired API key
        this.currentRequestsData = [];
        this.logsEventSource = null;
        this.logsInterval = null;
        this.autoRefreshInterval = null;
        
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

        // Auto-refresh toggle
        document.getElementById('auto-refresh').addEventListener('change', (e) => {
            this.autoRefresh = e.target.checked;
            if (this.autoRefresh) {
                this.startAutoRefresh();
            } else {
                this.stopAutoRefresh();
            }
        });

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
        const fetchSystemBtn = document.getElementById('fetch-system');
        const fetchMetricsBtn = document.getElementById('fetch-metrics');
        const sendIngestBtn = document.getElementById('send-ingest');
        const runLookupBtn = document.getElementById('run-lookup');
        
        if (fetchSystemBtn) fetchSystemBtn.addEventListener('click', () => this.fetchSystem());
        if (fetchMetricsBtn) fetchMetricsBtn.addEventListener('click', () => this.fetchMetrics());
        if (sendIngestBtn) sendIngestBtn.addEventListener('click', () => this.sendIngest());
        if (runLookupBtn) runLookupBtn.addEventListener('click', () => this.runLookup());

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
        }
    }

    async apiCall(endpoint, options = {}) {
        try {
            const url = `${this.apiBase}/v1${endpoint}`;
            const headers = {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.apiKey}`,
                ...options.headers
            };

            console.log('API call:', url);
            const response = await fetch(url, { ...options, headers });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API call failed (${endpoint}):`, error);
            throw error;
        }
    }

    async loadInitialData() {
        try {
            console.log('Loading initial data...');
            
            // Load system info first
            let system;
            try {
                system = await this.apiCall('/system');
                console.log('System info loaded:', system);
            } catch (error) {
                console.error('Failed to load system info:', error);
                system = { version: '0.7.9' }; // Set default version
            }
            
            this.updateSystemInfo(system);

            // Load metrics
            const metrics = await this.apiCall('/metrics');
            console.log('Metrics loaded:', metrics);
            this.updateDashboardMetrics(metrics);
            
        } catch (error) {
            console.error('Failed to load initial data:', error);
            this.showError('dashboard', error.message);
        }
    }

    updateSystemInfo(system) {
        console.log('Updating system info:', system);
        
        const version = system?.version || system?.service || '0.7.9';
        console.log('Version to display:', version);
        
        // Update version in dashboard only
        const versionElement = document.getElementById('version');
        if (versionElement) {
            versionElement.textContent = version;
            versionElement.title = 'Click to open Swagger UI documentation';
        }

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
        const errorRateElement = document.getElementById('error-rate');
        if (errorRateElement) {
            errorRateElement.textContent = `${errorRate}%`;
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
            
            // Try multiple endpoints to get requests data
            let requestsData = null;
            
            try {
                // Try /v1/admin/requests first
                requestsData = await this.apiCall('/admin/requests');
                console.log('Admin requests loaded:', requestsData);
            } catch (error) {
                console.log('Admin requests failed, trying API requests...');
                try {
                    // Try /v1/api/requests as fallback
                    requestsData = await this.apiCall('/api/requests');
                    console.log('API requests loaded:', requestsData);
                } catch (apiError) {
                    console.error('Both request endpoints failed:', apiError);
                    throw apiError;
                }
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
            if (successRing) {
                successRing.style.strokeDasharray = '0 440';
            }
            return;
        }
        
        // Calculate success rate
        const totalRequests = requests.length;
        const successfulRequests = requests.filter(req => (req.status || 0) < 400).length;
        const successRate = totalRequests > 0 ? Math.round((successfulRequests / totalRequests) * 100 * 10) / 10 : 0;
        
        // Calculate average latency
        const latencies = requests.map(req => req.duration_ms || 0).filter(lat => lat > 0);
        const avgLatency = latencies.length > 0 ? Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length) : 0;
        
        // Update success rate percentage
        const successPercentageElement = document.getElementById('success-percentage');
        if (successPercentageElement) {
            successPercentageElement.textContent = `${successRate}%`;
        }
        
        // Update circular progress ring
        const successRing = document.getElementById('success-ring');
        if (successRing) {
            const circumference = 2 * Math.PI * 70; // 2πr where r=70
            const progress = (successRate / 100) * circumference;
            successRing.style.strokeDasharray = `${progress} ${circumference}`;
        }
        
        // Update average latency
        const avgLatencyElement = document.getElementById('avg-latency');
        if (avgLatencyElement) {
            avgLatencyElement.textContent = `${avgLatency}ms`;
        }
        
        console.log('Requests summary updated:', { successRate, avgLatency, totalRequests, successfulRequests });
    }

    updateRequestsTable(requests = []) {
        console.log('Updating requests table with', requests.length, 'items');
        
        const tbody = document.getElementById('requests-table');
        if (!tbody) {
            console.error('Requests table tbody not found');
            return;
        }
        
        if (requests.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="px-5 py-6 text-center text-zinc-500">No requests found</td></tr>';
            return;
        }
        
        tbody.innerHTML = requests.map((request, index) => {
            const time = request.ts ? new Date(request.ts).toLocaleTimeString() : '—';
            const method = request.method || '—';
            const path = request.path || '—';
            const status = request.status !== undefined && request.status !== null ? request.status : '—';
            const latency = request.duration_ms ? `${request.duration_ms}ms` : '—';
            const records = request.ops || 0;
            const clientIp = request.client_ip || '—';
            const country = request.geo_country || '';
            
            const statusColor = (status >= 500) ? 'bg-rose-500/20 text-rose-300 border-rose-400/30' :
                               (status >= 400) ? 'bg-amber-500/20 text-amber-300 border-amber-400/30' :
                               'bg-emerald-500/20 text-emerald-300 border-emerald-400/30';
            
            const flag = this.getCountryFlag(country);
            
            return `
                <tr class="hover:bg-white/[0.04] cursor-pointer" onclick="dashboard.showRequestDetails(${index})">
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
                    <td class="px-5 py-3 text-sm text-zinc-300">
                        ${flag} ${clientIp}
                    </td>
                </tr>
            `;
        }).join('');
        
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
${JSON.stringify(request, null, 2)}
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
        document.getElementById('slide-over-backdrop').classList.add('open');
        document.getElementById('slide-over').classList.add('open');
        document.getElementById('slide-over-backdrop').classList.remove('pointer-events-none');
    }

    closeSlideOver() {
        document.getElementById('slide-over-backdrop').classList.remove('open');
        document.getElementById('slide-over').classList.remove('open');
        document.getElementById('slide-over-backdrop').classList.add('pointer-events-none');
    }

    getCountryFlag(cc) {
        if (!cc) return '🏳️';
        const code = cc.trim().toUpperCase();
        if (code.length !== 2) return '🏳️';
        const A = 0x1f1e6; // regional indicator A
        return String.fromCodePoint(...[...code].map(c => A + (c.charCodeAt(0) - 65)));
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
            let system;
            try {
                system = await this.apiCall('/system');
            } catch {
                system = await this.apiCall('/version');
            }
            document.getElementById('system-response').textContent = JSON.stringify(system, null, 2);
        } catch (error) {
            this.showError('api', error.message);
        }
    }

    async fetchMetrics() {
        try {
            this.hideError('api');
            const metrics = await this.apiCall('/metrics');
            document.getElementById('metrics-response').textContent = JSON.stringify(metrics, null, 2);
        } catch (error) {
            this.showError('api', error.message);
        }
    }

    async sendIngest() {
        try {
            this.hideError('api');
            const data = document.getElementById('ingest-data').value;
            const json = JSON.parse(data);
            const result = await this.apiCall('/ingest', {
                method: 'POST',
                body: JSON.stringify(json)
            });
            document.getElementById('api-output').textContent = JSON.stringify(result, null, 2);
        } catch (error) {
            this.showError('api', error.message);
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
        const errorEl = document.getElementById(`${panel}-error`);
        errorEl.textContent = message;
        errorEl.classList.remove('hidden');
    }

    hideError(panel) {
        const errorEl = document.getElementById(`${panel}-error`);
        errorEl.classList.add('hidden');
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

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new TelemetryDashboard();
});
