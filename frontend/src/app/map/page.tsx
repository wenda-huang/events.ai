"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";

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
  const [userLocation, setUserLocation] = useState<Origin | null>(null);
  const [radius, setRadius] = useState(3);
  const [start, setStart] = useState(windowDefaults.start);
  const [end, setEnd] = useState(windowDefaults.end);
  const [q, setQ] = useState("");
  const [showDateFilters, setShowDateFilters] = useState(false);
  const [recommendedExpanded, setRecommendedExpanded] = useState(false);
  const recommendedListRef = useRef<HTMLDivElement>(null);
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
        const coords = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        const resolved = resolveOrigin(coords);
        setOrigin(resolved.origin);
        setOutsideCity(resolved.outsideCity);
        setUserLocation(coords);
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
      <EventMap origin={origin} events={events} userLocation={userLocation} />
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
            <button
              type="button"
              onClick={() => setShowDateFilters((v) => !v)}
              className="flex items-center gap-1.5 rounded-full border border-line px-3 py-2 text-xs text-mute transition hover:border-gold/60 hover:text-cream"
              aria-expanded={showDateFilters}
            >
              Dates
              <svg
                viewBox="0 0 20 20"
                fill="none"
                className={`h-3.5 w-3.5 transition-transform ${showDateFilters ? "rotate-180" : ""}`}
              >
                <path d="M5 7.5L10 12.5L15 7.5" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
          {showDateFilters && (
            <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-line pt-2">
              <label className="flex items-center gap-2 text-xs text-mute">
                From
                <input className="field w-auto" type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} />
              </label>
              <label className="flex items-center gap-2 text-xs text-mute">
                To
                <input className="field w-auto" type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} />
              </label>
            </div>
          )}
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
        <div
          onWheel={(e) => {
            if (e.deltaY > 0 && !recommendedExpanded) {
              setRecommendedExpanded(true);
            } else if (e.deltaY < 0 && recommendedExpanded && (recommendedListRef.current?.scrollTop ?? 0) <= 0) {
              setRecommendedExpanded(false);
            }
          }}
          className={`absolute bottom-0 right-0 z-[500] flex w-[600px] max-w-[92vw] flex-col p-4 transition-[max-height] duration-300 ease-out ${
            recommendedExpanded ? "max-h-[90vh]" : "max-h-[22vh]"
          }`}
        >
          <div className="flex min-h-0 flex-1 flex-col rounded-2xl border border-line bg-panel/94 p-3 shadow-lift backdrop-blur">
            <div className="mb-2 flex shrink-0 items-center justify-between">
              <p className="text-[11px] uppercase tracking-[0.2em] text-gold">Recommended</p>
              <button
                type="button"
                onClick={() => setRecommendedExpanded((v) => !v)}
                className="flex items-center gap-1 text-xs text-mute transition hover:text-cream"
              >
                {recommendedExpanded ? "Collapse" : "Expand"}
                <svg
                  viewBox="0 0 20 20"
                  fill="none"
                  className={`h-3.5 w-3.5 transition-transform ${recommendedExpanded ? "rotate-180" : ""}`}
                >
                  <path d="M5 7.5L10 12.5L15 7.5" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>
            <div ref={recommendedListRef} className="min-h-0 flex-1 space-y-2 overflow-auto">
              {recommended.slice(0, recommendedExpanded ? recommended.length : 4).map((event) => (
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
