import React, { useEffect, useRef, useState } from "react";
import { PrimaryButton, SecondaryButton } from "../components/ui/Button";

// ---------- UI atoms ----------
const Card = ({ title, children, right }: { title: string; children: React.ReactNode; right?: React.ReactNode }) => (
  <div className="rounded-2xl bg-neutral-800/60 ring-1 ring-white/5 p-6">
    <div className="mb-4 flex items-center justify-between">
      <div className="text-sm text-zinc-300 font-medium">{title}</div>
      {right}
    </div>
    {children}
  </div>
);

const cx = (...list: (string | boolean | undefined)[]) => list.filter(Boolean).join(" ");

interface LogEntry {
  timestamp: string;
  level: string;
  logger: string;
  msg: string;
  trace_id?: string;
  method?: string;
  path?: string;
  status?: number;
  latency_ms?: number;
  client_ip?: string;
  tenant_id?: string;
  component?: string;
  [key: string]: any;
}

export default function Logs({ api }: { api: any }) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("Live logs stopped.");
  const [filters, setFilters] = useState({
    level: "",
    endpoint: "",
    traceId: "",
    text: ""
  });
  const eventSourceRef = useRef<EventSource | null>(null);

  // Filter logs based on current filters
  const filteredLogs = logs.filter(log => {
    if (filters.level && log.level !== filters.level.toUpperCase()) return false;
    if (filters.endpoint && log.path && !log.path.includes(filters.endpoint)) return false;
    if (filters.traceId && log.trace_id !== filters.traceId) return false;
    if (filters.text && !log.msg.toLowerCase().includes(filters.text.toLowerCase())) return false;
    return true;
  });

  const startStreaming = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setStatus("Starting live logs...");
    
    // EventSource cannot send custom headers. We pass the API key via querystring (?key=)
    // The backend accepts either Authorization header (for non-browser clients) or ?key=
    const keyFromState = api?.key || localStorage.getItem('api_key') || '';
    const url = `${api.base}/v1/logs/stream?key=${encodeURIComponent(keyFromState)}`;
    const eventSource = new EventSource(url);
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("SSE received:", data);
        setLogs(prev => [data, ...prev].slice(0, 1000));
        setStatus(`Live logs running. Last update: ${new Date().toLocaleTimeString()}`);
        setError("");
      } catch (e: any) {
        console.error("SSE parsing error:", e);
        setError(String(e.message || e));
      }
    };
    
    eventSource.onerror = (event) => {
      console.error("SSE error:", event);
      setError("SSE connection error");
      setStatus("Live logs error - check connection.");
      eventSource.close();
    };
    
    eventSourceRef.current = eventSource;
  };

  const stopStreaming = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setRunning(false);
    setStatus("Live logs stopped.");
  };

  const stopStreaming = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setRunning(false);
    setStatus("Live logs stopped.");
  };

  const download = async () => {
    try {
      setStatus("Downloading logs...");
      const r = await fetch(`${api.base}/v1/logs/download`, { 
        headers: api.headers 
      });
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      const blob = await r.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `telemetry-logs-${Date.now()}.jsonl`;
      a.click();
      setStatus("Logs downloaded successfully.");
    } catch (e: any) { 
      setError(String(e.message || e)); 
      setStatus("Download failed.");
    }
  };

  const clearLogs = () => {
    setLogs([]);
    setStatus("Logs cleared.");
  };

  const copyTraceId = (traceId: string) => {
    navigator.clipboard.writeText(traceId);
    setStatus(`Trace ID ${traceId} copied to clipboard.`);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const getLevelColor = (level: string) => {
    switch (level.toUpperCase()) {
      case 'ERROR': return 'text-red-300';
      case 'WARNING': return 'text-amber-300';
      case 'INFO': return 'text-blue-300';
      case 'DEBUG': return 'text-zinc-400';
      default: return 'text-zinc-300';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString();
    } catch {
      return timestamp;
    }
  };

  return (
    <div className="px-6 md:px-8 py-6 space-y-6">
      {error && <div className="text-sm text-red-400 bg-red-400/10 p-3 rounded-lg">{error}</div>}
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Logs</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Real-time application logs with filtering and search
          </p>
        </div>
        <div className="flex items-center gap-3">
          <SecondaryButton onClick={clearLogs}>
            Clear
          </SecondaryButton>
          <SecondaryButton onClick={download}>
            Download
          </SecondaryButton>
          {running ? (
            <PrimaryButton onClick={stopStreaming}>
              Stop Live
            </PrimaryButton>
          ) : (
            <PrimaryButton onClick={startStreaming}>
              Start Live
            </PrimaryButton>
          )}
        </div>
      </div>

      {/* Status */}
      <div className="text-sm text-zinc-400 bg-neutral-800/40 p-3 rounded-lg">
        {status} • {filteredLogs.length} logs shown • {logs.length} total
      </div>

      {/* Filters */}
      <Card title="Filters">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs text-zinc-400 mb-1">Level</label>
            <select
              value={filters.level}
              onChange={(e) => setFilters(prev => ({ ...prev, level: e.target.value }))}
              className="w-full bg-neutral-700 border border-neutral-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
            >
              <option value="">All Levels</option>
              <option value="ERROR">Error</option>
              <option value="WARNING">Warning</option>
              <option value="INFO">Info</option>
              <option value="DEBUG">Debug</option>
            </select>
          </div>
          
          <div>
            <label className="block text-xs text-zinc-400 mb-1">Endpoint</label>
            <input
              type="text"
              placeholder="Filter by endpoint..."
              value={filters.endpoint}
              onChange={(e) => setFilters(prev => ({ ...prev, endpoint: e.target.value }))}
              className="w-full bg-neutral-700 border border-neutral-600 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
            />
          </div>
          
          <div>
            <label className="block text-xs text-zinc-400 mb-1">Trace ID</label>
            <input
              type="text"
              placeholder="Filter by trace ID..."
              value={filters.traceId}
              onChange={(e) => setFilters(prev => ({ ...prev, traceId: e.target.value }))}
              className="w-full bg-neutral-700 border border-neutral-600 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
            />
          </div>
          
          <div>
            <label className="block text-xs text-zinc-400 mb-1">Text Search</label>
            <input
              type="text"
              placeholder="Search in messages..."
              value={filters.text}
              onChange={(e) => setFilters(prev => ({ ...prev, text: e.target.value }))}
              className="w-full bg-neutral-700 border border-neutral-600 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
            />
          </div>
        </div>
      </Card>

      {/* Logs Table */}
      <Card title="Live Logs" right={
        <div className="text-xs text-zinc-400">
          {running && <span className="inline-block w-2 h-2 bg-emerald-400 rounded-full animate-pulse mr-2"></span>}
          {running ? 'Streaming' : 'Stopped'}
        </div>
      }>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-zinc-400 border-b border-neutral-700">
              <tr>
                <th className="text-left py-2 px-3">Time</th>
                <th className="text-left py-2 px-3">Level</th>
                <th className="text-left py-2 px-3">Message</th>
                <th className="text-left py-2 px-3">Endpoint</th>
                <th className="text-left py-2 px-3">Status</th>
                <th className="text-left py-2 px-3">Trace ID</th>
                <th className="text-left py-2 px-3">Client IP</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-zinc-500">
                    {logs.length === 0 ? "No logs yet. Click 'Start Live' to begin streaming." : "No logs match the current filters."}
                  </td>
                </tr>
              ) : (
                filteredLogs.slice().reverse().map((log, i) => (
                  <tr key={i} className="border-b border-neutral-800/50 hover:bg-neutral-800/30">
                    <td className="py-2 px-3 text-zinc-400 font-mono text-xs">
                      {formatTimestamp(log.timestamp)}
                    </td>
                    <td className="py-2 px-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getLevelColor(log.level)}`}>
                        {log.level}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-zinc-300 max-w-md truncate">
                      {log.msg}
                    </td>
                    <td className="py-2 px-3 text-zinc-400 text-xs">
                      {log.path || '—'}
                    </td>
                    <td className="py-2 px-3 text-zinc-400 text-xs">
                      {log.status ? (
                        <span className={`px-2 py-1 rounded text-xs ${
                          log.status >= 500 ? 'bg-red-500/20 text-red-300' :
                          log.status >= 400 ? 'bg-amber-500/20 text-amber-300' :
                          'bg-emerald-500/20 text-emerald-300'
                        }`}>
                          {log.status}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="py-2 px-3 text-zinc-400 text-xs">
                      {log.trace_id ? (
                        <button
                          onClick={() => copyTraceId(log.trace_id!)}
                          className="text-emerald-400 hover:text-emerald-300 underline cursor-pointer"
                          title="Click to copy"
                        >
                          {log.trace_id.slice(0, 8)}...
                        </button>
                      ) : '—'}
                    </td>
                    <td className="py-2 px-3 text-zinc-400 text-xs">
                      {log.client_ip || '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
