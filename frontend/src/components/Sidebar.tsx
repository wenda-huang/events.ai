"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/map", label: "Map" },
  { href: "/my-events", label: "My events" },
  { href: "/profile", label: "My profile" },
  { href: "/settings", label: "Settings" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-[240px] shrink-0 flex-col border-r border-line bg-panel px-5 py-6">
      <Link href="/map" className="mb-10 block">
        <p className="font-display text-2xl tracking-tight text-cream">
          events<span className="text-gold">.ai</span>
        </p>
      </Link>
      <nav className="flex flex-1 flex-col gap-1">
        {LINKS.map((link) => {
          const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`rounded-xl px-3 py-2.5 text-sm ${
                active ? "bg-gold/15 text-gold" : "text-mute hover:bg-ink hover:text-cream"
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
      <Link href="/events/new" className="btn-gold w-full">
        Post an event
      </Link>
    </aside>
  );
}
