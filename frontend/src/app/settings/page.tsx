"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { RadiusSlider } from "@/components/RadiusSlider";
import { RequireAuth } from "@/components/RequireAuth";
import { client } from "@/lib/api";
import { clearToken } from "@/lib/auth";
import { logApp, logScanEnd, logScanEvent, logScanStart } from "@/lib/devlog";
import { radiusMiToSlider, sliderToRadiusMi } from "@/lib/radius";

const NOTIFY_STORAGE_KEY = "eventsai.notify.prefs";

const NOTIFY_CHANNELS = [
  { id: "email", label: "Email" },
  { id: "text", label: "Text" },
] as const;

const NOTIFY_KINDS = [
  { id: "invites", label: "Event invites" },
  { id: "reminders", label: "Event reminders" },
  { id: "updates", label: "Time & place changes" },
  { id: "nearby", label: "New nearby events" },
] as const;

type NotifyChannel = (typeof NOTIFY_CHANNELS)[number]["id"];
type NotifyKind = (typeof NOTIFY_KINDS)[number]["id"];
type NotifyKey = `${NotifyChannel}:${NotifyKind}`;
type NotifyPrefs = Record<NotifyKey, boolean>;

const DEFAULT_NOTIFY: NotifyPrefs = {
  "email:invites": true,
  "email:reminders": true,
  "email:updates": true,
  "email:nearby": false,
  "text:invites": true,
  "text:reminders": false,
  "text:updates": true,
  "text:nearby": false,
};

function loadNotifyPrefs(): NotifyPrefs {
  if (typeof window === "undefined") return DEFAULT_NOTIFY;
  try {
    const raw = localStorage.getItem(NOTIFY_STORAGE_KEY);
    if (!raw) return DEFAULT_NOTIFY;
    return { ...DEFAULT_NOTIFY, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_NOTIFY;
  }
}

function NotifyToggle({
  label,
  on,
  onToggle,
}: {
  label: string;
  on: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      onClick={onToggle}
      className={`flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-left text-sm transition ${
        on
          ? "border-gold/50 bg-gold/10 text-cream"
          : "border-line bg-transparent text-mute hover:border-gold/40 hover:text-cream"
      }`}
    >
      <span>{label}</span>
      <span
        className={`relative h-5 w-9 shrink-0 rounded-full transition ${on ? "bg-gold" : "bg-line"}`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-card shadow-sm transition ${
            on ? "left-[18px]" : "left-0.5"
          }`}
        />
      </span>
    </button>
  );
}

function Settings() {
  const router = useRouter();
  const [radiusSlider, setRadiusSlider] = useState(radiusMiToSlider(3));
  const [isAdmin, setIsAdmin] = useState(false);
  const [notify, setNotify] = useState<NotifyPrefs>(DEFAULT_NOTIFY);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const radius = sliderToRadiusMi(radiusSlider);

  useEffect(() => {
    setNotify(loadNotifyPrefs());
    client.me().then((me) => {
      setRadiusSlider(radiusMiToSlider(me.default_radius_mi));
      setIsAdmin(Boolean(me.is_admin) || me.email.toLowerCase() === "admin@admin.com");
    });
  }, []);

  async function saveRadius() {
    await client.patchMe({ default_radius_mi: radius });
    setMessage("Default radius saved.");
  }

  async function run(kind: "scan" | "cluster") {
    setBusy(true);
    setMessage("");
    try {
      if (kind === "scan") {
        logScanStart();
        setMessage("Scan running — open the browser console (F12) for live pipeline logs.");
        const last = await client.scanStream((event) => {
          logScanEvent(event);
          setMessage(event.message);
        });
        logScanEnd();
        setMessage(JSON.stringify(last));
      } else {
        logApp("cluster", "Starting user cluster job");
        const res = await client.cluster();
        logApp("cluster", "Cluster finished", res);
        setMessage(JSON.stringify(res));
      }
    } catch (err) {
      if (kind === "scan") logScanEnd();
      setMessage(err instanceof Error ? err.message : "Job failed");
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    clearToken();
    router.replace("/login");
  }

  return (
    <div className="mx-auto h-full max-w-2xl overflow-auto px-8 py-8">
      <h1 className="font-display text-4xl text-cream">Settings</h1>
      <section className="mt-8 rounded-2xl border border-line bg-card p-5">
        <h2 className="text-sm text-cream">Default search radius</h2>
        <div className="mt-4 flex items-center gap-3">
          <RadiusSlider
            slider={radiusSlider}
            onSliderChange={setRadiusSlider}
            valueClassName="min-w-[3.75rem] text-sm text-gold"
          />
          <button className="btn-ghost" onClick={saveRadius}>
            Save
          </button>
        </div>
      </section>
      <section className="mt-6 rounded-2xl border border-line bg-card p-5">
        <h2 className="text-sm text-cream">Notifications</h2>
        <p className="mt-2 text-sm text-mute">
          Choose how you hear about invites, reminders, and nearby meetups.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {NOTIFY_CHANNELS.map((channel) => (
            <div key={channel.id} className="flex flex-col gap-2">
              <p className="text-[11px] uppercase tracking-[0.18em] text-mute">{channel.label}</p>
              {NOTIFY_KINDS.map((kind) => {
                const key: NotifyKey = `${channel.id}:${kind.id}`;
                return (
                  <NotifyToggle
                    key={key}
                    label={kind.label}
                    on={notify[key]}
                    onToggle={() => {
                      const next = { ...notify, [key]: !notify[key] };
                      setNotify(next);
                      localStorage.setItem(NOTIFY_STORAGE_KEY, JSON.stringify(next));
                      setMessage("Notification preferences saved.");
                    }}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </section>
      {isAdmin && (
        <section className="mt-6 rounded-2xl border border-line bg-card p-5">
          <h2 className="text-sm text-cream">AI jobs</h2>
          <p className="mt-2 text-sm text-mute">
            Parallel scan of the top 100 listings in every implemented city. Pages are summarized with inception/mercury-2.5 via Inception, then saved with that city.
          </p>
          <div className="mt-4 flex gap-3">
            <button className="btn-gold" disabled={busy} onClick={() => run("scan")}>
              Run scan
            </button>
            <button className="btn-ghost" disabled={busy} onClick={() => run("cluster")}>
              Run cluster
            </button>
          </div>
        </section>
      )}
      {message && <p className="mt-4 break-all text-xs text-mute">{message}</p>}
      <button className="btn-ghost mt-10" onClick={logout}>
        Log out
      </button>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <RequireAuth>
      <AppShell>
        <Settings />
      </AppShell>
    </RequireAuth>
  );
}
