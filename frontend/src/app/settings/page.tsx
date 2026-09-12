"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { client } from "@/lib/api";
import { clearToken } from "@/lib/auth";

function Settings() {
  const router = useRouter();
  const [radius, setRadius] = useState(3);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    client.me().then((me) => setRadius(me.default_radius_mi));
  }, []);

  async function saveRadius() {
    await client.patchMe({ default_radius_mi: radius });
    setMessage("Default radius saved.");
  }

  async function run(kind: "scan" | "cluster") {
    setBusy(true);
    setMessage("");
    try {
      const res = kind === "scan" ? await client.scan() : await client.cluster();
      setMessage(JSON.stringify(res));
    } catch (err) {
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
          <input type="range" min={1} max={15} step={0.5} value={radius} onChange={(e) => setRadius(Number(e.target.value))} />
          <span className="text-sm text-gold">{radius} mi</span>
          <button className="btn-ghost" onClick={saveRadius}>
            Save
          </button>
        </div>
      </section>
      <section className="mt-6 rounded-2xl border border-line bg-card p-5">
        <h2 className="text-sm text-cream">AI jobs</h2>
        <p className="mt-2 text-sm text-mute">
          Scan Pittsburgh listings with Querit, then cluster nearby users and auto-invite them. Jobs also run every 6 hours on the server.
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
