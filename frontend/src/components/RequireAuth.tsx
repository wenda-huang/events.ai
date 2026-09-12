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

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    client
      .me()
      .then((me) => {
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
      .catch(() => router.replace("/login"));
  }, [pathname, requireOnboarded, router]);

  if (!ready || !user) {
    return (
      <div className="grid h-dvh place-items-center bg-ink text-mute">
        <p className="text-sm tracking-wide">Loading…</p>
      </div>
    );
  }

  return <>{children}</>;
}
