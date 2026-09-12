import Link from "next/link";

import { formatWhen } from "@/lib/geo";
import type { EventItem } from "@/lib/types";

export function EventCard({ event }: { event: EventItem }) {
  return (
    <Link href={`/events/${event.id}`} className="block rounded-2xl border border-line bg-card p-4 hover:border-gold/50">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-display text-lg leading-tight text-cream">{event.title}</h3>
        {event.distance_mi != null && <span className="shrink-0 text-xs text-mute">{event.distance_mi} mi</span>}
      </div>
      <p className="mt-1 text-xs text-mute">{formatWhen(event.starts_at)}</p>
      <p className="mt-2 line-clamp-2 text-sm text-cream/80">{event.description}</p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {event.tags.map((tag) => (
          <span key={tag} className="rounded-full bg-ink px-2 py-0.5 text-[10px] uppercase tracking-wide text-gold">
            {tag}
          </span>
        ))}
      </div>
    </Link>
  );
}
