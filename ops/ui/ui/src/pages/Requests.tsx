import React, { useEffect, useMemo, useState } from "react";
import SuccessRing from "../components/SuccessRing";
import SlideOver from "../components/SlideOver";
import { RequestRow } from "../components/RequestRow";
import { RequestDrawer } from "../components/RequestDrawer";
import { useAdminRequestsPoll } from "../hooks/useAdminRequestsPoll";

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
  const [selected, setSelected] = useState<AuditRow | null>(null);
  const [excludeMonitoring, setExcludeMonitoring] = useState(true);
  const [statusFilter, setStatusFilter] = useState("any");
  const [pathFilter, setPathFilter] = useState("");

  // Use new polling hook with ETag support
  const url = `/v1/admin/requests?exclude_monitoring=${excludeMonitoring}&limit=50&status=${statusFilter}${pathFilter ? `&path=${pathFilter}` : ''}`;
  const rows = useAdminRequestsPoll(url, 10000);

  async function fetchMetrics() {
    try {
      const res = await api.get("/v1/metrics");
      setMetrics(res);
    } catch (error) {
      console.error("Failed to fetch metrics:", error);
    }
  }

  useEffect(() => {
    fetchMetrics();
  }, []);

  const successRate = useMemo(() => {
    if (!metrics) return 0;
    const total = Number(metrics.requests_total ?? 0);
    const failed = Number(metrics.requests_failed ?? 0);
    if (total === 0) return 0;
    return ((total - failed) / total) * 100;
  }, [metrics]);

  const avgLatencyMs = useMemo(() => {
    // if backend doesn't return, estimate from recent rows
    const vals = rows.map(r => r.duration_ms ?? 0).filter(v => v > 0);
    if (!vals.length) return metrics?.avg_latency_ms ?? 0;
    return Math.round(vals.reduce((a,b)=>a+b,0)/vals.length);
  }, [rows, metrics]);

  return (
    <div className="mx-auto max-w-7xl px-6 md:px-10 pb-16">
      {/* Top stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
        <div className="rounded-2xl bg-white/[0.03] border border-white/5 p-6">
          <SuccessRing value={successRate} className="mx-auto" />
        </div>
        <div className="rounded-2xl bg-white/[0.03] border border-white/5 p-6 flex items-center justify-center">
          <div className="text-center">
            <div className="text-sm text-zinc-400 tracking-wide">Avg Latency</div>
            <div className="mt-2 text-5xl font-semibold tracking-tight text-white">
              {fmtLatency(avgLatencyMs)}
            </div>
          </div>
        </div>
      </div>

      {/* Recent requests toolbar */}
      <div className="mt-10 mb-3 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white">Recent Requests</h2>
        <div className="flex items-center gap-3">
          {/* Quick filters */}
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-zinc-400">
              <input
                type="checkbox"
                checked={excludeMonitoring}
                onChange={(e) => setExcludeMonitoring(e.target.checked)}
                className="rounded"
              />
              Hide monitoring
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-white/5 border border-white/10 rounded px-2 py-1 text-sm text-zinc-300"
            >
              <option value="any">All Status</option>
              <option value="2xx">2xx Success</option>
              <option value="4xx">4xx Client Error</option>
              <option value="5xx">5xx Server Error</option>
            </select>
            <input
              type="text"
              placeholder="Filter by path..."
              value={pathFilter}
              onChange={(e) => setPathFilter(e.target.value)}
              className="bg-white/5 border border-white/10 rounded px-2 py-1 text-sm text-zinc-300 w-40"
            />
          </div>
          <button
            onClick={() => fetchMetrics()}
            className="rounded-xl bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25 px-4 py-2 border border-emerald-400/20"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-2xl border border-white/5 bg-white/[0.02]">
        <table className="w-full text-left">
          <thead className="text-zinc-400 text-sm border-b border-white/5">
            <tr>
              <th className="px-5 py-3">Health</th>
              <th className="px-5 py-3">Time</th>
              <th className="px-5 py-3">Method/Path</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3">Latency</th>
              <th className="px-5 py-3">Records</th>
              <th className="px-5 py-3">Client</th>
              <th className="px-5 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {rows.map((r, idx) => (
              <RequestRow
                key={r.id ?? idx}
                item={r}
                onClick={(item) => setSelected(item)}
              />
            ))}
            {!rows.length && (
              <tr>
                <td colSpan={8} className="px-5 py-6 text-center text-zinc-500">
                  No requests yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Request drawer for timeline details */}
      {selected && (
        <RequestDrawer
          item={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
