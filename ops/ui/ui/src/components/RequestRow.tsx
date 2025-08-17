import React from "react";
import DonutGauge from "./DonutGauge";

export function RequestRow({ item, onClick }: { item: any, onClick: (it:any)=>void }) {
  const fitnessReason = (it: any): string => {
    const s = it.status ?? 0;
    const tl = it.timeline ?? [];
    const v = tl.find((x: any) => x.event === "validated");
    if (v && v.meta && v.meta.ok === false) return "Validation failed";
    const e = tl.find((x: any) => x.event === "exported");
    if (e && e.meta) {
      const bad: string[] = [];
      for (const k of ["splunk", "elastic"]) {
        const v = (e.meta as any)[k];
        if (v && String(v).toLowerCase() !== "ok" && String(v).toLowerCase() !== "success") bad.push(k);
      }
      if (bad.length) return `Export failure: ${bad.join(", ")}`;
    }
    if (typeof s === "number" && s >= 400) return `HTTP ${s}`;
    return "Healthy";
  };

  return (
    <tr className="hover:bg-gray-50 cursor-pointer" onClick={() => onClick(item)}>
      <td className="pl-2"><DonutGauge value={item.fitness ?? 0} title={fitnessReason(item)} /></td>
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
      <td>{typeof item.latency_ms === "number" ? `${item.latency_ms.toFixed(1)} ms` : "—"}</td>
      <td>{item.summary?.records ?? 0}</td>
      <td>{item.client_ip ?? "-"}</td>
      <td className="pr-2">›</td>
    </tr>
  );
}
