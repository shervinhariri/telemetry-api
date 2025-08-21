import React, { useEffect, useMemo, useState } from "react";
import DonutGauge from "../components/DonutGauge";
import { PrimaryButton, SecondaryButton } from "../components/ui/Button";

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
const MetricTile = ({ 
  label, 
  value, 
  sub, 
  onClick,
  className = "" 
}: { 
  label: string; 
  value: string; 
  sub?: string;
  onClick?: () => void;
  className?: string;
}) => (
  <div 
    className={cx(
      "rounded-2xl bg-neutral-800/60 p-5 transition ring-1 ring-transparent hover:ring-emerald-500/40 hover:shadow-[0_0_0_2px_rgba(16,185,129,.25)] flex flex-col gap-2",
      onClick && "cursor-pointer",
      className
    )}
    onClick={onClick}
  >
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
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setError("");
    try {
      setLoading(true);
      // Try /system first; fallback to /version
      let sys;
      try { sys = await api.get("/v1/system"); }
      catch { sys = await api.get("/v1/version"); }
      setSystem(sys);
      const met = await api.get("/v1/metrics");
      setMetrics(met);
    } catch (e: any) { 
      setError(String(e.message || e)); 
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);
  useAutoRefresh(load, auto, 5000);

  const avgRisk = useMemo(() => {
    const sum = metrics?.totals?.risk_sum || 0;
    const cnt = metrics?.totals?.risk_count || 0;
    return cnt ? Math.round((sum / cnt) * 10) / 10 : 0;
  }, [metrics]);

  const successRate = useMemo(() => {
    const total = metrics?.requests_total || 0;
    const failed = metrics?.requests_failed || 0;
    return total > 0 ? (total - failed) / total : 0;
  }, [metrics]);

  const errorRate = useMemo(() => {
    const total = metrics?.requests_total || 0;
    const failed = metrics?.requests_failed || 0;
    return total > 0 ? failed / total : 0;
  }, [metrics]);

  return (
    <div className="px-6 md:px-8 py-6 space-y-6">
      {error && <div className="text-xs text-red-400 bg-red-400/10 p-3 rounded-lg">{error}</div>}
      
      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricTile 
          label="Queue Lag" 
          value={numberFmt(metrics?.queue?.lag_ms_p50 ?? 0)} 
          sub="ms (p50)" 
        />
        <MetricTile 
          label="Average Risk" 
          value={numberFmt(avgRisk, 1)} 
          sub="0–100 scale" 
        />
        <MetricTile 
          label="Threat Matches" 
          value={numberFmt(metrics?.totals?.threat_matches ?? 0)} 
          sub="last 15m" 
        />
        <MetricTile 
          label="Success Rate" 
          value={numberFmt(successRate * 100, 1)} 
          sub="overall" 
        />
      </div>

      {/* Donut Gauges */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <div className="flex flex-col items-center">
          <DonutGauge
            value={successRate}
            title="Success Rate"
            loading={loading}
            size={80}
          />
        </div>
        <div className="flex flex-col items-center">
          <DonutGauge
            value={errorRate}
            title="Error Rate"
            loading={loading}
            size={80}
            thresholds={{ green: 0.05, amber: 0.1 }} // Lower is better for errors
          />
        </div>
        <div className="flex flex-col items-center">
          <DonutGauge
            value={avgRisk / 100}
            title="Avg Risk"
            loading={loading}
            size={80}
            thresholds={{ green: 0.3, amber: 0.6 }}
          />
        </div>
        <div className="flex flex-col items-center">
          <DonutGauge
            value={metrics?.queue?.lag_ms_p50 ? Math.min(metrics.queue.lag_ms_p50 / 1000, 1) : 0}
            title="Queue Lag"
            loading={loading}
            size={80}
            thresholds={{ green: 0.1, amber: 0.5 }}
          />
        </div>
      </div>

      {/* System Information */}
      <Card title="System Information" right={
        <div className="flex items-center gap-3 text-xs text-zinc-400">
          <label className="flex items-center gap-1 cursor-pointer select-none">
            <input type="checkbox" className="accent-emerald-400" checked={auto} onChange={(e)=>setAuto(e.target.checked)} />
            Auto-refresh 5s
          </label>
          <SecondaryButton onClick={()=>window.location.reload()}>
            Hard refresh
          </SecondaryButton>
        </div>
      }>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricTile
            label="Version"
            value={String(system?.version || system?.service || '—')}
            sub="Click to open Swagger"
            onClick={() => window.open('/docs', '_blank')}
            className="cursor-pointer"
          />
          <MetricTile
            label="Uptime"
            value={system?.uptime_s ? `${Math.floor(system.uptime_s/3600)}h ${Math.floor((system.uptime_s%3600)/60)}m` : '—'}
            sub="system uptime"
          />
          <MetricTile
            label="Requests"
            value={numberFmt(metrics?.requests_total || 0)}
            sub="total processed"
            onClick={() => window.open('/v1/metrics', '_blank')}
            className="cursor-pointer"
          />
          <MetricTile
            label="Records"
            value={numberFmt(metrics?.totals?.events || 0)}
            sub="total processed"
            onClick={() => window.open('/v1/metrics', '_blank')}
            className="cursor-pointer"
          />
        </div>
      </Card>
    </div>
  );
}
