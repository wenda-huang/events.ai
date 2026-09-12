"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { client } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { User } from "@/lib/types";

type Props = {
  children: React.ReactNode;
  requireOnboarded?: boolean;
};

export function RequireAuth({ children, requireOnboarded = true }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    client
      .me()
      .then((me) => {
        if (cancelled) return;
        if (requireOnboarded && !me.onboarded) {
          router.replace("/onboarding");
          return;
        }
        if (!requireOnboarded && me.onboarded && pathname === "/onboarding") {
          router.replace("/map");
          return;
        }
        setUser(me);
        setReady(true);
      })
      .catch((err) => {
        if (cancelled) return;
        if (!getToken()) {
          router.replace("/login");
          return;
        }
        setError(err instanceof Error ? err.message : "Can't reach the API. Is the backend running on port 8000?");
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, requireOnboarded]);

  if (error) {
    return (
      <div className="grid h-dvh place-items-center bg-ink px-6 text-center">
        <div>
          <p className="font-display text-2xl text-cream">Can’t load the app</p>
          <p className="mt-2 text-sm text-mute">{error}</p>
          <button className="btn-gold mt-6" onClick={() => window.location.reload()}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!ready || !user) {
    return (
      <div className="grid h-dvh place-items-center bg-ink text-mute">
        <p className="text-sm tracking-wide">Loading…</p>
      </div>
    );
  }

  return <>{children}</>;
}
