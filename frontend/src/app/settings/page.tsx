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

function Settings() {
  const router = useRouter();
  const [radiusSlider, setRadiusSlider] = useState(radiusMiToSlider(3));
  const [isAdmin, setIsAdmin] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const radius = sliderToRadiusMi(radiusSlider);

  useEffect(() => {
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
        <h2 className="text-sm text-cream">AI jobs</h2>
        {isAdmin && (
          <p className="mt-2 text-sm text-mute">
            Parallel scan of the top 100 listings in every implemented city. Pages are summarized with inception/mercury-2.5 via Inception, then saved with that city.
          </p>
        )}
        <div className="mt-4 flex gap-3">
          {isAdmin && (
            <button className="btn-gold" disabled={busy} onClick={() => run("scan")}>
              Run scan
            </button>
          )}
          <button className="btn-ghost" disabled={busy} onClick={() => run("cluster")}>
            Run cluster
          </button>
        </div>
      </section>
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
