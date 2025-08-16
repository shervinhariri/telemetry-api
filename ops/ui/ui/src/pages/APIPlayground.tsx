import React, { useState } from "react";

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
  const [ingest, setIngest] = useState("{\n  \"records\": []\n}");
  const [lookup, setLookup] = useState("");
  const [out, setOut] = useState<any>(null);
  const [error, setError] = useState("");

  const fetchSystem = async () => {
    setError("");
    try {
      let s;
      try { s = await api.get("/v1/system"); }
      catch { s = await api.get("/v1/version"); }
      setSys(s);
    } catch (e: any) { setError(String(e.message || e)); }
  };

  const fetchMetrics = async () => {
    setError("");
    try { setMet(await api.get("/v1/metrics")); } catch (e: any) { setError(String(e.message || e)); }
  };

  const doIngest = async () => {
    setError("");
    try { const j = JSON.parse(ingest); const r = await api.post("/v1/ingest", j); setOut(r); } catch (e: any) { setError(String(e.message || e)); }
  };

  const doLookup = async () => {
    setError("");
    try { const r = await api.post("/v1/lookup", { value: lookup }); setOut(r); } catch (e: any) { setError(String(e.message || e)); }
  };

  return (
    <div className="mt-6 space-y-4">
      {error && <div className="text-xs text-red-400">{error}</div>}

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="System Info" right={<button onClick={fetchSystem} className="text-xs rounded-lg ring-1 ring-white/10 px-2 py-1 hover:ring-indigo-400/40">Fetch</button>}>
          <JSONView data={sys} />
        </Card>
        <Card title="Metrics" right={<button onClick={fetchMetrics} className="text-xs rounded-lg ring-1 ring-white/10 px-2 py-1 hover:ring-indigo-400/40">Fetch</button>}>
          <JSONView data={met} />
        </Card>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Ingest (JSON)">
          <textarea value={ingest} onChange={(e)=>setIngest(e.target.value)} rows={10}
            className="w-full rounded-xl bg-black/40 p-3 text-xs ring-1 ring-white/5 outline-none" />
          <div className="mt-2 flex justify-end"><button onClick={doIngest} className="text-xs rounded-lg ring-1 ring-white/10 px-2 py-1 hover:ring-indigo-400/40">Send</button></div>
        </Card>
        <Card title="Lookup">
          <input value={lookup} onChange={(e)=>setLookup(e.target.value)} placeholder="ip, domain, hash…"
            className="w-full rounded-xl bg-black/40 p-3 text-sm ring-1 ring-white/5 outline-none" />
          <div className="mt-2 flex justify-end"><button onClick={doLookup} className="text-xs rounded-lg ring-1 ring-white/10 px-2 py-1 hover:ring-indigo-400/40">Run</button></div>
        </Card>
      </div>

      <Card title="Output">
        <JSONView data={out} />
      </Card>
    </div>
  );
}
