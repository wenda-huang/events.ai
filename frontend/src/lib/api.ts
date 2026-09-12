import { clearToken, getToken } from "@/lib/auth";
import type { EventItem, User } from "@/lib/types";

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

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
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
  return res.json() as Promise<T>;
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
  scan: () => api<{ ok: boolean; reason?: string; created?: number; scanned_docs?: number }>("/jobs/scan", { method: "POST" }),
  cluster: () => api<{ ok: boolean; clusters?: number; invites_created?: number }>("/jobs/cluster", { method: "POST" }),
  mapConfig: () =>
    api<{
      carto_api_base_url: string;
      tile_url: string;
      has_carto_key: boolean;
      has_querit_key: boolean;
    }>("/config/public"),
};
