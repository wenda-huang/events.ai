"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { client } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { AppNotification } from "@/lib/types";

const POLL_MS = 3000;

type NotificationsContextValue = {
  items: AppNotification[];
  unreadCount: number;
  enabled: boolean;
  open: boolean;
  toasts: AppNotification[];
  setOpen: (open: boolean) => void;
  openItem: (item: AppNotification) => void;
  markAllRead: () => void;
  dismissToast: (id: number) => void;
};

const NotificationsContext = createContext<NotificationsContextValue | null>(null);

function relativeTime(iso: string | null) {
  if (!iso) return "";
  const then = new Date(iso.endsWith("Z") ? iso : `${iso}Z`).getTime();
  if (Number.isNaN(then)) return "";
  const delta = Math.max(0, Date.now() - then);
  const minutes = Math.floor(delta / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function isFresh(iso: string | null) {
  if (!iso) return true;
  const then = new Date(iso.endsWith("Z") ? iso : `${iso}Z`).getTime();
  if (Number.isNaN(then)) return true;
  return Date.now() - then < 10 * 60 * 1000;
}

export function NotificationsProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [items, setItems] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [enabled, setEnabled] = useState(true);
  const [open, setOpen] = useState(false);
  const [toasts, setToasts] = useState<AppNotification[]>([]);
  const seenIds = useRef<Set<number>>(new Set());
  const primed = useRef(false);

    const ingest = useCallback((next: AppNotification[], unread: number, live: boolean) => {
    setItems(next);
    setUnreadCount(unread);
    setEnabled(live);
    const unseen = next.filter((item) => !seenIds.current.has(item.id));
    for (const item of next) seenIds.current.add(item.id);
    const toastable = unseen.filter((item) => !item.read && live && isFresh(item.created_at));
    if (!primed.current) {
      primed.current = true;
      if (toastable.length > 0) setToasts((current) => [...toastable, ...current].slice(0, 4));
      return;
    }
    if (unseen.length === 0) return;
    const liveToasts = live ? unseen.filter((item) => !item.read) : [];
    if (liveToasts.length === 0) return;
    setToasts((current) => [...liveToasts, ...current].slice(0, 4));
  }, []);

  const load = useCallback(async () => {
    if (!getToken()) return;
    try {
      const data = await client.notifications();
      ingest(data.notifications, data.unread_count, data.enabled);
    } catch {
      // Keep the last good snapshot while the next poll retries.
    }
  }, [ingest]);

  useEffect(() => {
    load();
    const interval = setInterval(load, POLL_MS);
    return () => clearInterval(interval);
  }, [load, pathname]);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  const dismissToast = useCallback((id: number) => {
    setToasts((current) => current.filter((item) => item.id !== id));
  }, []);

  const openItem = useCallback(
    async (item: AppNotification) => {
      dismissToast(item.id);
      setOpen(false);
      if (!item.read) {
        setItems((current) => current.map((row) => (row.id === item.id ? { ...row, read: true } : row)));
        setUnreadCount((count) => Math.max(0, count - 1));
        try {
          await client.readNotification(item.id);
        } catch {
          load();
        }
      }
      if (item.event_id) router.push(`/events/${item.event_id}`);
    },
    [dismissToast, load, router],
  );

  const markAllRead = useCallback(async () => {
    setItems((current) => current.map((row) => ({ ...row, read: true })));
    setUnreadCount(0);
    try {
      await client.readAllNotifications();
    } catch {
      load();
    }
  }, [load]);

  useEffect(() => {
    if (toasts.length === 0) return;
    const timers = toasts.map((item) => window.setTimeout(() => dismissToast(item.id), 8000));
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [toasts, dismissToast]);

  const value = useMemo(
    () => ({ items, unreadCount, enabled, open, toasts, setOpen, openItem, markAllRead, dismissToast }),
    [items, unreadCount, enabled, open, toasts, openItem, markAllRead, dismissToast],
  );

  return <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>;
}

export function useNotifications() {
  const value = useContext(NotificationsContext);
  if (!value) throw new Error("useNotifications must be used within NotificationsProvider");
  return value;
}

function BellIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4" aria-hidden>
      <path
        d="M10 2.4a4.2 4.2 0 0 0-4.2 4.2v1.3c0 .7-.3 1.4-.8 1.9L4 11.9c-.4.5 0 1.2.6 1.2h10.8c.6 0 1-.7.6-1.2l-1-2.1a2.6 2.6 0 0 1-.8-1.9V6.6A4.2 4.2 0 0 0 10 2.4Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path d="M8 14.4a2 2 0 0 0 4 0" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function NotificationBell() {
  const { items, unreadCount, enabled, open, setOpen, openItem, markAllRead } = useNotifications();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [panelTop, setPanelTop] = useState(120);

  useEffect(() => {
    if (!open) return;
    const top = buttonRef.current?.getBoundingClientRect().top;
    if (top != null) setPanelTop(top);
    function onDoc(event: MouseEvent) {
      const target = event.target as Node;
      if (buttonRef.current?.contains(target) || panelRef.current?.contains(target)) return;
      setOpen(false);
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, setOpen]);

  return (
    <div className="relative mb-4">
      <button
        ref={buttonRef}
        type="button"
        className={`flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-sm ${
          open ? "bg-gold/15 text-gold" : "text-mute hover:bg-ink hover:text-cream"
        }`}
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-label={unreadCount ? `Notifications, ${unreadCount} unread` : "Notifications"}
      >
        <span className="flex items-center gap-2">
          <BellIcon />
          Notifications
        </span>
        {unreadCount > 0 && (
          <span className="min-w-5 rounded-full bg-gold px-1.5 text-center text-[11px] font-semibold text-night">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>
      {open && (
        <div
          ref={panelRef}
          className="fixed z-[1200] w-[22rem] rounded-2xl border border-line bg-card p-3 shadow-lift"
          style={{ left: 252, top: panelTop }}
        >
          <div className="mb-2 flex items-center justify-between px-1">
            <p className="text-xs uppercase tracking-[0.18em] text-mute">{enabled ? "Live" : "Paused"}</p>
            {unreadCount > 0 && (
              <button type="button" className="text-xs text-gold" onClick={markAllRead}>
                Mark all read
              </button>
            )}
          </div>
          <div className="max-h-80 overflow-auto">
            {items.length === 0 && (
              <p className="px-2 py-6 text-center text-sm text-mute">
                {enabled ? "No notifications yet." : "Notifications are turned off in Settings."}
              </p>
            )}
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => openItem(item)}
                className={`mb-1 w-full rounded-xl px-3 py-2.5 text-left hover:bg-ink ${item.read ? "" : "bg-gold/10"}`}
              >
                <p className="text-sm text-cream">{item.title}</p>
                <p className="mt-0.5 text-xs text-mute">{item.body}</p>
                <p className="mt-1 text-[11px] text-mute">{relativeTime(item.created_at)}</p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function NotificationToasts() {
  const { toasts, openItem, dismissToast } = useNotifications();
  if (toasts.length === 0) return null;

  return (
    <div className="pointer-events-none absolute right-4 top-4 z-[1100] flex w-[22rem] max-w-[calc(100%-2rem)] flex-col gap-2">
      {toasts.map((item) => (
        <div
          key={item.id}
          className="notification-toast pointer-events-auto rounded-2xl border border-gold/40 bg-card p-4 shadow-lift"
        >
          <div className="flex items-start justify-between gap-3">
            <button type="button" className="min-w-0 flex-1 text-left" onClick={() => openItem(item)}>
              <p className="text-[11px] uppercase tracking-[0.18em] text-gold">New</p>
              <p className="mt-1 text-sm text-cream">{item.title}</p>
              <p className="mt-0.5 text-xs text-mute">{item.body}</p>
            </button>
            <button type="button" className="text-xs text-mute" onClick={() => dismissToast(item.id)} aria-label="Dismiss">
              Close
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
