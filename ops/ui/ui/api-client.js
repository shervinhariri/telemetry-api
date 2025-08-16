// Central API Client for Telemetry API
// Single source of truth for API configuration

// Configuration - can be overridden by window.__CFG__
const DEFAULT_CONFIG = {
    API_BASE_URL: 'http://localhost:8080',
    API_PREFIX: '/v1',
    API_KEY: 'TEST_KEY'
};

// Get config from window.__CFG__ or use defaults
const config = window.__CFG__ || DEFAULT_CONFIG;

// Log config in dev mode
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    console.log('API Config:', {
        API_BASE_URL: config.API_BASE_URL,
        API_PREFIX: config.API_PREFIX,
        API_KEY: config.API_KEY ? `${config.API_KEY.substring(0, 8)}...` : 'NOT_SET'
    });
}

/**
 * Central API client function
 * @param {string} path - API path (e.g., '/api/requests')
 * @param {Object} params - Query parameters
 * @returns {Promise<Object>} JSON response
 */
async function api(path, params = {}) {
  try {
    // Build URL
    const qp = new URLSearchParams(params).toString();
    
                // All endpoints should use /v1 prefix for consistency
            const url = `${config.API_BASE_URL}${config.API_PREFIX}${path}${qp ? `?${qp}` : ''}`;
    
    // Prepare headers
    const headers = {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    };
    
    // Add Authorization header for all endpoints except health and docs
    if (config.API_KEY && !path.endsWith('/health') && !path.includes('/docs') && !path.includes('/openapi')) {
      headers['Authorization'] = `Bearer ${config.API_KEY}`;
    }
    
    // Log request in dev mode
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      console.log(`[API] ${url}`, { headers: { ...headers, Authorization: headers.Authorization ? 'Bearer ***' : undefined } });
    }
    
    // Make request
    const startTime = performance.now();
    const response = await fetch(url, { headers });
    const duration = performance.now() - startTime;
    
    // Log response in dev mode
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      console.log(`[API] ${response.status} ${response.statusText} (${duration.toFixed(1)}ms)`);
    }
    
    // Handle errors
    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      
      try {
        const errorJson = JSON.parse(errorText);
        if (errorJson.detail) {
          errorMessage = errorJson.detail;
        }
      } catch (e) {
        // Use default error message if JSON parsing fails
      }
      
      // Show toast for 401/404 errors
      if (response.status === 401) {
        showToast('Authentication failed - check API key', 'error');
      } else if (response.status === 404) {
        showToast(`Endpoint not found: ${path}`, 'error');
      }
      
      throw new Error(errorMessage);
    }
    
    // Parse JSON response
    const data = await response.json();
    return data;
    
  } catch (error) {
    console.error(`API Error (${path}):`, error);
    throw error;
  }
}

/**
 * Transform API request data to UI format
 * @param {Object} apiData - Raw API response
 * @returns {Object} UI-formatted data
 */
function toUiRequestRow(apiData) {
  try {
    // Guard against null/undefined
    if (!apiData || typeof apiData !== 'object') {
      console.warn('toUiRequestRow: Invalid input data', apiData);
      apiData = {};
    }
    
    const result = {
      id: apiData.id || apiData.request_id || crypto.randomUUID(),
      method: (apiData.method || '').toUpperCase(),
      path: apiData.path || apiData.url || apiData.endpoint || '/',
      status: Number(apiData.status || apiData.code || 0),
      latencyMs: Number(apiData.latency_ms ?? apiData.duration_ms ?? 0),
      when: apiData.ts || apiData.timestamp || apiData.time || new Date().toISOString(),
      srcIp: apiData.source_ip || apiData.client_ip || apiData.remote_addr || '-',
      apiKeyScope: apiData.scope || apiData.api_key_scope || '-',
      records: Number(apiData.records || 0),
      riskAvg: Number(apiData.risk_avg || 0),
      result: apiData.result || 'unknown'
    };
    
    // Validate critical fields
    if (isNaN(result.status)) result.status = 0;
    if (isNaN(result.latencyMs)) result.latencyMs = 0;
    if (isNaN(result.records)) result.records = 0;
    if (isNaN(result.riskAvg)) result.riskAvg = 0;
    
    return result;
  } catch (error) {
    console.error('Error transforming request row:', error, apiData);
    return {
      id: crypto.randomUUID(),
      method: 'UNKNOWN',
      path: '/',
      status: 0,
      latencyMs: 0,
      when: new Date().toISOString(),
      srcIp: '-',
      apiKeyScope: '-',
      records: 0,
      riskAvg: 0,
      result: 'error'
    };
  }
}

/**
 * Transform API metrics data to UI format
 * @param {Object} apiData - Raw API response
 * @returns {Object} UI-formatted metrics
 */
function toDashboardMetrics(apiData) {
  try {
    // Guard against null/undefined
    if (!apiData || typeof apiData !== 'object') {
      console.warn('toDashboardMetrics: Invalid input data', apiData);
      apiData = {};
    }
    
    const result = {
      throughput: Number(apiData.eps || apiData.throughput || 0),
      queueLag: Number(apiData.queue_depth || apiData.queue_lag || 0),
      avgRisk: Number(apiData.avg_risk || apiData.risk_avg || 0),
      threatMatches: Number(apiData.threat_matches || apiData.threats || 0),
      errorRate: Number(apiData.error_rate || 0),
      totalRequests: Number(apiData.requests_total || 0),
      succeeded: Number(apiData.requests_succeeded || 0),
      failed: Number(apiData.requests_failed || 0),
      avgLatency: Number(apiData.avg_latency_ms || 0)
    };
    
    // Validate all numeric fields
    Object.keys(result).forEach(key => {
      if (isNaN(result[key])) {
        console.warn(`toDashboardMetrics: Invalid ${key} value:`, apiData[key]);
        result[key] = 0;
      }
    });
    
    return result;
  } catch (error) {
    console.error('Error transforming metrics:', error, apiData);
    return {
      throughput: 0,
      queueLag: 0,
      avgRisk: 0,
      threatMatches: 0,
      errorRate: 0,
      totalRequests: 0,
      succeeded: 0,
      failed: 0,
      avgLatency: 0
    };
  }
}

/**
 * Show toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type: 'info', 'error', 'warning'
 */
function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'error' ? '#fee2e2' : type === 'warning' ? '#fef3c7' : '#dbeafe'};
        color: ${type === 'error' ? '#991b1b' : type === 'warning' ? '#92400e' : '#1e40af'};
        padding: 12px 16px;
        border-radius: 8px;
        z-index: 10000;
        font-size: 14px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        max-width: 300px;
        word-wrap: break-word;
    `;
    
    document.body.appendChild(toast);
    
    // Remove after 5 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 5000);
}

// Export for use in other scripts
window.api = api;
window.toUiRequestRow = toUiRequestRow;
window.toDashboardMetrics = toDashboardMetrics;
window.showToast = showToast;
window.apiConfig = config;
