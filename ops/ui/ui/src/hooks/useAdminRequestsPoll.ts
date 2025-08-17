import { useEffect, useRef, useState, useCallback } from "react";

type HeadersLike = Record<string, string>;

export function useAdminRequestsPoll(
  url: string,
  intervalMs = 10000,
  headers: HeadersLike = {}
) {
  const [items, setItems] = useState<any[]>([]);
  const etagRef = useRef<string | null>(null);
  const timerRef = useRef<any>(null);

  const tick = useCallback(async () => {
    if (document.hidden) return; // pause when tab hidden
    const h: HeadersLike = { ...headers };
    if (etagRef.current) h["If-None-Match"] = etagRef.current;
    const res = await fetch(url, { headers: h, credentials: "same-origin" });
    if (res.status === 304) return;
    if (!res.ok) return;
    const etag = res.headers.get("ETag");
    if (etag) etagRef.current = etag;
    const data = await res.json().catch(() => ({}));
    setItems(Array.isArray(data.items) ? data.items : []);
  }, [url, headers]);

  useEffect(() => {
    tick();
    timerRef.current = setInterval(tick, intervalMs);
    return () => clearInterval(timerRef.current);
  }, [tick, intervalMs]);

  // allow manual refresh (e.g., a "Refresh" button)
  const refresh = useCallback(() => {
    etagRef.current = null; // bust ETag to force a 200
    tick();
  }, [tick]);

  return { items, refresh };
}
