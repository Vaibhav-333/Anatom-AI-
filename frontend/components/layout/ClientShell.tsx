"use client";

import { Suspense } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { AICopilot } from "@/components/copilot/AICopilot";

const AUTH_PREFIXES = ["/login", "/signup", "/forgot-password", "/health-profile"];

interface Props {
  children: React.ReactNode;
}

/**
 * ClientShell renders the dashboard shell (Sidebar + TopBar) for all routes
 * except the auth pages, which get a plain full-page layout.
 */
export function ClientShell({ children }: Props) {
  const pathname = usePathname();
  const isAuthPage = AUTH_PREFIXES.some((p) => pathname.startsWith(p));

  if (isAuthPage) {
    return (
      <main className="relative z-10 min-h-screen">
        {children}
      </main>
    );
  }

  return (
    <>
      <Sidebar />
      <TopBar />
      <main className="relative z-10 ml-60 mt-14 min-h-[calc(100vh-3.5rem)] p-6">
        {children}
      </main>
      {/* AI Health Copilot — global floating assistant */}
      <Suspense fallback={null}>
        <AICopilot />
      </Suspense>
    </>
  );
}
