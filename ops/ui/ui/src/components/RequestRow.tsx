import React from "react";
import DonutGauge from "./DonutGauge";

export function RequestRow({ item, onClick }: { item: any, onClick: (it:any)=>void }) {
  return (
    <tr className="hover:bg-gray-50 cursor-pointer" onClick={() => onClick(item)}>
      <td className="pl-2"><DonutGauge value={item.fitness ?? 0} /></td>
      <td>{new Date(item.ts).toLocaleTimeString()}</td>
      <td><span className="font-medium">{item.method}</span> <span className="text-gray-600">{item.path}</span></td>
      <td>
        <span className={`px-2 py-0.5 rounded text-xs
          ${item.status >= 500 ? 'bg-red-100 text-red-800' :
            item.status >= 400 ? 'bg-amber-100 text-amber-800' :
            'bg-emerald-100 text-emerald-800'}`}>
          {item.status}
        </span>
      </td>
      <td>{(item.latency_ms ?? 0).toFixed(1)} ms</td>
      <td>{item.summary?.records ?? 0}</td>
      <td>{item.client_ip ?? "-"}</td>
      <td className="pr-2">›</td>
    </tr>
  );
}
