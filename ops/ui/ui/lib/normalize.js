/**
 * Normalization utilities for API data
 * Handles property name variations and provides fallbacks
 */

/**
 * Normalize metrics data from API
 * @param {Object} raw - Raw API response
 * @returns {Object} Normalized metrics
 */
window.normalizeMetrics = function(raw) {
  // Accept both snake_case and camelCase
  const get = (o, ...keys) => keys.find(k => k in o) ? o[keys.find(k => k in o)] : undefined;
  
  const total = get(raw, 'requests_total', 'requestsTotal') ?? 0;
  const failed = get(raw, 'requests_failed', 'requestsFailed') ?? 0;
  const succeeded = get(raw, 'requests_succeeded', 'requestsSucceeded') ?? (total - failed);
  const avgLatency = get(raw, 'latency_avg', 'avg_latency', 'avgLatencyMs') ?? 0;
  const queueLag = get(raw, 'queue_lag', 'queue_depth', 'queueDepth') ?? 0;
  const avgRisk = get(raw, 'avg_risk', 'risk_avg', 'riskAvg') ?? 0;
  const threatMatches = get(raw, 'threat_matches', 'threatMatches15m', 'threatMatches') ?? 0;
  const errorRate = get(raw, 'error_rate', 'errorRatePct', 'error_rate_pct') ?? (total ? (failed / total * 100) : 0);

  // Extract from totals if available
  const events = get(raw, 'totals.events', 'events') ?? 0;
  const riskSum = get(raw, 'totals.risk_sum', 'riskSum') ?? 0;
  const riskCount = get(raw, 'totals.risk_count', 'riskCount') ?? 0;
  
  // Calculate average risk from totals if available
  const calculatedAvgRisk = riskCount > 0 ? (riskSum / riskCount) : avgRisk;

  // time series arrays (accept several names; default to empty)
  const throughput = get(raw, 'timeseries.last_5m.eps', 'throughput', 'events_per_sec', 'eventsPerSec') ?? [];
  const eventsPerMin = get(raw, 'timeseries.last_5m.epm', 'events_per_min', 'eventsPerMinute', 'eventsPerMin') ?? [];

  return { 
    total, 
    failed, 
    succeeded, 
    avgLatency, 
    queueLag, 
    avgRisk: calculatedAvgRisk, 
    threatMatches, 
    errorRate, 
    throughput, 
    eventsPerMin,
    events,
    riskSum,
    riskCount
  };
}

/**
 * Normalize requests data from API
 * @param {Object} raw - Raw API response
 * @returns {Object} Normalized requests data
 */
window.normalizeRequests = function(raw) {
  // Ensure we return a flat array of entries with time, method, path, status, latencyMs, sourceIp, records, riskAvg, requestId
  // Map snake/camel and provide defaults
  const rows = Array.isArray(raw?.items || raw?.data || raw) ? (raw.items || raw.data || raw) : [];
  return rows.map(r => ({
    time: r.time || r.ts || r.timestamp || null,
    method: r.method || r.verb || '',
    path: r.path || r.endpoint || '',
    status: r.status || r.code || 0,
    latencyMs: r.latency_ms || r.latencyMs || r.duration_ms || 0,
    sourceIp: r.source_ip || r.client_ip || r.clientIp || '',
    records: r.records || r.records_processed || 0,
    riskAvg: r.risk_avg || r.avg_risk || 0,
    requestId: r.id || r.request_id || r.reqId || ''
  }));
}

/**
 * Normalize system data from API
 * @param {Object} raw - Raw API response
 * @returns {Object} Normalized system data
 */
window.normalizeSystem = function(raw) {
  // Show bounded JSON; tolerate null/empty
  if (!raw) return { status: 'unknown' };
  
  return {
    version: raw.version || 'unknown',
    uptime: raw.uptime_s || 0,
    queueDepth: raw.queue_depth || 0,
    backpressure: raw.backpressure || false,
    dlq: raw.dlq || {},
    idempotency: raw.idempotency || {},
    lastErrors: raw.last_errors || []
  };
}

/**
 * Safe number formatting with fallback
 * @param {number} value - Value to format
 * @param {number} fallback - Fallback value if NaN
 * @returns {string} Formatted number
 */
window.safeNumber = function(value, fallback = 0) {
  const num = Number(value);
  return isNaN(num) ? fallback.toString() : num.toString();
}

/**
 * Safe percentage formatting
 * @param {number} value - Value to format as percentage
 * @param {number} fallback - Fallback value if NaN
 * @returns {string} Formatted percentage
 */
window.safePercentage = function(value, fallback = 0) {
  const num = Number(value);
  return isNaN(num) ? `${fallback}%` : `${num.toFixed(1)}%`;
}
