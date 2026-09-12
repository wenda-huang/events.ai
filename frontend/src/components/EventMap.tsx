"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import L from "leaflet";
import { MapContainer, Marker, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";

import { client } from "@/lib/api";
import { formatWhen } from "@/lib/geo";
import type { EventItem, Origin } from "@/lib/types";

import "leaflet/dist/leaflet.css";

const DEFAULT_TILES = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";

const pin = L.divIcon({
  className: "event-pin",
  html: '<span class="pin-dot"></span>',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

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
  const router = useRouter();
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
      {events
        .filter((event) => Number.isFinite(event.location?.lat) && Number.isFinite(event.location?.lng))
        .map((event) => (
        <Marker
          key={event.id}
          position={[event.location.lat, event.location.lng]}
          icon={pin}
          eventHandlers={{
            click: () => router.push(`/events/${event.id}`),
          }}
        >
          <Tooltip className="event-tip" direction="top" offset={[0, -10]} opacity={1}>
            <div className="min-w-44">
              <p className="font-display text-sm text-cream">{event.title}</p>
              <p className="mt-1 text-[11px] text-mute">{formatWhen(event.starts_at)}</p>
              <p className="mt-1 text-[11px] text-gold">{event.cost_estimate}</p>
              <p className="mt-1 text-[11px] capitalize text-cream/80">{(event.tags || []).join(" · ")}</p>
            </div>
          </Tooltip>
        </Marker>
      ))}
      {pick && (
        <Marker position={[pick.lat, pick.lng]} icon={pin}>
          <Tooltip permanent className="event-tip">
            New event
          </Tooltip>
        </Marker>
      )}
    </MapContainer>
  );
}
