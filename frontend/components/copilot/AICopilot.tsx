"use client";

import { useEffect } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { useCopilotStore } from "@/lib/copilotStore";
import { FloatingChatButton } from "./FloatingChatButton";
import { ChatTray } from "./ChatTray";
import { ChatWindow } from "./ChatWindow";

/**
 * AICopilot — global orchestrator mounted once in ClientShell.
 * Reads page context (pathname + search params) to pass report IDs
 * and current page name into the copilot store.
 */
export function AICopilot() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { setCurrentPage, setCurrentReportId } = useCopilotStore();

  useEffect(() => {
    // Derive context page from pathname
    if (pathname.startsWith("/results/")) {
      const reportId = pathname.split("/results/")[1]?.split("/")[0] || null;
      setCurrentPage("results");
      setCurrentReportId(reportId);
    } else if (pathname.startsWith("/upload")) {
      setCurrentPage("upload");
      setCurrentReportId(null);
    } else if (pathname.startsWith("/history")) {
      setCurrentPage("history");
      setCurrentReportId(null);
    } else if (pathname === "/") {
      setCurrentPage("dashboard");
      setCurrentReportId(null);
    } else {
      setCurrentPage(pathname.slice(1).split("/")[0] || "dashboard");
      setCurrentReportId(null);
    }
  }, [pathname]);

  return (
    <>
      <FloatingChatButton />
      <ChatTray />
      <ChatWindow />
    </>
  );
}
