"use client";

import { FormEvent, useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { TagPicker } from "@/components/TagPicker";
import { client } from "@/lib/api";

function Profile() {
  const [tags, setTags] = useState<string[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([client.tags(), client.me()]).then(([tagRes, me]) => {
      setTags(tagRes.tags);
      setSelected(me.tags);
      setName(me.name);
      setPhone(me.phone || "");
      setEmail(me.email);
    });
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await client.patchMe({ name, phone, tags: selected });
      setMessage("Profile saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    } finally {
      setBusy(false);
    }
  }

  async function refreshLocation() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(async (pos) => {
      await client.patchMe({ lat: pos.coords.latitude, lng: pos.coords.longitude });
      setMessage("Location updated.");
    });
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto h-full max-w-2xl overflow-auto px-8 py-8">
      <h1 className="font-display text-4xl text-cream">My profile</h1>
      <p className="mt-2 text-sm text-mute">{email}</p>
      <label className="mt-8 block text-xs uppercase tracking-wide text-mute">Name</label>
      <input className="field mt-2" value={name} onChange={(e) => setName(e.target.value)} />
      <label className="mt-4 block text-xs uppercase tracking-wide text-mute">Contact</label>
      <input className="field mt-2" value={phone} onChange={(e) => setPhone(e.target.value)} />
      <div className="mt-6">
        <p className="mb-3 text-xs uppercase tracking-wide text-mute">Interests</p>
        <TagPicker tags={tags} selected={selected} onChange={setSelected} />
      </div>
      <div className="mt-6 flex gap-3">
        <button className="btn-gold" disabled={busy}>
          {busy ? "Saving…" : "Save profile"}
        </button>
        <button type="button" className="btn-ghost" onClick={refreshLocation}>
          Update location
        </button>
      </div>
      {message && <p className="mt-4 text-sm text-river">{message}</p>}
      {error && <p className="mt-4 text-sm text-rust">{error}</p>}
    </form>
  );
}

export default function ProfilePage() {
  return (
    <RequireAuth>
      <AppShell>
        <Profile />
      </AppShell>
    </RequireAuth>
  );
}
