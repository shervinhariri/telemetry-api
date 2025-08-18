import React from "react";

const ICONS: Record<string,string> = {
  received: "⬤",
  validated: "✅",
  enriched: "🧠",
  exported: "↗",
  completed: "🏁",
  posthook: "🔔",
};

export function RequestDrawer({ item, onClose }: { item:any, onClose:()=>void }) {
  if (!item) return null;
  const tl = (item.timeline ?? []).slice(0, 6);

  const jsonText = JSON.stringify(item, null, 2);

  return (
    <>
      {/* Backdrop */}
      {/* Offset for top bar height (approx 56px). Keeps content fully visible below the top tabs/pill. */}
      <div className="fixed left-0 right-0 bg-black/40" style={{ top: 56, bottom: 0, zIndex: 9998 }} onClick={onClose} />
      <aside className="fixed right-0 w-full max-w-md z-50 bg-[#111218] border-l border-white/10 shadow-2xl" style={{ top: 56, height: 'calc(100vh - 56px)', zIndex: 9999 }}>
      {/* Header (stays visible) */}
      <div className="sticky top-0 z-[71] bg-[#111218] px-4 py-3 border-b border-white/10 flex items-center gap-2">
        <div className="text-sm font-semibold text-white/90 truncate">{item.method} {item.path}</div>
        <span className="ml-auto text-xs text-zinc-400">{new Date(item.ts).toLocaleString()}</span>
        <button className="ml-3 rounded-md px-2 py-1 text-xs ring-1 ring-white/10 text-zinc-300 hover:bg-white/5" onClick={onClose}>Close</button>
      </div>

      {/* Scrollable content */}
      <div className="h-[calc(100vh-44px)] overflow-y-auto px-4 py-3 space-y-4">
        <div className="text-xs text-zinc-400">
          Status <b className="text-zinc-200">{item.status}</b> · Latency <b className="text-zinc-200">{(item.latency_ms ?? 0).toFixed(1)} ms</b> · Trace <b className="text-zinc-200">{item.id}</b>
        </div>

        <ol className="space-y-2">
          {tl.map((s:any, i:number) => (
            <li key={i} className="flex items-start gap-2">
              <div className="mt-0.5">{ICONS[s.event] ?? "•"}</div>
              <div>
                <div className="font-medium text-zinc-200">{s.event}</div>
                <div className="text-xs text-zinc-500">{new Date(s.ts).toLocaleTimeString()}</div>
                {!!s.meta && <pre className="text-xs bg-black/30 border border-white/10 text-zinc-300 p-2 rounded mt-1 overflow-auto max-h-40">
                  {JSON.stringify(s.meta, null, 2)}
                </pre>}
              </div>
            </li>
          ))}
        </ol>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <div className="text-sm text-zinc-300">Raw JSON</div>
            <button onClick={() => navigator.clipboard.writeText(jsonText)} className="rounded-md px-2 py-1 text-xs bg-white/5 text-zinc-200 ring-1 ring-white/10 hover:bg-white/10">Copy</button>
          </div>
          <pre className="text-xs bg-black/40 border border-white/10 text-zinc-300 p-3 rounded overflow-auto max-h-[60vh]">
{jsonText}
          </pre>
        </div>
      </div>
      </aside>
    </>
  );
}
