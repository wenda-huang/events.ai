"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { TagPicker } from "@/components/TagPicker";
import { client } from "@/lib/api";
import { defaultWindow, PITTSBURGH } from "@/lib/geo";
import type { Origin } from "@/lib/types";

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
  const [pick, setPick] = useState<Origin>(PITTSBURGH);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    client.tags().then((res) => setTags(res.tags));
    client.me().then((me) => {
      if (me.lat != null && me.lng != null) setPick({ lat: me.lat, lng: me.lng });
    });
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const created = await client.createEvent({
        title,
        description,
        address,
        city: "Pittsburgh",
        lat: pick.lat,
        lng: pick.lng,
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
        <p className="mt-2 text-sm text-mute">Click the map to drop a pin. You are automatically signed up as host.</p>
        <label className="mt-6 block text-xs uppercase tracking-wide text-mute">Title</label>
        <input className="field mt-2" value={title} onChange={(e) => setTitle(e.target.value)} required />
        <label className="mt-4 block text-xs uppercase tracking-wide text-mute">Description</label>
        <textarea className="field mt-2 min-h-28" value={description} onChange={(e) => setDescription(e.target.value)} />
        <label className="mt-4 block text-xs uppercase tracking-wide text-mute">Address</label>
        <input className="field mt-2" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Neighborhood or street" />
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
        <button className="btn-gold mt-6" disabled={busy}>
          {busy ? "Publishing…" : "Publish event"}
        </button>
      </form>
      <div className="h-full border-l border-line">
        <EventMap origin={pick} pick={pick} onPick={setPick} zoom={13} />
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
