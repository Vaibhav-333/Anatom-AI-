"use client";

import { useState, useCallback } from "react";
import { Bell, User } from "lucide-react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { SettingsDropdown } from "@/components/ui/SettingsDropdown";
import { NotificationPanel } from "@/components/ui/NotificationPanel";
import { useNotificationStore } from "@/lib/notificationStore";

const pageTitles: Record<string, string> = {
  "/": "Dashboard",
  "/upload": "Upload Report",
  "/viewer": "3D Body Viewer",
  "/results": "Analysis Results",
  "/profile": "Health Profile",
  "/history": "Report History",
};

export function TopBar() {
  const pathname = usePathname();
  const [panelOpen, setPanelOpen] = useState(false);
  const unread = useNotificationStore(
    (s) => s.notifications.filter((n) => !n.read).length
  );

  const title =
    Object.entries(pageTitles).find(([path]) =>
      path === "/" ? pathname === "/" : pathname.startsWith(path)
    )?.[1] ?? "Anatom-AI";

  const handleBellClick = () => setPanelOpen((v) => !v);
  const closePanel = useCallback(() => setPanelOpen(false), []);

  return (
    <header className="fixed top-0 right-0 left-60 z-30 h-14">
      {/* Background */}
      <div
        className="absolute inset-0"
        style={{
          background: "var(--bg-topbar)",
          backdropFilter: "blur(20px) saturate(180%)",
          WebkitBackdropFilter: "blur(20px) saturate(180%)",
          borderBottom: "1px solid var(--border-default)",
          transition: "background 0.3s ease, border-color 0.3s ease",
        }}
      />

      <div className="relative h-full flex items-center justify-between px-6">
        {/* Page title */}
        <div className="flex items-center gap-3">
          <h2
            className="font-semibold tracking-tight"
            style={{ color: "var(--label-primary)", fontSize: "14px", letterSpacing: "-0.01em" }}
          >
            {title}
          </h2>
          <div
            className="w-px h-4"
            style={{ background: "var(--separator)" }}
          />
          <span
            className="text-[11px] font-mono"
            style={{ color: "var(--label-tertiary)" }}
          >
            {new Date().toLocaleDateString("en-US", {
              weekday: "short",
              month: "short",
              day: "numeric",
            })}
          </span>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1">
          {/* Bell */}
          <div className="relative">
            <button
              onClick={handleBellClick}
              className={cn(
                "p-2 rounded-xl transition-all duration-160 relative"
              )}
              style={
                panelOpen
                  ? { background: "rgba(10,132,255,0.16)", color: "#0A84FF" }
                  : { color: "var(--label-secondary)" }
              }
              onMouseOver={(e) => { if (!panelOpen) (e.currentTarget as HTMLElement).style.background = "var(--bg-hover)"; (e.currentTarget as HTMLElement).style.color = "var(--label-primary)"; }}
              onMouseOut={(e) => { if (!panelOpen) { (e.currentTarget as HTMLElement).style.background = ""; (e.currentTarget as HTMLElement).style.color = "var(--label-secondary)"; } }}
              aria-label="Notifications"
            >
              <Bell className="w-4 h-4" />
              {unread > 0 && (
                <span
                  className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full text-[9px] font-bold flex items-center justify-center leading-none"
                  style={{ background: "#FF453A", color: "#fff" }}
                >
                  {unread > 9 ? "9+" : unread}
                </span>
              )}
            </button>

            <AnimatePresence>
              {panelOpen && <NotificationPanel onClose={closePanel} />}
            </AnimatePresence>
          </div>

          <Link
            href="/profile"
            className="p-2 rounded-xl transition-all duration-200"
            style={{ color: "var(--label-secondary)" }}
            onMouseOver={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--bg-hover)"; (e.currentTarget as HTMLElement).style.color = "var(--label-primary)"; }}
            onMouseOut={(e) => { (e.currentTarget as HTMLElement).style.background = ""; (e.currentTarget as HTMLElement).style.color = "var(--label-secondary)"; }}
            aria-label="Profile"
          >
            <User className="w-4 h-4" />
          </Link>

          <SettingsDropdown />
        </div>
      </div>
    </header>
  );
}
