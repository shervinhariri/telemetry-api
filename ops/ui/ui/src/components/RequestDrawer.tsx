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

  return (
    <aside className="fixed top-0 right-0 h-full w-[420px] bg-white shadow-2xl border-l p-4 overflow-y-auto">
      <button className="mb-3 text-sm text-gray-600 hover:text-black" onClick={onClose}>Close</button>
      <div className="flex items-center gap-2 mb-2">
        <div className="text-xl font-semibold">{item.method} {item.path}</div>
        <span className="ml-auto text-sm text-gray-500">{new Date(item.ts).toLocaleString()}</span>
      </div>
      <div className="text-sm text-gray-600 mb-4">
        Status <b>{item.status}</b> · Latency <b>{(item.latency_ms ?? 0).toFixed(1)} ms</b> · Trace <b>{item.id}</b>
      </div>
      <ol className="space-y-2">
        {tl.map((s:any, i:number) => (
          <li key={i} className="flex items-start gap-2">
            <div className="mt-0.5">{ICONS[s.event] ?? "•"}</div>
            <div>
              <div className="font-medium">{s.event}</div>
              <div className="text-xs text-gray-600">{new Date(s.ts).toLocaleTimeString()}</div>
              {!!s.meta && <pre className="text-xs bg-gray-50 p-2 rounded mt-1 overflow-x-auto">
                {JSON.stringify(s.meta, null, 2)}
              </pre>}
            </div>
          </li>
        ))}
      </ol>
      <details className="mt-4">
        <summary className="cursor-pointer text-sm text-gray-700">View raw JSON</summary>
        <pre className="text-xs bg-gray-50 p-2 rounded mt-2 overflow-x-auto">
{JSON.stringify(item, null, 2)}
        </pre>
      </details>
    </aside>
  );
}
