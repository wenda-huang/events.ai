"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { EventCard } from "@/components/EventCard";
import { RequireAuth } from "@/components/RequireAuth";
import { client } from "@/lib/api";
import { defaultWindow, PITTSBURGH, queryParams, resolveOrigin } from "@/lib/geo";
import type { EventItem, Origin } from "@/lib/types";

const EventMap = dynamic(() => import("@/components/EventMap"), { ssr: false });

function MapView() {
  const windowDefaults = useMemo(() => defaultWindow(), []);
  const [origin, setOrigin] = useState<Origin>(PITTSBURGH);
  const [outsideCity, setOutsideCity] = useState(false);
  const [radius, setRadius] = useState(3);
  const [start, setStart] = useState(windowDefaults.start);
  const [end, setEnd] = useState(windowDefaults.end);
  const [q, setQ] = useState("");
  const [events, setEvents] = useState<EventItem[]>([]);
  const [recommended, setRecommended] = useState<EventItem[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    client.me().then((me) => {
      if (me.default_radius_mi) setRadius(me.default_radius_mi);
    });
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const resolved = resolveOrigin({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        setOrigin(resolved.origin);
        setOutsideCity(resolved.outsideCity);
      },
      () => {
        setOrigin(PITTSBURGH);
        setOutsideCity(false);
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  }, []);

  useEffect(() => {
    const params = queryParams(origin, radius, start, end, q);
    let cancelled = false;
    setError("");
    Promise.all([client.events(params), client.recommended(queryParams(origin, radius, start, end))])
      .then(([list, rec]) => {
        if (cancelled) return;
        setEvents(list.events);
        setRecommended(rec.events);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load events");
      });
    return () => {
      cancelled = true;
    };
  }, [origin, radius, start, end, q]);

  return (
    <div className="relative min-h-0 flex-1">
      <EventMap origin={origin} events={events} />
      <div className="pointer-events-none absolute inset-x-0 top-0 z-[500] p-4">
        <div className="pointer-events-auto mx-auto max-w-4xl rounded-2xl border border-line bg-panel/92 p-3 shadow-lift backdrop-blur">
          <div className="flex flex-wrap items-center gap-2">
            <input
              className="field min-w-56 flex-1"
              placeholder="Search events, tags, neighborhoods…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <label className="flex items-center gap-2 text-xs text-mute">
              Radius
              <input
                type="range"
                min={1}
                max={15}
                step={0.5}
                value={radius}
                onChange={(e) => setRadius(Number(e.target.value))}
              />
              <span className="w-10 text-cream">{radius} mi</span>
            </label>
            <input className="field w-auto" type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} />
            <input className="field w-auto" type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} />
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-mute">
            <span>
              {events.length} events · default window is 2 weeks
              {outsideCity ? " · showing Pittsburgh (you’re outside the launch city)" : ""}
            </span>
            {error && <span className="text-rust">{error}</span>}
          </div>
        </div>
      </div>
      {recommended.length > 0 && (
        <div className="absolute bottom-0 right-0 z-[500] max-h-[46%] w-[360px] overflow-auto p-4">
          <div className="rounded-2xl border border-line bg-panel/94 p-3 shadow-lift backdrop-blur">
            <p className="mb-2 text-[11px] uppercase tracking-[0.2em] text-gold">Recommended</p>
            <div className="space-y-2">
              {recommended.slice(0, 4).map((event) => (
                <EventCard key={event.id} event={event} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function MapPage() {
  return (
    <RequireAuth>
      <AppShell>
        <MapView />
      </AppShell>
    </RequireAuth>
  );
}
