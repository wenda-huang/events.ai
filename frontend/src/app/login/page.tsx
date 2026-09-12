"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { client } from "@/lib/api";
import { setToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await client.login(email, password);
      setToken(res.access_token);
      const me = await client.me();
      router.replace(me.onboarded ? "/map" : "/onboarding");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-dvh place-items-center bg-[radial-gradient(circle_at_top,_#3a2a12,_#14110e_55%)] px-4">
      <form onSubmit={onSubmit} className="w-full max-w-md rounded-3xl border border-line bg-panel p-8 shadow-lift">
        <p className="text-[11px] uppercase tracking-[0.24em] text-gold">Pittsburgh</p>
        <h1 className="mt-2 font-display text-4xl text-cream">Meet in the city.</h1>
        <p className="mt-2 text-sm text-mute">Sign in to see nearby events on the map.</p>
        <label className="mt-8 block text-xs uppercase tracking-wide text-mute">Email</label>
        <input className="field mt-2" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <label className="mt-4 block text-xs uppercase tracking-wide text-mute">Password</label>
        <input className="field mt-2" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        {error && <p className="mt-3 text-sm text-rust">{error}</p>}
        <button className="btn-gold mt-6 w-full" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <p className="mt-5 text-center text-sm text-mute">
          New here?{" "}
          <Link href="/register" className="text-gold">
            Create an account
          </Link>
        </p>
      </form>
    </div>
  );
}
