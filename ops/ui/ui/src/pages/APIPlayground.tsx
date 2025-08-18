import React, { useEffect, useState } from "react";
import { apiFetch } from "../lib/apiClient";

// ---------- UI atoms ----------
const Card = ({ title, right, children }: { title: string; right?: React.ReactNode; children: React.ReactNode }) => (
  <div className="rounded-2xl bg-[#111218] ring-1 ring-white/5 p-6">
    <div className="mb-4 flex items-center justify-between">
      <div className="text-sm text-zinc-300">{title}</div>
      {right}
    </div>
    {children}
  </div>
);

const JSONView = ({ data }: { data: any }) => (
  <pre className="text-xs leading-relaxed overflow-auto rounded-xl bg-black/40 p-4 ring-1 ring-white/5">
    {data ? JSON.stringify(data, null, 2) : "—"}
  </pre>
);

export default function APIPlayground({ api }: { api: any }) {
  const [sys, setSys] = useState<any>(null);
  const [met, setMet] = useState<any>(null);
  const [ingest, setIngest] = useState('{"collector_id":"tester","format":"flows.v1","records":[{"ts":1723351200.456,"src_ip":"10.0.0.10","dst_ip":"8.8.8.8","src_port":54000,"dst_port":53,"protocol":"udp","bytes":120,"packets":1}] }');
  const [out, setOut] = useState<any>(null);
  const [error, setError] = useState("");

  // Keep API key persisted for apiClient
  useEffect(() => {
    try { localStorage.setItem("API_KEY", (api as any)?.headers?.Authorization?.replace('Bearer ', '') || 'TEST_KEY'); } catch {}
  }, [api]);

  const fetchSystem = async () => {
    setError("");
    try {
      const { status, data } = await apiFetch("/v1/system", "GET");
      setSys({ status, data });
    } catch (e: any) { setError(String(e.message || e)); }
  };

  const fetchMetrics = async () => {
    setError("");
    try { const { status, data } = await apiFetch("/v1/metrics?window=900", "GET"); setMet({ status, data }); } catch (e: any) { setError(String(e.message || e)); }
  };

  const doIngest = async () => {
    setError("");
    try { const j = JSON.parse(ingest); const r = await apiFetch("/v1/ingest", "POST", j); setOut(r); } catch (e: any) { setError(String(e.message || e)); }
  };

  return (
    <div className="mt-6 space-y-4">
      {error && <div className="text-xs text-red-400">{error}</div>}

      <div className="flex gap-2 flex-wrap">
        <button onClick={fetchSystem} className="rounded-xl bg-neutral-700 hover:bg-neutral-600 px-3 py-2 text-sm">/v1/system</button>
        <button onClick={fetchMetrics} className="rounded-xl bg-neutral-700 hover:bg-neutral-600 px-3 py-2 text-sm">/v1/metrics</button>
      </div>

      <div>
        <div className="text-sm mb-2">Send ingest</div>
        <textarea value={ingest} onChange={(e)=>setIngest(e.target.value)} rows={10}
          className="w-full rounded-xl bg-neutral-900 border border-neutral-700 p-3 text-xs font-mono" />
        <div className="mt-2"><button onClick={doIngest} className="rounded-xl bg-emerald-700/50 hover:bg-emerald-700/70 px-3 py-2 text-sm">Send ingest</button></div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <JSONView data={sys} />
        <JSONView data={met} />
      </div>
    </div>
  );
}
