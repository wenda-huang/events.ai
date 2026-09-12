"use client";

import dynamic from "next/dynamic";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { EventCard } from "@/components/EventCard";
import { RequireAuth } from "@/components/RequireAuth";
import { TagPicker } from "@/components/TagPicker";
import { client } from "@/lib/api";
import { defaultWindow, PITTSBURGH, queryParams, resolveOrigin } from "@/lib/geo";
import type { EventItem, Origin } from "@/lib/types";

const EventMap = dynamic(() => import("@/components/EventMap"), { ssr: false });

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`}
    >
      <path d="M5 7.5L10 12.5L15 7.5" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function MapView() {
  const windowDefaults = useMemo(() => defaultWindow(), []);
  const [origin, setOrigin] = useState<Origin>(PITTSBURGH);
  const [outsideCity, setOutsideCity] = useState(false);
  const [radius, setRadius] = useState(3);
  const [start, setStart] = useState(windowDefaults.start);
  const [end, setEnd] = useState(windowDefaults.end);
  const [q, setQ] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [filterTags, setFilterTags] = useState<string[]>([]);
  const [allTags, setAllTags] = useState<string[]>([]);
  const [recommendedExpanded, setRecommendedExpanded] = useState(false);
  const mapAreaRef = useRef<HTMLDivElement>(null);
  const recommendedListRef = useRef<HTMLDivElement>(null);
  const recHeaderRef = useRef<HTMLDivElement>(null);
  const firstCardRef = useRef<HTMLDivElement>(null);
  const searchOverlayRef = useRef<HTMLDivElement>(null);
  const filterInnerRef = useRef<HTMLDivElement>(null);
  const [searchOverlayHeight, setSearchOverlayHeight] = useState(128);
  const [filterHeight, setFilterHeight] = useState(0);
  const [panelHeight, setPanelHeight] = useState<number>();
  const [events, setEvents] = useState<EventItem[]>([]);
  const [recommended, setRecommended] = useState<EventItem[]>([]);
  const [error, setError] = useState("");
  const filteredRecommended = useMemo(() => {
    if (filterTags.length === 0) return recommended;
    return recommended.filter((event) => (event.tags || []).some((tag) => filterTags.includes(tag)));
  }, [recommended, filterTags]);

  useEffect(() => {
    client.tags().then((res) => setAllTags(res.tags));
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

  useEffect(() => {
    const el = searchOverlayRef.current;
    if (!el) return;
    const update = () => setSearchOverlayHeight(el.getBoundingClientRect().height);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, [showFilters, filterHeight]);

  useLayoutEffect(() => {
    const inner = filterInnerRef.current;
    if (!inner) return;
    const apply = () => setFilterHeight(showFilters ? inner.scrollHeight : 0);
    apply();
    const observer = new ResizeObserver(apply);
    observer.observe(inner);
    return () => observer.disconnect();
  }, [showFilters, allTags]);

  useLayoutEffect(() => {
    const mapHeight = mapAreaRef.current?.clientHeight ?? 0;
    const headerHeight = recHeaderRef.current?.getBoundingClientRect().height ?? 0;
    const cardHeight = firstCardRef.current?.getBoundingClientRect().height ?? 0;
    const outerPad = 32;
    const innerPad = 24;
    const headerGap = 8;
    const collapsedHeight = Math.ceil(outerPad + innerPad + headerHeight + headerGap + cardHeight);
    const expandedHeight = Math.max(collapsedHeight, mapHeight - searchOverlayHeight);
    setPanelHeight(recommendedExpanded ? expandedHeight : collapsedHeight);
  }, [recommendedExpanded, searchOverlayHeight, filteredRecommended]);

  return (
    <div ref={mapAreaRef} className="relative min-h-0 flex-1">
      <EventMap origin={origin} events={events} onMapInteract={() => setRecommendedExpanded(false)} />
      <div ref={searchOverlayRef} className="pointer-events-none absolute inset-x-0 top-0 z-[510] p-4">
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
              onClick={() => setShowFilters((v) => !v)}
              className={`flex items-center gap-1.5 rounded-full border px-3 py-2 text-xs transition hover:border-gold/60 hover:text-cream ${
                showFilters || filterTags.length > 0 ? "border-gold/60 text-cream" : "border-line text-mute"
              }`}
              aria-expanded={showFilters}
            >
              Filter
              {filterTags.length > 0 && <span className="rounded-full bg-gold/20 px-1.5 text-[10px] text-gold">{filterTags.length}</span>}
              <Chevron open={showFilters} />
            </button>
          </div>
          <div
            className="overflow-hidden transition-[height] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]"
            style={{ height: filterHeight }}
            aria-hidden={!showFilters}
            inert={!showFilters}
          >
            <div
              ref={filterInnerRef}
              className={`mt-2 space-y-3 border-t border-line pt-2 ${showFilters ? "" : "pointer-events-none"}`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <label className="flex items-center gap-2 text-xs text-mute">
                  From
                  <input className="field w-auto" type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} />
                </label>
                <label className="flex items-center gap-2 text-xs text-mute">
                  To
                  <input className="field w-auto" type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} />
                </label>
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-[11px] uppercase tracking-[0.2em] text-mute">Recommendation tags</p>
                  {filterTags.length > 0 && (
                    <button type="button" className="text-[11px] text-gold" onClick={() => setFilterTags([])}>
                      Clear
                    </button>
                  )}
                </div>
                <TagPicker tags={allTags} selected={filterTags} onChange={setFilterTags} />
              </div>
            </div>
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
        <div
          onWheel={(e) => {
            if (e.deltaY > 0 && !recommendedExpanded) {
              setRecommendedExpanded(true);
            } else if (e.deltaY < 0 && recommendedExpanded && (recommendedListRef.current?.scrollTop ?? 0) <= 0) {
              setRecommendedExpanded(false);
            }
          }}
          className="pointer-events-none absolute inset-x-0 bottom-0 z-[500] flex flex-col overflow-hidden p-4 transition-[height] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]"
          style={panelHeight ? { height: panelHeight } : undefined}
        >
          <div className="pointer-events-auto mx-auto flex h-full min-h-0 w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-line bg-panel/94 p-3 shadow-lift backdrop-blur">
            <div ref={recHeaderRef} className="mb-2 flex shrink-0 items-center justify-between">
              <p className="text-[11px] uppercase tracking-[0.2em] text-gold">
                Recommended
                <span className="ml-2 tracking-normal text-mute">
                  {filteredRecommended.length}
                  {filterTags.length > 0 ? " filtered" : ""}
                </span>
              </p>
              <button
                type="button"
                onClick={() => setRecommendedExpanded((v) => !v)}
                className="flex items-center gap-1 text-xs text-mute transition hover:text-cream"
              >
                {recommendedExpanded ? "Collapse" : "Expand"}
                <Chevron open={recommendedExpanded} />
              </button>
            </div>
            <div
              ref={recommendedListRef}
              className={`min-h-0 flex-1 space-y-2 ${recommendedExpanded ? "overflow-auto" : "overflow-hidden"}`}
            >
              {filteredRecommended.map((event, index) => (
                <div key={event.id} ref={index === 0 ? firstCardRef : undefined}>
                  <EventCard event={event} />
                </div>
              ))}
              {filteredRecommended.length === 0 && (
                <p ref={firstCardRef} className="px-1 py-6 text-center text-sm text-mute">
                  No recommendations match these filters.
                </p>
              )}
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
