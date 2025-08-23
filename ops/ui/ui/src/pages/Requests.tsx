import React, { useEffect, useMemo, useState } from "react";
import SuccessRing from "../components/SuccessRing";
import SlideOver from "../components/SlideOver";
import DonutGauge from "../components/DonutGauge";
import { RequestRow } from "../components/RequestRow";
import { RequestDrawer } from "../components/RequestDrawer";
import RequestDetailsSlideOver from "../components/RequestDetailsSlideOver";
import { PrimaryButton, SecondaryButton } from "../components/ui/Button";
import { useAdminRequestsPoll } from "../hooks/useAdminRequestsPoll";

type AuditItem = {
  id: string;
  ts: string;
  method: string;
  path: string;
  status: number;
  latency_ms?: number;
  summary?: { records?: number };
  client_ip?: string;
  fitness?: number;
  timeline?: any[];
};

type AuditRow = {
  id?: string;
  ts?: string;                  // ISO
  method?: string;
  path?: string;
  status?: number;
  duration_ms?: number;
  records?: number;
  client_ip?: string;
  user_agent?: string;
  trace_id?: string;
  tenant_id?: string;
  api_key_hash?: string;
  geo_country?: string;         // e.g. "PL"
  asn?: string | number;
  risk_avg?: number;
  // ... any other backend fields
};

function countryFlag(cc?: string) {
  if (!cc) return "🏳️";
  const code = cc.trim().toUpperCase();
  if (code.length !== 2) return "🏳️";
  const A = 0x1f1e6; // regional indicator A
  return String.fromCodePoint(...[...code].map(c => A + (c.charCodeAt(0) - 65)));
}

function fmtLatency(ms?: number) {
  if (ms == null) return "—";
  return `${ms}ms`;
}

function fitnessReason(it: AuditItem): string {
  const s = it.status ?? 0;
  const tl = it.timeline ?? [];
  const v = tl.find((x: any) => x.event === "validated");
  if (v && v.meta && v.meta.ok === false) return "Validation failed";
  const e = tl.find((x: any) => x.event === "exported");
  if (e && e.meta) {
    const bad: string[] = [];
    for (const k of ["splunk", "elastic"]) {
      const v = (e.meta as any)[k];
      if (v && String(v).toLowerCase() !== "ok" && String(v).toLowerCase() !== "success") bad.push(k);
    }
    if (bad.length) return `Export failure: ${bad.join(", ")}`;
  }
  if (typeof s === "number" && s >= 400) return `HTTP ${s}`;
  return "Healthy";
}

