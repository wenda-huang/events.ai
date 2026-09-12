"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { EventCard } from "@/components/EventCard";
import { RequireAuth } from "@/components/RequireAuth";
import { client } from "@/lib/api";
import type { EventItem } from "@/lib/types";

function MyEvents() {
  const [joined, setJoined] = useState<EventItem[]>([]);
  const [invited, setInvited] = useState<EventItem[]>([]);
  const [error, setError] = useState("");

  async function reload() {
    const data = await client.myEvents();
    setJoined(data.joined);
    setInvited(data.invited);
  }

  useEffect(() => {
    reload().catch((err) => setError(err instanceof Error ? err.message : "Could not load"));
  }, []);

  async function accept(id: number) {
    await client.signup(id);
    await reload();
  }

  async function decline(id: number) {
    await client.decline(id);
    await reload();
  }

  return (
    <div className="h-full overflow-auto px-8 py-8">
      <h1 className="font-display text-4xl text-cream">My events</h1>
      <p className="mt-2 text-sm text-mute">Joined meetups and AI invites from nearby clusters.</p>
      {error && <p className="mt-4 text-sm text-rust">{error}</p>}
      <section className="mt-8">
        <h2 className="text-[11px] uppercase tracking-[0.2em] text-gold">Invites</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {invited.length === 0 && <p className="text-sm text-mute">No pending invites yet.</p>}
          {invited.map((event) => (
            <div key={event.id} className="space-y-2">
              <EventCard event={event} />
              {event.invite_reason && <p className="px-1 text-xs text-mute">{event.invite_reason}</p>}
              <div className="flex gap-2 px-1">
                <button className="btn-gold" onClick={() => accept(event.id)}>
                  Accept
                </button>
                <button className="btn-ghost" onClick={() => decline(event.id)}>
                  Decline
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
      <section className="mt-10">
        <h2 className="text-[11px] uppercase tracking-[0.2em] text-gold">Joined</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {joined.length === 0 && <p className="text-sm text-mute">You have not signed up for an event yet.</p>}
          {joined.map((event) => (
            <EventCard key={event.id} event={event} />
          ))}
        </div>
      </section>
    </div>
  );
}

export default function MyEventsPage() {
  return (
    <RequireAuth>
      <AppShell>
        <MyEvents />
      </AppShell>
    </RequireAuth>
  );
}
