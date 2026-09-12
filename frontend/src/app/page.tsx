"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { getToken } from "@/lib/auth";

export default function HomePage() {
  const router = useRouter();
  useEffect(() => {
    router.replace(getToken() ? "/map" : "/login");
  }, [router]);
  return (
    <div className="grid h-dvh place-items-center bg-ink text-mute">
      <p className="text-sm tracking-wide">Loading…</p>
    </div>
  );
}
