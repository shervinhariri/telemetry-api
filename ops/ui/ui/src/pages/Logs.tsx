import React, { useEffect, useRef, useState } from "react";

// ---------- UI atoms ----------
const Card = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div className="rounded-2xl bg-[#111218] ring-1 ring-white/5 p-6">
    <div className="mb-4 flex items-center justify-between">
      <div className="text-sm text-zinc-300">{title}</div>
    </div>
    {children}
  </div>
);

const cx = (...list: (string | boolean | undefined)[]) => list.filter(Boolean).join(" ");

export default function Logs({ api }: { api: any }) {
  const [lines, setLines] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const ctrlRef = useRef<EventSource | null>(null);
  const pollRef = useRef<any>(null);

  const startPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const r = await fetch(`${api.base}/v1/logs/tail?max_bytes=50000&format=text`, { headers: api.headers });
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        const text = await r.text();
        const next = text.split('\n').filter(Boolean);
        setLines((prev) => [...next.slice(-100), ...prev].slice(0, 500));
      } catch (e: any) {
        setError(String(e.message || e));
      }
    }, 2000);
  };

  const stopPolling = () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };

  const start = async () => {
    setError("");
    setRunning(true);
    try {
      // Prefer SSE at /v1/admin/requests/stream; fallback to polling
      const sse = new EventSource((api.base || "") + "/v1/admin/requests/stream");
      ctrlRef.current = sse;
      sse.onmessage = (e) => { setLines((prev) => [e.data, ...prev].slice(0, 500)); };
      sse.onerror = () => { sse.close(); ctrlRef.current = null; startPolling(); };
    } catch (e: any) {
      setError(String(e.message || e));
      startPolling();
    }
  };

  const stop = () => {
    const sse = ctrlRef.current;
    if (sse && sse.close) sse.close();
    ctrlRef.current = null;
    stopPolling();
    setRunning(false);
  };

  const download = async () => {
    try {
      const r = await fetch(`${api.base}/v1/logs/tail?max_bytes=2000000&format=text`, { headers: api.headers });
      const blob = await r.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `telemetry-logs-${Date.now()}.txt`;
      a.click();
    } catch (e: any) { setError(String(e.message || e)); }
  };

  return (
    <div className="mt-6 space-y-4">
      {error && <div className="text-xs text-red-400">{error}</div>}
      <div className="flex items-center gap-3">
        <button onClick={running ? undefined : start} disabled={running}
          className={cx("rounded-xl px-3 py-2 text-sm ring-1",
            running ? "opacity-40 cursor-not-allowed bg-[#14151B] ring-white/5" : "bg-emerald-500/15 ring-emerald-500/30 text-emerald-200 hover:bg-emerald-500/20")}>Start Live</button>
        <button onClick={stop} className="rounded-xl px-3 py-2 text-sm bg-rose-500/15 text-rose-200 ring-1 ring-rose-500/30 hover:bg-rose-500/20">Stop Live</button>
        <button onClick={download} className="rounded-xl px-3 py-2 text-sm bg-indigo-500/15 text-indigo-200 ring-1 ring-indigo-500/30 hover:bg-indigo-500/20">Download (2MB)</button>
      </div>
      <Card title="Live Logs">
        <div className="h-[60vh] overflow-auto font-mono text-[11px] leading-relaxed">
          {lines.length === 0 && <div className="text-zinc-500">No logs yet.</div>}
          {lines.map((l, i) => (
            <div key={i} className={cx(
              "whitespace-pre-wrap",
              l.includes("ERROR") ? "text-red-300" : l.includes("WARN") ? "text-amber-300" : "text-zinc-300"
            )}>{l}</div>
          ))}
        </div>
      </Card>
    </div>
  );
}
