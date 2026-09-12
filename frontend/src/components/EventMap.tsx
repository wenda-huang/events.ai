"use client";

import Link from "next/link";
import { useEffect, useMemo, useReducer, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useRouter } from "next/navigation";
import L from "leaflet";
import { MapContainer, Marker, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";

import { client } from "@/lib/api";
import { formatWhen } from "@/lib/geo";
import type { EventItem, Origin } from "@/lib/types";

import "leaflet/dist/leaflet.css";

const DEFAULT_TILES = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";
const CLUSTER_PIXELS = 28;

const pinIcons = new Map<number, L.DivIcon>();

function pinIcon(count: number) {
  const key = count <= 1 ? 1 : count;
  const cached = pinIcons.get(key);
  if (cached) return cached;
  const icon =
    key === 1
      ? L.divIcon({
          className: "event-pin",
          html: '<span class="pin-dot"></span>',
          iconSize: [18, 18],
          iconAnchor: [9, 9],
        })
      : L.divIcon({
          className: "event-pin",
          html: `<span class="pin-dot pin-cluster">${key}</span>`,
          iconSize: [22, 22],
          iconAnchor: [11, 11],
        });
  pinIcons.set(key, icon);
  return icon;
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
    <div className={multi ? "event-tip-scroll min-w-48" : "min-w-44"} onWheel={(e) => e.stopPropagation()}>
      {multi && (
        <p className="mb-2 text-[10px] uppercase tracking-[0.16em] text-gold">
          {events.length} events
        </p>
      )}
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
  const [, tick] = useReducer((n: number) => n + 1, 0);
  useMapEvents({ move: tick, zoom: tick });

  const container = map.getContainer();
  const point = map.latLngToContainerPoint([cluster.lat, cluster.lng]);
  const pad = 136;
  const left = Math.min(Math.max(point.x, pad), Math.max(pad, container.clientWidth - pad));
  const flipDown = point.y < 280;

  return createPortal(
    <div
      className={`event-hover-card ${flipDown ? "event-hover-card-below" : ""}`}
      style={{ left, top: point.y }}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      onMouseDown={(e) => e.stopPropagation()}
      onWheel={(e) => e.stopPropagation()}
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
          icon={pinIcon(cluster.events.length)}
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

function Recenter({ origin }: { origin: Origin }) {
  const map = useMap();
  useEffect(() => {
    map.setView([origin.lat, origin.lng], map.getZoom());
  }, [map, origin.lat, origin.lng]);
  return null;
}

function MapGestures({
  onPick,
  onMapInteract,
}: {
  onPick?: (origin: Origin) => void;
  onMapInteract?: () => void;
}) {
  useMapEvents({
    click(e) {
      onMapInteract?.();
      onPick?.({ lat: e.latlng.lat, lng: e.latlng.lng });
    },
    dragstart() {
      onMapInteract?.();
    },
  });
  return null;
}

type Props = {
  origin: Origin;
  events?: EventItem[];
  pick?: Origin | null;
  onPick?: (origin: Origin) => void;
  onMapInteract?: () => void;
  zoom?: number;
};

export default function EventMap({ origin, events = [], pick, onPick, onMapInteract, zoom = 13 }: Props) {
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
      <Recenter origin={center} />
      <MapGestures onPick={onPick} onMapInteract={onMapInteract} />
      <ClusteredMarkers events={events} />
      {pick && (
        <Marker position={[pick.lat, pick.lng]} icon={pinIcon(1)}>
          <Tooltip permanent className="event-tip">
            New event
          </Tooltip>
        </Marker>
      )}
    </MapContainer>
  );
}
