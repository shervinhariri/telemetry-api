export type ApiMethod = "GET" | "POST" | "PUT" | "DELETE";

const DEFAULT_BASE =
  (window as any).__API_BASE_URL__ ||
  (import.meta as any).env?.API_BASE_URL ||
  "http://localhost:80";

function getKey(): string | null {
  try {
    return localStorage.getItem("API_KEY") || null;
  } catch {
    return null;
  }
}

export async function apiFetch<T = any>(
  path: string,
  method: ApiMethod = "GET",
  body?: unknown,
  opts: RequestInit = {}
): Promise<{ status: number; data: T | string }> {
  const key = getKey();
  const headers: Record<string, string> = {
    Accept: "*/*",
  };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (key) headers["Authorization"] = `Bearer ${key}`;

  const res = await fetch(`${DEFAULT_BASE}${path}`, {
    method,
    headers: { ...headers, ...(opts.headers || {}) },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: "omit",
    mode: "cors",
    cache: "no-store",
  });

  const text = await res.text();
  try {
    return { status: res.status, data: JSON.parse(text) as T };
  } catch {
    return { status: res.status, data: text };
  }
}


