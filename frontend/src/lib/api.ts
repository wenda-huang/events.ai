import { clearToken, getToken } from "@/lib/auth";
import type { City, EventItem, User } from "@/lib/types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "/api").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function detailMessage(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === "object" && item && "msg" in item ? String(item.msg) : String(item)))
      .join(", ");
  }
  return "Request failed";
}

function candidateBases(): string[] {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/$/, "");
  if (configured) return [configured];
  const bases = ["/api"];
  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    if (hostname === "localhost" || hostname === "127.0.0.1" || hostname === "[::1]") {
      bases.push(`${protocol}//127.0.0.1:8000`, `${protocol}//localhost:8000`);
    }
  }
  return [...new Set(bases)];
}

function isProxyFailure(status: number, contentType: string): boolean {
  if (status === 502 || status === 503 || status === 504) return true;
  return status === 500 && !contentType.includes("application/json");
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const bases = candidateBases();
  let lastNetworkError = "Cannot reach the API server. Start the FastAPI backend on port 8000.";

  for (let i = 0; i < bases.length; i++) {
    const canFallback = i < bases.length - 1;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    if (init.signal) {
      init.signal.addEventListener("abort", () => controller.abort(), { once: true });
    }
    try {
      const res = await fetch(`${bases[i]}${path}`, { ...init, headers, signal: controller.signal });
      const contentType = res.headers.get("content-type") || "";
      if (canFallback && isProxyFailure(res.status, contentType)) {
        continue;
      }
      const text = await res.text();
      if (res.status === 401) {
        clearToken();
        if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
          window.location.href = "/login";
        }
      }
      if (!res.ok) {
        let detail: unknown = res.statusText;
        try {
          const parsed = JSON.parse(text) as { detail?: unknown };
          detail = parsed.detail ?? parsed;
        } catch {
          detail = text.trim() || res.statusText;
        }
        throw new ApiError(res.status, detailMessage(detail));
      }
      if (!text.trim()) {
        return {} as T;
      }
      return JSON.parse(text) as T;
    } catch (err) {
      if (err instanceof ApiError) throw err;
      const aborted = err instanceof DOMException && err.name === "AbortError";
      lastNetworkError = aborted
        ? "API timed out. Is the backend running?"
        : err instanceof Error
          ? err.message
          : lastNetworkError;
      if (!canFallback) {
        throw new ApiError(503, lastNetworkError);
      }
    } finally {
      clearTimeout(timer);
    }
  }

  throw new ApiError(503, lastNetworkError);
}

export type ScanPipelineEvent = {
  stage: string;
  message: string;
  level?: "log" | "info" | "warn" | "error";
  [key: string]: unknown;
};

export async function scanStream(onEvent: (event: ScanPipelineEvent) => void): Promise<ScanPipelineEvent> {
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const bases = candidateBases();
  let res: Response | null = null;
  for (let i = 0; i < bases.length; i++) {
    try {
      const next = await fetch(`${bases[i]}/jobs/scan`, { method: "POST", headers });
      const contentType = next.headers.get("content-type") || "";
      if (i < bases.length - 1 && isProxyFailure(next.status, contentType)) {
        continue;
      }
      res = next;
      break;
    } catch {
      if (i === bases.length - 1) {
        throw new ApiError(503, "Cannot reach the API server. Start the FastAPI backend on port 8000.");
      }
    }
  }
  if (!res) {
    throw new ApiError(503, "Cannot reach the API server. Start the FastAPI backend on port 8000.");
  }
  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, detailMessage(body.detail));
  }
  if (!res.body) {
    throw new ApiError(500, "Scan stream had no body");
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let last: ScanPipelineEvent = { stage: "done", message: "Scan finished", ok: false };
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (!line.trim()) continue;
      const event = JSON.parse(line) as ScanPipelineEvent;
      last = event;
      onEvent(event);
    }
    if (done) break;
  }
  if (buffer.trim()) {
    const event = JSON.parse(buffer) as ScanPipelineEvent;
    last = event;
    onEvent(event);
  }
  return last;
}

export const client = {
  register: (email: string, password: string, name: string) =>
    api<{ access_token: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    }),
  login: (email: string, password: string) =>
    api<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => api<User>("/me"),
  tags: () => api<{ tags: string[] }>("/tags"),
  cities: () => api<{ cities: City[] }>("/cities"),
  onboard: (body: { name: string; phone?: string; tags: string[]; lat?: number; lng?: number }) =>
    api<User>("/me/onboarding", { method: "POST", body: JSON.stringify(body) }),
  patchMe: (body: Partial<User> & { default_radius_mi?: number }) =>
    api<User>("/me", { method: "PATCH", body: JSON.stringify(body) }),
  events: (params: URLSearchParams) => api<{ events: EventItem[] }>(`/events?${params}`),
  recommended: (params: URLSearchParams) => api<{ events: EventItem[] }>(`/events/recommended?${params}`),
  event: (id: number) => api<EventItem>(`/events/${id}`),
  createEvent: (body: Record<string, unknown>) =>
    api<EventItem>("/events", { method: "POST", body: JSON.stringify(body) }),
  signup: (id: number) => api<EventItem>(`/events/${id}/signup`, { method: "POST" }),
  leave: (id: number) => api<EventItem>(`/events/${id}/signup`, { method: "DELETE" }),
  decline: (id: number) => api<EventItem>(`/events/${id}/decline`, { method: "POST" }),
  myEvents: () => api<{ joined: EventItem[]; invited: EventItem[] }>("/me/events"),
  scan: () => scanStream(() => undefined),
  scanStream,
  cluster: () => api<{ ok: boolean; clusters?: number; invites_created?: number }>("/jobs/cluster", { method: "POST" }),
  mapConfig: () =>
    api<{
      carto_api_base_url: string;
      tile_url: string;
      has_carto_key: boolean;
      has_querit_key: boolean;
    }>("/config/public"),
};
