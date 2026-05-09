"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Settings,
  User,
  LogOut,
  Sun,
  Moon,
  Monitor,
  Bell,
  BellOff,
  Globe,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useAuthStore } from "@/lib/authStore";
import { useTheme } from "@/context/ThemeContext";

type SystemStatus = "online" | "offline" | null;

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p
      className="px-3 pt-3 pb-1 text-[10px] font-semibold tracking-widest uppercase"
      style={{ color: "var(--label-tertiary)" }}
    >
      {children}
    </p>
  );
}

function Divider() {
  return <div className="my-1" style={{ borderTop: "1px solid var(--border-subtle)" }} />;
}

function MenuItem({
  icon: Icon,
  label,
  onClick,
  danger,
  rightEl,
  disabled,
}: {
  icon: React.ElementType;
  label: string;
  onClick?: () => void;
  danger?: boolean;
  rightEl?: React.ReactNode;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors duration-150",
        disabled && "opacity-40 cursor-not-allowed"
      )}
      style={
        danger
          ? { color: "#FF453A" }
          : { color: "var(--label-secondary)" }
      }
      onMouseOver={(e) => {
        if (!disabled) {
          if (danger) {
            (e.currentTarget as HTMLElement).style.background = "rgba(255,69,58,0.10)";
            (e.currentTarget as HTMLElement).style.color = "#FF453A";
          } else {
            (e.currentTarget as HTMLElement).style.background = "var(--bg-hover)";
            (e.currentTarget as HTMLElement).style.color = "var(--label-primary)";
          }
        }
      }}
      onMouseOut={(e) => {
        if (!disabled) {
          (e.currentTarget as HTMLElement).style.background = "";
          (e.currentTarget as HTMLElement).style.color = danger ? "#FF453A" : "var(--label-secondary)";
        }
      }}
    >
      <Icon className="w-4 h-4 shrink-0 opacity-70" />
      <span className="flex-1 text-left">{label}</span>
      {rightEl}
    </button>
  );
}

type Theme = "dark" | "light" | "auto";

const themeOptions: { value: Theme; icon: React.ElementType; label: string }[] = [
  { value: "dark", icon: Moon, label: "Dark" },
  { value: "light", icon: Sun, label: "Light" },
  { value: "auto", icon: Monitor, label: "Auto" },
];

