"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { RequireAuth } from "@/components/RequireAuth";
import { TagPicker } from "@/components/TagPicker";
import { client } from "@/lib/api";
import { DEFAULT_ORIGIN, defaultCity } from "@/lib/geo";

function OnboardingForm() {
  const router = useRouter();
  const [tags, setTags] = useState<string[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [lat, setLat] = useState<number>(DEFAULT_ORIGIN.lat);
  const [lng, setLng] = useState<number>(DEFAULT_ORIGIN.lng);
  const [locLabel, setLocLabel] = useState("Finding your city…");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    client.tags().then((res) => setTags(res.tags));
    client.me().then((me) => {
      if (me.name) setName(me.name);
    });
    client.cities().then((res) => {
      const fallback = defaultCity(res.cities);
      if (!navigator.geolocation) {
        if (fallback) {
          setLat(fallback.lat);
          setLng(fallback.lng);
          setLocLabel(`Using downtown ${fallback.label}`);
        }
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLat(pos.coords.latitude);
          setLng(pos.coords.longitude);
          setLocLabel("Using your current location");
        },
        () => {
          if (fallback) {
            setLat(fallback.lat);
            setLng(fallback.lng);
            setLocLabel(`Location blocked — using downtown ${fallback.label}`);
          }
        },
        { enableHighAccuracy: true, timeout: 8000 }
      );
    });
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (selected.length === 0) {
      setError("Pick at least one event tag.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await client.onboard({ name, phone, tags: selected, lat, lng });
      router.replace("/map");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Onboarding failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-dvh overflow-auto bg-ink px-4 py-10">
      <form onSubmit={onSubmit} className="mx-auto max-w-2xl rounded-3xl border border-line bg-panel p-8 shadow-lift">
        <p className="text-[11px] uppercase tracking-[0.24em] text-gold">Onboarding</p>
        <h1 className="mt-2 font-display text-4xl text-cream">What are you down for?</h1>
        <p className="mt-2 text-sm text-mute">We’ll use this to recommend nearby meetups and cluster you with people nearby.</p>
        <div className="mt-8">
          <TagPicker tags={tags} selected={selected} onChange={setSelected} />
        </div>
        <label className="mt-8 block text-xs uppercase tracking-wide text-mute">Name</label>
        <input className="field mt-2" value={name} onChange={(e) => setName(e.target.value)} required />
        <label className="mt-4 block text-xs uppercase tracking-wide text-mute">Contact</label>
        <input className="field mt-2" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Phone or other contact" />
        <p className="mt-4 text-xs text-mute">{locLabel}</p>
        {error && <p className="mt-3 text-sm text-rust">{error}</p>}
        <button className="btn-gold mt-6" disabled={busy}>
          {busy ? "Saving…" : "Show me the map"}
        </button>
      </form>
    </div>
  );
}

export default function OnboardingPage() {
  return (
    <RequireAuth requireOnboarded={false}>
      <OnboardingForm />
    </RequireAuth>
  );
}
