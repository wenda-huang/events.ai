"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { client } from "@/lib/api";
import { setToken } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await client.register(email, password, name);
      setToken(res.access_token);
      router.replace("/onboarding");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not register");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-dvh place-items-center bg-[radial-gradient(circle_at_top,_#3a2a12,_#14110e_55%)] px-4">
      <form onSubmit={onSubmit} className="w-full max-w-md rounded-3xl border border-line bg-panel p-8 shadow-lift">
        <p className="text-[11px] uppercase tracking-[0.24em] text-gold">Join events.ai</p>
        <h1 className="mt-2 font-display text-4xl text-cream">Create your spot.</h1>
        <label className="mt-8 block text-xs uppercase tracking-wide text-mute">Name</label>
        <input className="field mt-2" value={name} onChange={(e) => setName(e.target.value)} required />
        <label className="mt-4 block text-xs uppercase tracking-wide text-mute">Email</label>
        <input className="field mt-2" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <label className="mt-4 block text-xs uppercase tracking-wide text-mute">Password</label>
        <input className="field mt-2" type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={6} required />
        {error && <p className="mt-3 text-sm text-rust">{error}</p>}
        <button className="btn-gold mt-6 w-full" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>
        <p className="mt-5 text-center text-sm text-mute">
          Already have one?{" "}
          <Link href="/login" className="text-gold">
            Sign in
          </Link>
        </p>
      </form>
    </div>
  );
}
