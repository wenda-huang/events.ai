"use client";

import Link from "next/link";
import { useEffect, useMemo, useReducer, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useRouter } from "next/navigation";
import L from "leaflet";
import { MapContainer, Marker, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";

import { client } from "@/lib/api";
import { formatWhen } from "@/lib/geo";
import { coverTag, PALETTES, type CoverTag } from "@/components/EventCover";
import type { EventItem, Origin } from "@/lib/types";

import "leaflet/dist/leaflet.css";

const DEFAULT_TILES = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";
const CLUSTER_PIXELS = 28;

function hexToRgb(hex: string) {
  const clean = hex.replace("#", "");
  const value = parseInt(clean, 16);
  return { r: (value >> 16) & 255, g: (value >> 8) & 255, b: value & 255 };
}

const singlePinIcons = new Map<CoverTag, L.DivIcon>();
const clusterPinIcons = new Map<number, L.DivIcon>();

function singlePinIcon(tag: CoverTag) {
  const cached = singlePinIcons.get(tag);
  if (cached) return cached;
  const p = PALETTES[tag];
  const { r, g, b } = hexToRgb(p.sky1);
  const style = `--pin-light:${p.light};--pin-accent:${p.sky1};--pin-shadow:${p.land};--pin-glow:rgba(${r}, ${g}, ${b}, 0.3);`;
  const icon = L.divIcon({
    className: "event-pin",
    html: `<span class="pin-dot" style="${style}"></span>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });
  singlePinIcons.set(tag, icon);
  return icon;
}

function clusterPinIcon(count: number) {
  const cached = clusterPinIcons.get(count);
  if (cached) return cached;
  const icon = L.divIcon({
    className: "event-pin",
    html: `<span class="pin-dot pin-cluster">${count}</span>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
  clusterPinIcons.set(count, icon);
  return icon;
}

function pinIconFor(events: EventItem[]) {
  if (events.length === 1) return singlePinIcon(coverTag(events[0].tags));
  return clusterPinIcon(events.length);
}

let userDotIcon: L.DivIcon | null = null;

function getUserDotIcon() {
  if (!userDotIcon) {
    userDotIcon = L.divIcon({
      className: "user-location-pin",
      html: '<span class="user-dot"></span>',
      iconSize: [14, 14],
      iconAnchor: [7, 7],
    });
  }
  return userDotIcon;
}

type EventCluster = {
  id: string;
  lat: number;
  lng: number;
  events: EventItem[];
};

function clusterEvents(events: EventItem[], map: L.Map, threshold = CLUSTER_PIXELS): EventCluster[] {
  const placed = events.filter(
    (event) => Number.isFinite(event.location?.lat) && Number.isFinite(event.location?.lng),
  );
  const points = placed.map((event) => map.latLngToLayerPoint([event.location.lat, event.location.lng]));
  const parent = placed.map((_, index) => index);
  const find = (index: number) => {
    while (parent[index] !== index) {
      parent[index] = parent[parent[index]];
      index = parent[index];
    }
    return index;
  };
  const limit = threshold * threshold;
  for (let i = 0; i < placed.length; i++) {
    for (let j = i + 1; j < placed.length; j++) {
      const dx = points[i].x - points[j].x;
      const dy = points[i].y - points[j].y;
      if (dx * dx + dy * dy <= limit) {
        const a = find(i);
        const b = find(j);
        if (a !== b) parent[b] = a;
      }
    }
  }
  const groups = new Map<number, EventItem[]>();
  placed.forEach((event, index) => {
    const root = find(index);
    const group = groups.get(root);
    if (group) group.push(event);
    else groups.set(root, [event]);
  });
  return [...groups.values()].map((group) => {
    const items = [...group].sort((a, b) => +new Date(a.starts_at) - +new Date(b.starts_at));
    return {
      id: items.map((event) => event.id).join("-"),
      lat: items.reduce((sum, event) => sum + event.location.lat, 0) / items.length,
      lng: items.reduce((sum, event) => sum + event.location.lng, 0) / items.length,
      events: items,
    };
  });
}

function EventTipBody({ events }: { events: EventItem[] }) {
  const multi = events.length > 1;
  return (
    <>
      {multi && (
        <p className="event-hover-card-heading">
          {events.length} events
        </p>
      )}
      <div className={multi ? "event-tip-scroll min-w-48" : "min-w-44"}>
        <div className={multi ? "space-y-1" : undefined}>
          {events.map((event) => {
            const body = (
              <>
                <p className="font-display text-sm text-cream">{event.title}</p>
                <p className="mt-0.5 text-[11px] text-mute">{formatWhen(event.starts_at)}</p>
                <p className="mt-0.5 text-[11px] text-gold">{event.cost_estimate}</p>
                {(event.tags || []).length > 0 && (
                  <p className="mt-0.5 text-[11px] capitalize text-cream/80">{event.tags.join(" · ")}</p>
                )}
              </>
            );
            return multi ? (
              <Link
                key={event.id}
                href={`/events/${event.id}`}
                className="-mx-1 block rounded-lg px-1.5 py-1.5 hover:bg-ink"
              >
                {body}
              </Link>
            ) : (
              <div key={event.id}>{body}</div>
            );
          })}
        </div>
      </div>
    </>
  );
}

function ClusterHoverCard({
  cluster,
  onEnter,
  onLeave,
}: {
  cluster: EventCluster;
  onEnter: () => void;
  onLeave: () => void;
}) {
  const map = useMap();
  const cardRef = useRef<HTMLDivElement>(null);
  const [, tick] = useReducer((n: number) => n + 1, 0);
  useMapEvents({ move: tick, zoom: tick });

  useEffect(() => {
    const el = cardRef.current;
    if (!el) return;
    L.DomEvent.disableScrollPropagation(el);
    L.DomEvent.disableClickPropagation(el);
    map.scrollWheelZoom.disable();
    return () => {
      map.scrollWheelZoom.enable();
    };
  }, [map]);

  const container = map.getContainer();
  const point = map.latLngToContainerPoint([cluster.lat, cluster.lng]);
  const pad = 136;
  const left = Math.min(Math.max(point.x, pad), Math.max(pad, container.clientWidth - pad));
  const flipDown = point.y < 280;

  return createPortal(
    <div
      ref={cardRef}
      className={`event-hover-card ${cluster.events.length > 1 ? "event-hover-card-list" : ""} ${flipDown ? "event-hover-card-below" : ""}`}
      style={{ left, top: point.y }}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
    >
      <EventTipBody events={cluster.events} />
    </div>,
    container,
  );
}

function ClusteredMarkers({ events }: { events: EventItem[] }) {
  const map = useMap();
  const router = useRouter();
  const hideTimer = useRef<number | null>(null);
  const [zoom, setZoom] = useState(() => map.getZoom());
  const [activeId, setActiveId] = useState<string | null>(null);

  useMapEvents({
    zoomend() {
      setZoom(map.getZoom());
      setActiveId(null);
    },
    movestart() {
      setActiveId(null);
    },
  });

  const clusters = useMemo(() => clusterEvents(events, map), [events, map, zoom]);
  const active = clusters.find((cluster) => cluster.id === activeId) ?? null;

  function show(id: string) {
    if (hideTimer.current) window.clearTimeout(hideTimer.current);
    setActiveId(id);
  }

  function hideSoon() {
    if (hideTimer.current) window.clearTimeout(hideTimer.current);
    hideTimer.current = window.setTimeout(() => setActiveId(null), 160);
  }

  return (
    <>
      {clusters.map((cluster) => (
        <Marker
          key={cluster.id}
          position={[cluster.lat, cluster.lng]}
          icon={pinIconFor(cluster.events)}
          eventHandlers={{
            mouseover: () => show(cluster.id),
            mouseout: hideSoon,
            click: () => {
              if (cluster.events.length === 1) router.push(`/events/${cluster.events[0].id}`);
              else show(cluster.id);
            },
          }}
        />
      ))}
      {active && <ClusterHoverCard cluster={active} onEnter={() => show(active.id)} onLeave={hideSoon} />}
    </>
  );
}

function Recenter({ origin, nonce = 0, zoom }: { origin: Origin; nonce?: number; zoom?: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView([origin.lat, origin.lng], zoom ?? map.getZoom());
  }, [map, origin.lat, origin.lng, nonce, zoom]);
  return null;
}

function MapGestures({
  onPick,
  onMapInteract,
  onViewIdle,
}: {
  onPick?: (origin: Origin) => void;
  onMapInteract?: () => void;
  onViewIdle?: (center: Origin) => void;
}) {
  const idleTimer = useRef<number | null>(null);
  const map = useMap();

  useMapEvents({
    click(e) {
      onMapInteract?.();
      onPick?.({ lat: e.latlng.lat, lng: e.latlng.lng });
    },
    dragstart() {
      onMapInteract?.();
      if (idleTimer.current) window.clearTimeout(idleTimer.current);
    },
    zoomstart() {
      onMapInteract?.();
      if (idleTimer.current) window.clearTimeout(idleTimer.current);
    },
    moveend() {
      if (!onViewIdle) return;
      if (idleTimer.current) window.clearTimeout(idleTimer.current);
      idleTimer.current = window.setTimeout(() => {
        const center = map.getCenter();
        onViewIdle({ lat: center.lat, lng: center.lng });
      }, 280);
    },
  });
  useEffect(() => {
    return () => {
      if (idleTimer.current) window.clearTimeout(idleTimer.current);
    };
  }, []);
  return null;
}

type Props = {
  origin: Origin;
  events?: EventItem[];
  pick?: Origin | null;
  onPick?: (origin: Origin) => void;
  onMapInteract?: () => void;
  onViewIdle?: (center: Origin) => void;
  onUserLocationClick?: () => void;
  focusNonce?: number;
  zoom?: number;
  recenterZoom?: number;
  userLocation?: Origin | null;
};

export default function EventMap({
  origin,
  events = [],
  pick,
  onPick,
  onMapInteract,
  onViewIdle,
  onUserLocationClick,
  focusNonce = 0,
  zoom = 13,
  recenterZoom,
  userLocation,
}: Props) {
  const center = pick ?? origin;
  const [tileUrl, setTileUrl] = useState(DEFAULT_TILES);

  useEffect(() => {
    client
      .mapConfig()
      .then((config) => {
        if (config.tile_url) setTileUrl(config.tile_url);
      })
      .catch(() => setTileUrl(DEFAULT_TILES));
  }, []);

  return (
    <MapContainer
      center={[center.lat, center.lng]}
      zoom={zoom}
      className="h-full w-full"
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; CARTO'
        url={tileUrl}
      />
      <Recenter origin={center} nonce={focusNonce} zoom={recenterZoom} />
      <MapGestures onPick={onPick} onMapInteract={onMapInteract} onViewIdle={onViewIdle} />
      <ClusteredMarkers events={events} />
      {userLocation && (
        <Marker
          position={[userLocation.lat, userLocation.lng]}
          icon={getUserDotIcon()}
          zIndexOffset={400}
          eventHandlers={{
            click: (e) => {
              L.DomEvent.stop(e.originalEvent);
              onUserLocationClick?.();
            },
          }}
        />
      )}
      {pick && (
        <Marker position={[pick.lat, pick.lng]} icon={singlePinIcon("community")}>
          <Tooltip permanent className="event-tip">
            New event
          </Tooltip>
        </Marker>
      )}
    </MapContainer>
  );
}