export function SettingsDropdown() {
  const router = useRouter();
  const logout = useAuthStore((s) => s.logout);
  const { theme, setTheme } = useTheme();

  const [open, setOpen] = useState(false);
  const [backendStatus, setBackendStatus] = useState<SystemStatus>(null);
  const [neuroStatus] = useState<SystemStatus>("online");
  const [notifications, setNotifications] = useState(() => {
    if (typeof window === "undefined") return true;
    return localStorage.getItem("anatom-notifs") !== "false";
  });

  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    fetch("/api/health")
      .then((r) => setBackendStatus(r.ok ? "online" : "offline"))
      .catch(() => setBackendStatus("offline"));
  }, [open]);

  const handleLogout = () => {
    setOpen(false);
    logout();
    router.push("/login");
  };

  const toggleNotifications = () => {
    const next = !notifications;
    setNotifications(next);
    localStorage.setItem("anatom-notifs", String(next));
  };

  return (
    <div ref={ref} className="relative">
      {/* Trigger */}
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Settings"
        className="p-2 rounded-lg transition-colors"
        style={
          open
            ? { color: "var(--accent-blue)", background: "rgba(10,132,255,0.12)" }
            : { color: "var(--label-tertiary)" }
        }
        onMouseOver={(e) => { if (!open) { (e.currentTarget as HTMLElement).style.color = "var(--label-secondary)"; (e.currentTarget as HTMLElement).style.background = "var(--bg-hover)"; } }}
        onMouseOut={(e) => { if (!open) { (e.currentTarget as HTMLElement).style.color = "var(--label-tertiary)"; (e.currentTarget as HTMLElement).style.background = ""; } }}
      >
        <Settings className={cn("w-4 h-4 transition-transform duration-300", open && "rotate-45")} />
      </button>

      {/* Dropdown panel */}
      {open && (
        <div
          className="absolute right-0 top-full mt-2 w-64 z-50 rounded-xl"
          style={{
            background: "var(--glass-bg)",
            border: "1px solid var(--border-default)",
            boxShadow: "var(--glass-shadow-lg)",
          }}
        >
          {/* USER */}
          <SectionLabel>User</SectionLabel>
          <div className="px-1 pb-1">
            <MenuItem
              icon={User}
              label="View Profile"
              onClick={() => { setOpen(false); router.push("/profile"); }}
            />
            <MenuItem
              icon={LogOut}
              label="Logout"
              danger
              onClick={handleLogout}
            />
          </div>

          <Divider />

          {/* APPEARANCE */}
          <SectionLabel>Appearance</SectionLabel>
          <div className="px-1 pb-1">
            <div className="px-3 py-2 flex items-center gap-2">
              {themeOptions.map(({ value, icon: Icon, label }) => (
                <button
                  key={value}
                  onClick={() => setTheme(value)}
                  className="flex-1 flex flex-col items-center gap-1 py-1.5 rounded-lg text-xs transition-all duration-150"
                  style={
                    theme === value
                      ? {
                          background: "rgba(10,132,255,0.15)",
                          color: "var(--accent-blue)",
                          border: "1px solid rgba(10,132,255,0.30)",
                        }
                      : {
                          color: "var(--label-tertiary)",
                          border: "1px solid transparent",
                        }
                  }
                  onMouseOver={(e) => { if (theme !== value) { (e.currentTarget as HTMLElement).style.background = "var(--bg-hover)"; (e.currentTarget as HTMLElement).style.color = "var(--label-secondary)"; } }}
                  onMouseOut={(e) => { if (theme !== value) { (e.currentTarget as HTMLElement).style.background = ""; (e.currentTarget as HTMLElement).style.color = "var(--label-tertiary)"; } }}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {label}
                </button>
              ))}
            </div>
          </div>

          <Divider />

          {/* SYSTEM STATUS */}
          <SectionLabel>System Status</SectionLabel>
          <div className="px-3 pb-2 space-y-2">
            {[
              {
                label: "FastAPI Backend",
                detail: "localhost:8000",
                status: backendStatus ?? ("offline" as const),
              },
              {
                label: "NeuroMapper Engine",
                detail: "PyVista renderer",
                status: neuroStatus ?? ("offline" as const),
              },
            ].map((sys) => (
              <div
                key={sys.label}
                className="flex items-center justify-between py-1.5 last:border-0"
                style={{ borderBottom: "1px solid var(--border-subtle)" }}
              >
                <div>
                  <p className="text-xs" style={{ color: "var(--label-secondary)" }}>{sys.label}</p>
                  <p className="text-[10px] font-mono" style={{ color: "var(--label-tertiary)" }}>{sys.detail}</p>
                </div>
                <StatusBadge status={sys.status} />
              </div>
            ))}
          </div>

          <Divider />

          {/* PREFERENCES */}
          <SectionLabel>Preferences</SectionLabel>
          <div className="px-1 pb-2">
            <MenuItem
              icon={notifications ? Bell : BellOff}
              label={notifications ? "Notifications On" : "Notifications Off"}
              onClick={toggleNotifications}
              rightEl={
                <span
                  className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                  style={
                    notifications
                      ? { background: "rgba(10,132,255,0.15)", color: "var(--accent-blue)" }
                      : { background: "var(--bg-elevated)", color: "var(--label-tertiary)" }
                  }
                >
                  {notifications ? "ON" : "OFF"}
                </span>
              }
            />
            <MenuItem
              icon={Globe}
              label="Language"
              disabled
              rightEl={
                <span className="flex items-center gap-1 text-[10px]" style={{ color: "var(--label-tertiary)" }}>
                  EN <ChevronRight className="w-3 h-3" />
                </span>
              }
            />
          </div>
        </div>
      )}
    </div>
  );
}