/* ---------- small chip component ---------- */
function Chip({ label, value, tone = "default" }:{
  label: string; value: string; tone?: "default"|"ok"|"warn"|"danger";
}) {
  const styles = {
    default: "bg-white/5 text-zinc-200 border-white/10",
    ok:      "bg-emerald-500/15 text-emerald-300 border-emerald-400/20",
    warn:    "bg-amber-500/15 text-amber-300 border-amber-400/20",
    danger:  "bg-rose-500/15 text-rose-300 border-rose-400/20",
  }[tone];
  return (
    <div className={`px-3 py-1.5 rounded-lg border ${styles}`}>
      <span className="mr-2 text-xs uppercase tracking-wide text-zinc-400">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}

export default function Requests({ api }: { api: any }) {
  const [metrics, setMetrics] = useState<any>(null);
  const [selected, setSelected] = useState<AuditItem | null>(null);
  const [selectedRequest, setSelectedRequest] = useState<any>(null);
  const [excludeMonitoring, setExcludeMonitoring] = useState(true);
  const [statusFilter, setStatusFilter] = useState("any");
  const [pathFilter, setPathFilter] = useState("");

  // Get API key from your existing global store / context / localStorage
  // (adjust if you already have a selector for it)
  const apiKey = (window as any).API_KEY || "TEST_KEY";
  const headers = useMemo(
    () => ({ Authorization: `Bearer ${apiKey}` }),
    [apiKey]
  );

  const { data: requests, loading, error, refetch } = useAdminRequestsPoll(api, headers);

  const load = async () => {
    try {
      const met = await api.get("/v1/metrics");
      setMetrics(met);
    } catch (e: any) {
      console.error("Failed to load metrics:", e);
    }
  };

  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    if (!requests) return [];
    let filtered = requests;
    
    if (excludeMonitoring) {
      filtered = filtered.filter((r: any) => !r.path?.includes("/v1/metrics") && !r.path?.includes("/v1/system"));
    }
    
    if (statusFilter !== "any") {
      const status = parseInt(statusFilter);
      filtered = filtered.filter((r: any) => r.status === status);
    }
    
    if (pathFilter) {
      filtered = filtered.filter((r: any) => r.path?.toLowerCase().includes(pathFilter.toLowerCase()));
    }
    
    return filtered.slice(0, 100); // Limit to 100 most recent
  }, [requests, excludeMonitoring, statusFilter, pathFilter]);

  const handleRequestClick = (request: any) => {
    setSelectedRequest({
      timestamp: request.ts,
      method: request.method,
      path: request.path,
      status: request.status,
      latency_ms: request.latency_ms || request.duration_ms || 0,
      trace_id: request.trace_id || request.id,
      tenant_id: request.tenant_id || 'unknown',
      client_ip: request.client_ip || 'unknown',
      enrichment: {
        src_ip: request.src_ip,
        dst_ip: request.dst_ip,
        country: request.geo_country,
        asn: request.asn,
        risk: request.risk_avg,
      }
    });
  };

  const handleOpenInLogs = (traceId: string) => {
    // Navigate to logs page with trace filter
    window.location.hash = `#/logs?trace_id=${traceId}`;
    setSelectedRequest(null);
  };

  return (
    <div className="px-6 md:px-8 py-6 space-y-6">
      {/* Header with improved spacing */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Recent Requests</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Monitor API requests and their performance
          </p>
        </div>
        <div className="flex items-center gap-3">
          <SecondaryButton onClick={refetch} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </SecondaryButton>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-center">
        <label className="flex items-center gap-2 text-sm text-zinc-300">
          <input
            type="checkbox"
            checked={excludeMonitoring}
            onChange={(e) => setExcludeMonitoring(e.target.checked)}
            className="accent-emerald-400"
          />
          Exclude monitoring
        </label>
        
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-neutral-800 border border-neutral-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
        >
          <option value="any">Any Status</option>
          <option value="200">200 OK</option>
          <option value="400">400 Bad Request</option>
          <option value="401">401 Unauthorized</option>
          <option value="500">500 Server Error</option>
        </select>
        
        <input
          type="text"
          placeholder="Filter by path..."
          value={pathFilter}
          onChange={(e) => setPathFilter(e.target.value)}
          className="bg-neutral-800 border border-neutral-600 rounded-lg px-3 py-1.5 text-sm text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
        />
      </div>

      {/* Metrics Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-2xl bg-neutral-800/60 p-5">
          <div className="text-xs uppercase tracking-wide text-zinc-400 mb-2">Total Requests</div>
          <div className="text-2xl font-semibold text-white">{metrics?.requests_total || 0}</div>
        </div>
        <div className="rounded-2xl bg-neutral-800/60 p-5">
          <div className="text-xs uppercase tracking-wide text-zinc-400 mb-2">Success Rate</div>
          <div className="text-2xl font-semibold text-white">
            {metrics?.requests_total ? 
              `${Math.round(((metrics.requests_total - (metrics.requests_failed || 0)) / metrics.requests_total) * 100)}%` : 
              '0%'
            }
          </div>
        </div>
        <div className="rounded-2xl bg-neutral-800/60 p-5">
          <div className="text-xs uppercase tracking-wide text-zinc-400 mb-2">Avg Latency</div>
          <div className="text-2xl font-semibold text-white">
            {metrics?.latency_ms_avg ? `${Math.round(metrics.latency_ms_avg)}ms` : '—'}
          </div>
        </div>
        <div className="rounded-2xl bg-neutral-800/60 p-5">
          <div className="text-xs uppercase tracking-wide text-zinc-400 mb-2">Recent</div>
          <div className="text-2xl font-semibold text-white">{filtered.length}</div>
        </div>
      </div>

      {/* Requests Table */}
      <div className="rounded-2xl bg-[#111218] ring-1 ring-white/5 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-neutral-800/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Time</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Method</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Path</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Latency</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Trace ID</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-700">
              {filtered.map((request: any, index: number) => (
                <tr 
                  key={request.id || index}
                  onClick={() => handleRequestClick(request)}
                  className="hover:bg-neutral-800/30 cursor-pointer transition-colors"
                >
                  <td className="px-6 py-4 text-sm text-zinc-300">
                    {new Date(request.ts).toLocaleTimeString()}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded ${
                      request.method === 'GET' ? 'bg-blue-500/20 text-blue-300' :
                      request.method === 'POST' ? 'bg-green-500/20 text-green-300' :
                      request.method === 'PUT' ? 'bg-yellow-500/20 text-yellow-300' :
                      request.method === 'DELETE' ? 'bg-red-500/20 text-red-300' :
                      'bg-neutral-500/20 text-neutral-300'
                    }`}>
                      {request.method}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-zinc-300 font-mono">
                    {request.path}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded ${
                      request.status >= 200 && request.status < 300 ? 'bg-green-500/20 text-green-300' :
                      request.status >= 400 && request.status < 500 ? 'bg-yellow-500/20 text-yellow-300' :
                      request.status >= 500 ? 'bg-red-500/20 text-red-300' :
                      'bg-neutral-500/20 text-neutral-300'
                    }`}>
                      {request.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-zinc-300">
                    {fmtLatency(request.latency_ms || request.duration_ms)}
                  </td>
                  <td className="px-6 py-4 text-sm text-emerald-300 font-mono">
                    {request.trace_id || request.id}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {filtered.length === 0 && (
          <div className="px-6 py-12 text-center text-zinc-400">
            {loading ? 'Loading requests...' : 'No requests found'}
          </div>
        )}
      </div>

      {/* Request Details SlideOver */}
      <RequestDetailsSlideOver
        request={selectedRequest}
        isOpen={!!selectedRequest}
        onClose={() => setSelectedRequest(null)}
        onOpenInLogs={handleOpenInLogs}
      />
    </div>
  );
}
