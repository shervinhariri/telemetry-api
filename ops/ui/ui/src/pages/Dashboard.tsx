import React, { useEffect, useMemo, useState } from "react";

// ---------- Small helpers ----------
const cx = (...list: (string | boolean | undefined)[]) => list.filter(Boolean).join(" ");

const numberFmt = (n: number | null | undefined, d = 0) => {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  const nf = new Intl.NumberFormat(undefined, { maximumFractionDigits: d });
  return nf.format(n);
};

function useAutoRefresh(cb: () => void, enabled: boolean, intervalMs: number) {
  const savedCb = React.useRef(cb);
  React.useEffect(() => { savedCb.current = cb; }, [cb]);
  React.useEffect(() => {
    if (!enabled) return;
    const id = setInterval(() => savedCb.current?.(), intervalMs);
    return () => clearInterval(id);
  }, [enabled, intervalMs]);
}

// ---------- UI atoms ----------
const MetricTile = ({ label, value, sub }: { label: string; value: string; sub?: string }) => (
  <div className="rounded-2xl bg-neutral-800/60 p-5 transition ring-1 ring-transparent hover:ring-emerald-500/40 hover:shadow-[0_0_0_2px_rgba(16,185,129,.25)] flex flex-col gap-2">
    <div className="text-xs uppercase tracking-wide text-zinc-400">{label}</div>
    <div className="text-4xl font-semibold leading-none">{value}</div>
    {sub && <div className="text-xs text-zinc-500">{sub}</div>}
  </div>
);

const Card = ({ title, right, children }: { title: string; right?: React.ReactNode; children: React.ReactNode }) => (
  <div className="rounded-2xl bg-[#111218] ring-1 ring-white/5 p-6">
    <div className="mb-4 flex items-center justify-between">
      <div className="text-sm text-zinc-300">{title}</div>
      {right}
    </div>
    {children}
  </div>
);

export default function Dashboard({ api, auto, setAuto }: { api: any; auto: boolean; setAuto: (auto: boolean) => void }) {
  const [system, setSystem] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try {
      // Try /system first; fallback to /version
      let sys;
      try { sys = await api.get("/v1/system"); }
      catch { sys = await api.get("/v1/version"); }
      setSystem(sys);
      const met = await api.get("/v1/metrics");
      setMetrics(met);
    } catch (e: any) { setError(String(e.message || e)); }
  };

  useEffect(() => { load(); }, []);
  useAutoRefresh(load, auto, 5000);

  const avgRisk = useMemo(() => {
    const sum = metrics?.totals?.risk_sum || 0;
    const cnt = metrics?.totals?.risk_count || 0;
    return cnt ? Math.round((sum / cnt) * 10) / 10 : 0;
  }, [metrics]);

  return (
    <div className="mt-6 space-y-4">
      {error && <div className="text-xs text-red-400">{error}</div>}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricTile label="Queue Lag" value={numberFmt(metrics?.queue?.lag_ms_p50 ?? 0)} sub="ms (p50)" />
        <MetricTile label="Average Risk" value={numberFmt(avgRisk, 1)} sub="0–100 scale" />
        <MetricTile label="Threat Matches" value={numberFmt(metrics?.totals?.threat_matches ?? 0)} sub="last 15m" />
        <MetricTile label="Error Rate" value={`${numberFmt(((metrics?.requests_failed||0)/(metrics?.requests_total||1))*100,1)}%`} sub="overall" />
      </div>

      <Card title="System Information" right={
        <div className="flex items-center gap-3 text-xs text-zinc-400">
          <label className="flex items-center gap-1 cursor-pointer select-none">
            <input type="checkbox" className="accent-indigo-400" checked={auto} onChange={(e)=>setAuto(e.target.checked)} />
            Auto-refresh 5s
          </label>
          <button onClick={()=>window.location.reload()} className="rounded-lg px-2 py-1 ring-1 ring-white/10 hover:ring-indigo-400/40">Hard refresh</button>
        </div>
      }>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <button
            onClick={()=>window.open('/docs','_blank')}
            className="w-full text-left rounded-2xl bg-neutral-800/60 p-5 transition ring-1 ring-transparent hover:ring-emerald-500/40 hover:shadow-[0_0_0_2px_rgba(16,185,129,.25)] focus:outline-none focus:ring-emerald-500/60">
            <div className="text-xs uppercase tracking-wide text-zinc-400">Version</div>
            <div className="text-2xl mt-1 font-semibold">{String(system?.version || system?.service || '—')}</div>
            <div className="text-xs mt-2 text-zinc-500">Click to open Swagger</div>
          </button>
          <div className="rounded-2xl bg-neutral-800/60 p-5 transition ring-1 ring-transparent hover:ring-emerald-500/40 hover:shadow-[0_0_0_2px_rgba(16,185,129,.25)] flex flex-col gap-2">
            <div className="text-xs uppercase tracking-wide text-zinc-400">Uptime</div>
            <div className="text-2xl font-semibold leading-none">{system?.uptime_s ? `${Math.floor(system.uptime_s/3600)}h ${Math.floor((system.uptime_s%3600)/60)}m` : '—'}</div>
          </div>
        </div>
      </Card>
    </div>
  );
}
