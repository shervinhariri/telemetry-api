import { useEffect, useRef, useState } from "react";

export function useAdminRequestsPoll(url: string, intervalMs = 10000) {
  const [items, setItems] = useState<any[]>([]);
  const etagRef = useRef<string | null>(null);
  const timerRef = useRef<any>(null);

  const tick = async () => {
    if (document.hidden) return; // pause when hidden
    const headers: Record<string,string> = {};
    if (etagRef.current) headers["If-None-Match"] = etagRef.current;
    const res = await fetch(url, { headers });
    if (res.status === 304) return;
    if (!res.ok) return;
    const etag = res.headers.get("ETag");
    if (etag) etagRef.current = etag;
    const data = await res.json();
    setItems(data.items ?? []);
  };

  useEffect(() => {
    tick();
    timerRef.current = setInterval(tick, intervalMs);
    return () => clearInterval(timerRef.current);
  }, [url, intervalMs]);

  return items;
}
