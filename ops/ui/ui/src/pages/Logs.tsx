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
  const [status, setStatus] = useState("Live logs stopped.");
  const pollRef = useRef<any>(null);

  // Test function to verify button clicks work
  const testClick = () => {
    console.log("Test button clicked!");
    setStatus("Test button works!");
  };

  const startPolling = () => {
    console.log("startPolling called");
    if (pollRef.current) clearInterval(pollRef.current);
    setStatus("Starting live logs...");
    
    pollRef.current = setInterval(async () => {
      try {
        console.log("Polling for logs...");
        const r = await fetch(`${api.base}/v1/logs/tail?max_bytes=50000&format=text`, { headers: api.headers });
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        const text = await r.text();
        const next = text.split('\n').filter(Boolean);
        console.log(`Received ${next.length} log lines`);
        setLines((prev) => [...next.slice(-100), ...prev].slice(0, 500));
        setStatus(`Live logs running. Last update: ${new Date().toLocaleTimeString()}`);
        setError("");
      } catch (e: any) {
        console.error("Polling error:", e);
        setError(String(e.message || e));
        setStatus("Live logs error - check connection.");
      }
    }, 2000);
  };

  const stopPolling = () => { 
    if (pollRef.current) { 
      clearInterval(pollRef.current); 
      pollRef.current = null; 
    } 
  };

  const start = async () => {
    console.log("Start Live button clicked");
    console.log("Current running state:", running);
    console.log("API base:", api.base);
    console.log("API headers:", api.headers);
    
    setError("");
    setRunning(true);
    setStatus("Starting live logs...");
    
    try {
      console.log("Starting polling...");
      // Start polling immediately
      startPolling();
    } catch (e: any) {
      console.error("Error in start function:", e);
      setError(String(e.message || e));
      setStatus("Failed to start live logs.");
      setRunning(false);
    }
  };

  const stop = () => {
    console.log("Stop Live button clicked");
    stopPolling();
    setRunning(false);
    setStatus("Live logs stopped.");
  };

  const download = async () => {
    try {
      setStatus("Downloading logs...");
      const r = await fetch(`${api.base}/v1/logs/tail?max_bytes=2000000&format=text`, { headers: api.headers });
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      const blob = await r.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `telemetry-logs-${Date.now()}.txt`;
      a.click();
      setStatus("Logs downloaded successfully.");
    } catch (e: any) { 
      setError(String(e.message || e)); 
      setStatus("Download failed.");
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
      }
    };
  }, []);

  return (
    <div className="mt-6 space-y-4">
      {error && <div className="text-xs text-red-400">{error}</div>}
      <div className="flex items-center gap-3">
        <button onClick={testClick} className="rounded-xl px-3 py-2 text-sm bg-blue-500/15 text-blue-200 ring-1 ring-blue-500/30 hover:bg-blue-500/20">Test Button</button>
        <button onClick={start} 
          className={cx("rounded-xl px-3 py-2 text-sm ring-1",
            running ? "opacity-40 cursor-not-allowed bg-[#14151B] ring-white/5" : "bg-emerald-500/15 ring-emerald-500/30 text-emerald-200 hover:bg-emerald-500/20")}>Start Live</button>
        <button onClick={stop} className="rounded-xl px-3 py-2 text-sm bg-rose-500/15 text-rose-200 ring-1 ring-rose-500/30 hover:bg-rose-500/20">Stop Live</button>
        <button onClick={download} className="rounded-xl px-3 py-2 text-sm bg-indigo-500/15 text-indigo-200 ring-1 ring-indigo-500/30 hover:bg-indigo-500/20">Download (2MB)</button>
      </div>
      <div className="text-xs text-zinc-400">{status}</div>
      <Card title="Live Logs">
        <div className="h-[60vh] overflow-auto font-mono text-[11px] leading-relaxed">
          {lines.length === 0 && <div className="text-zinc-500">No logs yet. Click "Start Live" to begin streaming.</div>}
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
