import React, { useEffect, useMemo, useState } from "react";
import SuccessRing from "../components/SuccessRing";
import SlideOver from "../components/SlideOver";
import DonutGauge from "../components/DonutGauge";
import { RequestRow } from "../components/RequestRow";
import { RequestDrawer } from "../components/RequestDrawer";
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

  async function sendDemoIngest(authHeader: string) {
    await fetch("/v1/ingest", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: authHeader,
      },
      body: JSON.stringify({
        collector_id: "demo",
        format: "flows.v1",
        records: [{
          ts: 1723351200.456,
          src_ip: "10.0.0.1",
          dst_ip: "1.1.1.1",
          src_port: 12345,
          dst_port: 80,
          protocol: "tcp",
          bytes: 256,
          packets: 2,
        }]
      })
    });
  }

  // Use new polling hook with ETag support
  const qs = `exclude_monitoring=${excludeMonitoring}&limit=50${statusFilter !== "any" ? `&status=${statusFilter}` : ""}${pathFilter ? `&path=${pathFilter}` : ""}`;
  const { items, refresh } = useAdminRequestsPoll(
    `/v1/admin/requests?${qs}`,
    10000,
    headers
  );
  const rows: AuditItem[] = useMemo(() => (items || []) as AuditItem[], [items]);

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
    const vals = rows.map(r => r.latency_ms ?? 0).filter(v => v > 0);
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
            <div className="mt-2 text-3xl md:text-4xl font-semibold tracking-tight text-white">
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
            className="rounded-md bg-blue-600 px-3 py-1.5 text-white text-sm hover:bg-blue-700"
            onClick={async () => { await sendDemoIngest(headers.Authorization!); refresh(); }}
            title="Send a demo ingest request"
          >
            Send demo ingest
          </button>
          <button
            onClick={() => { fetchMetrics(); refresh(); }}
            className="rounded-xl bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25 px-4 py-2 border border-emerald-400/20"
            title="Force refresh (busts ETag)"
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
            {rows.length === 0 && (
              <tr>
                <td colSpan={8} className="px-5 py-6 text-center text-zinc-500">
                  No recent business requests yet. Send an <code>/v1/ingest</code> to populate.
                </td>
              </tr>
            )}
            {rows.map((it) => (
              <tr
                key={it.id}
                className="hover:bg-gray-900/30 cursor-pointer"
                onClick={() => setSelected(it)}
              >
                <td className="px-5 py-3">
                  {Number.isFinite(it.fitness as number) ? <DonutGauge value={it.fitness ?? 0} title={fitnessReason(it)} /> : <span>—</span>}
                </td>
                <td className="px-5 py-3 text-sm text-zinc-300">
                  {new Date(it.ts).toLocaleTimeString()}
                </td>
                <td className="px-5 py-3 text-sm">
                  <span className="font-medium">{it.method}</span>{" "}
                  <span className="text-zinc-400">{it.path}</span>
                </td>
                <td className="px-5 py-3">
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    it.status >= 500 ? "bg-red-500/20 text-red-300"
                    : it.status >= 400 ? "bg-amber-500/20 text-amber-300"
                    : "bg-emerald-500/20 text-emerald-300"
                  }`}>{it.status}</span>
                </td>
                <td className="px-5 py-3 text-sm text-zinc-300">
                  {Number.isFinite(it.latency_ms as number) ? `${Math.round(it.latency_ms as number)} ms` : "—"}
                </td>
                <td className="px-5 py-3 text-sm text-zinc-300">{it.summary?.records ?? 0}</td>
                <td className="px-5 py-3 text-sm text-zinc-300">{it.client_ip ?? "—"}</td>
                <td className="px-5 py-3 text-right text-zinc-500">›</td>
              </tr>
            ))}
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

      {/* Legend */}
      <div className="mt-6 mb-2 flex items-center justify-center gap-6 text-xs text-zinc-500">
        <span className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
          <span className="font-medium">≥90%</span>
        </span>
        <span className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-amber-500"></div>
          <span className="font-medium">≥60%</span>
        </span>
        <span className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-red-500"></div>
          <span className="font-medium">&lt;60%</span>
        </span>
      </div>
    </div>
  );
}
