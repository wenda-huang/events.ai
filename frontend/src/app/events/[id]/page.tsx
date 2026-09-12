"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { EventCover } from "@/components/EventCover";
import { RequireAuth } from "@/components/RequireAuth";
import { client } from "@/lib/api";
import { formatWhen } from "@/lib/geo";
import type { EventItem } from "@/lib/types";

const EVENT_POLL_MS = 20000;

function EventDetail() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const [event, setEvent] = useState<EventItem | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;

    function load(background: boolean) {
      client
        .event(id)
        .then((data) => {
          if (!cancelled) setEvent(data);
        })
        .catch((err) => {
          if (!cancelled && !background) setError(err instanceof Error ? err.message : "Not found");
        });
    }

    load(false);
    const interval = setInterval(() => load(true), EVENT_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [id]);

  async function join() {
    setBusy(true);
    try {
      setEvent(await client.signup(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not join");
    } finally {
      setBusy(false);
    }
  }

  async function leave() {
    setBusy(true);
    try {
      setEvent(await client.leave(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not leave");
    } finally {
      setBusy(false);
    }
  }

  if (!event) {
    return <div className="p-10 text-mute">{error || "Loading event…"}</div>;
  }

  return (
    <div className="h-full min-h-0 overflow-auto">
      <div className="mx-auto max-w-3xl px-8 py-10">
        <Link href="/map" className="text-xs uppercase tracking-[0.2em] text-gold">
          Back to map
        </Link>
        <p className="mt-5 text-[11px] uppercase tracking-[0.2em] text-mute">
          {event.source === "ai" ? "AI-discovered" : "Posted by a neighbor"} · {event.location.city}
        </p>
        <h1 className="mt-2 font-display text-5xl leading-tight text-cream">{event.title}</h1>
        <EventCover
          tags={event.tags}
          title={`${event.tags?.[0] || "Event"} cover`}
          className="mt-6 aspect-[16/9] w-full rounded-3xl border border-line"
        />
        <p className="mt-4 text-mute">
          {formatWhen(event.starts_at)} — {formatWhen(event.ends_at)}
          {event.estimated_fields?.includes("ends_at") && (
            <span className="ml-2 text-[10px] uppercase tracking-wide text-gold">end estimated</span>
          )}
        </p>
        <p className="mt-2 text-sm text-cream/80">{event.location.address}</p>
        <div className="mt-6 flex flex-wrap gap-2">
          {event.tags.map((tag) => (
            <span key={tag} className="rounded-full border border-line px-3 py-1 text-xs capitalize text-gold">
              {tag}
            </span>
          ))}
        </div>
        <p className="mt-8 whitespace-pre-wrap text-lg leading-relaxed text-cream/90">{event.description}</p>
        <dl className="mt-8 grid grid-cols-2 gap-4 text-sm">
          <div className="rounded-2xl border border-line bg-card p-4">
            <dt className="text-mute">People</dt>
            <dd className="mt-1 text-cream">
              {event.attendee_count} joined · {event.people_min}–{event.people_max}
              {(event.estimated_fields?.includes("people_min") || event.estimated_fields?.includes("people_max")) && (
                <span className="ml-2 text-[10px] uppercase tracking-wide text-gold">estimated</span>
              )}
            </dd>
          </div>
          <div className="rounded-2xl border border-line bg-card p-4">
            <dt className="text-mute">Cost</dt>
            <dd className="mt-1 text-cream">
              {event.cost_estimate}
              {event.estimated_fields?.includes("cost_estimate") && (
                <span className="ml-2 text-[10px] uppercase tracking-wide text-gold">estimated</span>
              )}
            </dd>
          </div>
        </dl>
        {event.source_url && (
          <a href={event.source_url} className="mt-4 inline-block text-sm text-river" target="_blank" rel="noreferrer">
            Source listing
          </a>
        )}
        {error && <p className="mt-4 text-sm text-rust">{error}</p>}
        <div className="mt-8 flex gap-3">
          {event.my_status === "joined" ? (
            <button className="btn-ghost" onClick={leave} disabled={busy}>
              Leave event
            </button>
          ) : (
            <button className="btn-gold" onClick={join} disabled={busy}>
              {event.my_status === "invited" ? "Accept invite" : "Join event"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function EventPage() {
  return (
    <RequireAuth>
      <AppShell>
        <EventDetail />
      </AppShell>
    </RequireAuth>
  );
}
