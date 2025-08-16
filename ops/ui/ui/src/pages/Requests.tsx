import React, { useEffect, useMemo, useState } from "react";
import SuccessRing from "../components/SuccessRing";
import SlideOver from "../components/SlideOver";

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
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<AuditRow | null>(null);
  const [loading, setLoading] = useState(false);

  async function fetchMetrics() {
    try {
      const res = await api.get("/v1/metrics");
      setMetrics(res);
    } catch (error) {
      console.error("Failed to fetch metrics:", error);
    }
  }

  async function fetchRequests() {
    setLoading(true);
    try {
      let res;
      try {
        res = await api.get("/v1/requests?limit=50");
      } catch {
        res = await api.get("/v1/audit/requests?limit=50");
      }
      setRows(Array.isArray(res) ? res : (res.items ?? []));
    } catch (error) {
      console.error("Failed to fetch requests:", error);
    }
    setLoading(false);
  }

  useEffect(() => {
    fetchMetrics();
    fetchRequests();
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
          <button
            onClick={() => { fetchMetrics(); fetchRequests(); }}
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
              <th className="px-5 py-3">Time</th>
              <th className="px-5 py-3">Endpoint</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3">Latency</th>
              <th className="px-5 py-3">Records</th>
              <th className="px-5 py-3">Client</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {rows.map((r, idx) => {
              const dt = r.ts ? new Date(r.ts) : null;
              const statusColor =
                (r.status ?? 0) >= 500 ? "bg-rose-500/20 text-rose-300 border-rose-400/30" :
                (r.status ?? 0) >= 400 ? "bg-amber-500/20 text-amber-300 border-amber-400/30" :
                "bg-emerald-500/20 text-emerald-300 border-emerald-400/30";
              return (
                <tr
                  key={r.id ?? idx}
                  className="hover:bg-white/[0.04] cursor-pointer"
                  onClick={() => { setSelected(r); setOpen(true); }}
                >
                  <td className="px-5 py-3 text-sm text-zinc-300">
                    {dt ? dt.toLocaleTimeString() : "—"}
                  </td>
                  <td className="px-5 py-3 text-sm text-white">
                    <span className="text-zinc-400 mr-2">{r.method}</span>{r.path}
                  </td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-lg text-xs border ${statusColor}`}>
                      {r.status ?? "—"}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-sm text-zinc-300">{fmtLatency(r.duration_ms)}</td>
                  <td className="px-5 py-3 text-sm text-zinc-300">{r.records ?? 0}</td>
                  <td className="px-5 py-3 text-sm text-zinc-300">
                    {countryFlag(r.geo_country)} {r.client_ip ?? "—"}
                  </td>
                </tr>
              );
            })}
            {!rows.length && (
              <tr>
                <td colSpan={6} className="px-5 py-6 text-center text-zinc-500">
                  {loading ? "Loading…" : "No requests yet"}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Slide-over for details */}
      <SlideOver
        open={open}
        onClose={() => setOpen(false)}
        title="Request Details"
        width={560}
      >
        {!selected ? null : (
          <div className="space-y-6">
            {/* summary chips */}
            <div className="flex flex-wrap gap-2">
              <Chip label="Status" value={String(selected.status ?? "—")}
                tone={(selected.status ?? 0) >= 500 ? "danger" :
                      (selected.status ?? 0) >= 400 ? "warn" : "ok"} />
              <Chip label="Method" value={selected.method ?? "—"} />
              <Chip label="Latency" value={fmtLatency(selected.duration_ms)} />
              <Chip label="Records" value={String(selected.records ?? 0)} />
              <Chip label="Endpoint" value={selected.path ?? "—"} />
              <Chip label="Source IP" value={`${countryFlag(selected.geo_country)} ${selected.client_ip ?? "—"}`} />
              <Chip label="Country" value={selected.geo_country ?? "—"} />
              <Chip label="ASN" value={String(selected.asn ?? "—")} />
              <Chip label="Tenant" value={selected.tenant_id ?? "—"} />
              <Chip label="API Key" value={(selected.api_key_hash ?? "—").slice(0, 8)} />
              <Chip label="Trace ID" value={selected.trace_id ?? "—"} />
              {selected.risk_avg != null && <Chip label="Avg Risk" value={String(selected.risk_avg)} />}
            </div>

            {/* JSON viewer */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-medium text-zinc-300">Raw JSON</div>
                <button
                  onClick={() => navigator.clipboard.writeText(JSON.stringify(selected, null, 2))}
                  className="px-3 py-1.5 text-sm rounded-md bg-white/5 hover:bg-white/10 text-zinc-200"
                >
                  Copy
                </button>
              </div>
              <pre className="bg-black/40 border border-white/10 rounded-xl p-4 overflow-auto text-xs leading-relaxed text-zinc-300">
{JSON.stringify(selected, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </SlideOver>
    </div>
  );
}
