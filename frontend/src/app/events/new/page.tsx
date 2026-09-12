"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { TagPicker } from "@/components/TagPicker";
import { client } from "@/lib/api";
import { DEFAULT_ORIGIN, defaultWindow, nearestCity } from "@/lib/geo";
import type { City, Origin } from "@/lib/types";

const EventMap = dynamic(() => import("@/components/EventMap"), { ssr: false });

function CreateEvent() {
  const router = useRouter();
  const windowDefaults = defaultWindow();
  const [tags, setTags] = useState<string[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [address, setAddress] = useState("");
  const [starts, setStarts] = useState(windowDefaults.start);
  const [ends, setEnds] = useState(windowDefaults.end);
  const [peopleMin, setPeopleMin] = useState(2);
  const [peopleMax, setPeopleMax] = useState(12);
  const [cost, setCost] = useState("Free");
  const [pick, setPick] = useState<Origin>(DEFAULT_ORIGIN);
  const [located, setLocated] = useState(false);
  const [geoHint, setGeoHint] = useState("");
  const [geoBusy, setGeoBusy] = useState(false);
  const [focusNonce, setFocusNonce] = useState(0);
  const [cities, setCities] = useState<City[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    client.tags().then((res) => setTags(res.tags));
    client.cities().then((res) => setCities(res.cities));
  }, []);

  useEffect(() => {
    const query = address.trim();
    if (query.length < 3) {
      setLocated(false);
      setGeoBusy(false);
      setGeoHint(query ? "Keep typing an address" : "");
      return;
    }
    let cancelled = false;
    setGeoBusy(true);
    setGeoHint("Looking up that address…");
    const timer = window.setTimeout(async () => {
      try {
        const hit = await client.geocode(query);
        if (cancelled) return;
        setPick({ lat: hit.lat, lng: hit.lng });
        setLocated(true);
        setFocusNonce((n) => n + 1);
        setGeoHint(hit.address && hit.address !== query ? hit.address : "Pinned from this address");
      } catch {
        if (cancelled) return;
        setLocated(false);
        setGeoHint("Could not find that address");
      } finally {
        if (!cancelled) setGeoBusy(false);
      }
    }, 450);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [address]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const query = address.trim();
    if (!query) {
      setError("Add an address so we can place the event on the map");
      return;
    }
    setBusy(true);
    setError("");
    try {
      let coords = located ? pick : null;
      if (!coords) {
        const hit = await client.geocode(query);
        coords = { lat: hit.lat, lng: hit.lng };
        setPick(coords);
        setLocated(true);
      }
      const city = nearestCity(coords, cities);
      const created = await client.createEvent({
        title,
        description,
        address: query,
        city: city?.name ?? "",
        city_id: city?.id,
        lat: coords.lat,
        lng: coords.lng,
        starts_at: new Date(starts).toISOString(),
        ends_at: new Date(ends).toISOString(),
        people_min: peopleMin,
        people_max: peopleMax,
        cost_estimate: cost,
        tags: selected,
      });
      router.push(`/events/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create event");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[1.1fr_0.9fr]">
      <form onSubmit={onSubmit} className="overflow-auto px-8 py-8">
        <h1 className="font-display text-4xl text-cream">Post an event</h1>
        <p className="mt-2 text-sm text-mute">
          Enter a street or venue. Mapbox places the pin there — not at your current location.
        </p>
        <label className="mt-6 block text-xs uppercase tracking-wide text-mute">Title</label>
        <input className="field mt-2" value={title} onChange={(e) => setTitle(e.target.value)} required />
        <label className="mt-4 block text-xs uppercase tracking-wide text-mute">Description</label>
        <textarea className="field mt-2 min-h-28" value={description} onChange={(e) => setDescription(e.target.value)} />
        <label className="mt-4 block text-xs uppercase tracking-wide text-mute">Address</label>
        <input
          className="field mt-2"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="Street, venue, or neighborhood"
          required
        />
        {geoHint && <p className={`mt-2 text-xs ${located ? "text-gold" : "text-mute"}`}>{geoHint}</p>}
        <div className="mt-4 grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs uppercase tracking-wide text-mute">Starts</label>
            <input className="field mt-2" type="datetime-local" value={starts} onChange={(e) => setStarts(e.target.value)} required />
          </div>
          <div>
            <label className="block text-xs uppercase tracking-wide text-mute">Ends</label>
            <input className="field mt-2" type="datetime-local" value={ends} onChange={(e) => setEnds(e.target.value)} required />
          </div>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-3">
          <div>
            <label className="block text-xs uppercase tracking-wide text-mute">Min</label>
            <input className="field mt-2" type="number" min={1} value={peopleMin} onChange={(e) => setPeopleMin(Number(e.target.value))} />
          </div>
          <div>
            <label className="block text-xs uppercase tracking-wide text-mute">Max</label>
            <input className="field mt-2" type="number" min={1} value={peopleMax} onChange={(e) => setPeopleMax(Number(e.target.value))} />
          </div>
          <div>
            <label className="block text-xs uppercase tracking-wide text-mute">Cost</label>
            <input className="field mt-2" value={cost} onChange={(e) => setCost(e.target.value)} />
          </div>
        </div>
        <div className="mt-5">
          <TagPicker tags={tags} selected={selected} onChange={setSelected} />
        </div>
        {error && <p className="mt-4 text-sm text-rust">{error}</p>}
        <button className="btn-gold mt-6" disabled={busy || geoBusy}>
          {busy ? "Publishing…" : "Publish event"}
        </button>
      </form>
      <div className="h-full border-l border-line">
        <EventMap
          origin={pick}
          pick={located ? pick : null}
          focusNonce={focusNonce}
          zoom={located ? 15 : 12}
          recenterZoom={located ? 15 : 12}
        />
      </div>
    </div>
  );
}

export default function NewEventPage() {
  return (
    <RequireAuth>
      <AppShell>
        <CreateEvent />
      </AppShell>
    </RequireAuth>
  );
}
