import type { Origin } from "@/lib/types";

export const PITTSBURGH: Origin = { lat: 40.4406, lng: -79.9959 };

export function haversineMi(a: Origin, b: Origin): number {
  const r = 3958.8;
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLng = ((b.lng - a.lng) * Math.PI) / 180;
  const x =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((a.lat * Math.PI) / 180) * Math.cos((b.lat * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
  return r * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}

export function resolveOrigin(coords: Origin | null): { origin: Origin; outsideCity: boolean } {
  if (!coords) return { origin: PITTSBURGH, outsideCity: false };
  const outsideCity = haversineMi(coords, PITTSBURGH) > 25;
  return { origin: outsideCity ? PITTSBURGH : coords, outsideCity };
}

export function formatWhen(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function toLocalInput(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function defaultWindow(): { start: string; end: string } {
  const start = new Date();
  const end = new Date(start.getTime() + 14 * 24 * 60 * 60 * 1000);
  return { start: toLocalInput(start), end: toLocalInput(end) };
}

export function roundCoord(value: number): number {
  return Math.round(value * 1e5) / 1e5;
}

export function sameOrigin(a: Origin, b: Origin): boolean {
  return roundCoord(a.lat) === roundCoord(b.lat) && roundCoord(a.lng) === roundCoord(b.lng);
}

export function queryParams(
  center: Origin,
  radius: number,
  start: string,
  end: string,
  q = "",
  distanceFrom?: Origin | null
): URLSearchParams {
  const params = new URLSearchParams({
    lat: String(center.lat),
    lng: String(center.lng),
    radius_mi: String(radius),
    start: new Date(start).toISOString(),
    end: new Date(end).toISOString(),
  });
  const from = distanceFrom ?? center;
  params.set("origin_lat", String(from.lat));
  params.set("origin_lng", String(from.lng));
  if (q.trim()) params.set("q", q.trim());
  return params;
}
