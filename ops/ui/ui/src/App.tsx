import React, { useEffect, useMemo, useState } from "react";
import Dashboard from "./pages/Dashboard";
import Requests from "./pages/Requests";
import Logs from "./pages/Logs";
import APIPlayground from "./pages/APIPlayground";

// ---------- Small helpers ----------
const cx = (...list: (string | boolean | undefined)[]) => list.filter(Boolean).join(" ");

// ---------- API client ----------
function makeApiClient(baseUrl: string, apiKey: string) {
  const h: HeadersInit = {
    "Content-Type": "application/json",
    ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
  };
  
  const get = async (path: string) => {
    const r = await fetch(`${baseUrl}${path}`, { headers: h });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  };
  
  const post = async (path: string, body: any) => {
    const r = await fetch(`${baseUrl}${path}`, { method: "POST", headers: h, body: JSON.stringify(body) });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  };
  
  return { get, post };
}

// ---------- UI atoms ----------
const Page = ({ children }: { children: React.ReactNode }) => (
  <div className="min-h-screen w-full bg-[#0B0C10] text-zinc-100 antialiased">
    <div className="max-w-7xl mx-auto px-5 pb-24">{children}</div>
  </div>
);

const TopBar = ({ status, apiKey, setApiKey, versionText }: {
  status: string;
  apiKey: string;
  setApiKey: (key: string) => void;
  versionText: string;
}) => (
  <div className="sticky top-0 z-30 backdrop-blur bg-[#0B0C10]/70">
    <div className="max-w-7xl mx-auto px-5 py-4 flex items-center gap-3">
      <div className="text-xl font-semibold tracking-tight">Telemetry</div>
      <span className={cx(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium",
        status === "online" ? "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/40" : "bg-zinc-700/40 text-zinc-300 ring-1 ring-zinc-600"
      )}>
        <span className={cx("mr-1 h-1.5 w-1.5 rounded-full", status === "online" ? "bg-emerald-400" : "bg-zinc-400")} />
        {status === "online" ? "Online" : "Offline"}
      </span>
      <div className="text-xs text-zinc-400">Version: <span className="text-zinc-200">{versionText || "—"}</span></div>
      <div className="ml-auto flex items-center gap-2">
        <span className="text-xs text-zinc-400">API Key</span>
        <input
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="paste…"
          className="w-[340px] rounded-xl bg-[#14151B] px-3 py-2 text-sm text-zinc-200 outline-none ring-1 ring-white/5 focus:ring-indigo-400/40"
        />
      </div>
    </div>
  </div>
);

const Tabs = ({ tab, setTab, items }: {
  tab: string;
  setTab: (tab: string) => void;
  items: string[];
}) => (
  <div className="mt-4 flex gap-2 flex-wrap">
    {items.map((t) => (
      <button key={t}
        className={cx(
          "px-4 py-2 rounded-2xl text-sm ring-1",
          tab === t ? "bg-[#14151B] ring-indigo-500/40 text-zinc-100" : "bg-[#0F1116] ring-white/5 text-zinc-400 hover:text-zinc-200"
        )}
        onClick={() => setTab(t)}
      >{t}</button>
    ))}
  </div>
);

export default function App() {
  const [apiBase, setApiBase] = useState(""); // Use relative URLs by default
  const [apiKey, setApiKey] = useState("TEST_KEY");
  const [tab, setTab] = useState("Dashboard");
  const [status, setStatus] = useState("online");
  const [versionText, setVersionText] = useState("");
  const [auto, setAuto] = useState(true);

  const api = useMemo(() => {
    const client = makeApiClient(apiBase, apiKey);
    // expose headers & base for logs download fallback
    (client as any).headers = { "Content-Type": "application/json", ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}) };
    (client as any).base = apiBase;
    return client;
  }, [apiBase, apiKey]);

  // Initial ping for version + status
  useEffect(() => {
    try { localStorage.setItem("API_KEY", apiKey || ""); } catch {}
    (async () => {
      try {
        let sys;
        try { sys = await api.get("/v1/system"); }
        catch { sys = await api.get("/v1/version"); }
        const v = (sys as any)?.image?.includes(":") ? (sys as any).image.split(":").pop() : ((sys as any)?.version || (sys as any)?.service || "");
        setVersionText(v);
        setStatus("online");
      } catch { setStatus("offline"); }
    })();
  }, [api]);

  return (
    <Page>
      <TopBar status={status} apiKey={apiKey} setApiKey={setApiKey} versionText={versionText} />

      <div className="mt-6 flex items-center gap-3 text-sm text-zinc-400">
        <label className="flex items-center gap-2">API Base
          <input value={apiBase} onChange={(e)=>setApiBase(e.target.value)} className="ml-2 w-[320px] rounded-xl bg-[#14151B] px-3 py-2 text-sm text-zinc-200 outline-none ring-1 ring-white/5 focus:ring-indigo-400/40" />
        </label>
      </div>

      <Tabs tab={tab} setTab={setTab} items={["Dashboard", "Requests", "Logs", "API"]} />

      {tab === "Dashboard" && <Dashboard api={api} auto={auto} setAuto={setAuto} />}
      {tab === "Requests" && <Requests api={api} />}
      {tab === "Logs" && <Logs api={api} />}
      {tab === "API" && <APIPlayground api={api} />}
    </Page>
  );
}
