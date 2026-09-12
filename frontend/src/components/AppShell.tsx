"use client";

import { Sidebar } from "@/components/Sidebar";
import { NotificationToasts, NotificationsProvider } from "@/components/Notifications";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <NotificationsProvider>
      <div className="flex h-dvh overflow-hidden bg-ink">
        <Sidebar />
        <main className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          {children}
          <NotificationToasts />
        </main>
      </div>
    </NotificationsProvider>
  );
}
