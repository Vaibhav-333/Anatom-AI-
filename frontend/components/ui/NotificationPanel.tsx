"use client";

import { useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bell, X, CheckCheck, FileText, Sparkles, Leaf,
  Activity, Pill, CheckCircle2, Brain, Stethoscope,
  Download, Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  useNotificationStore,
  AppNotification,
  NotificationType,
} from "@/lib/notificationStore";

// ── Type → visual config ──────────────────────────────────────────────────────

const TYPE_CONFIG: Record<
  NotificationType,
  { icon: React.ElementType; color: string; bg: string; border: string }
> = {
  report_analyzed:  { icon: FileText,     color: "#0A84FF", bg: "rgba(10,132,255,0.10)",  border: "rgba(10,132,255,0.25)" },
  report_generated: { icon: Sparkles,     color: "#0A84FF", bg: "rgba(10,132,255,0.10)",  border: "rgba(10,132,255,0.25)" },
  plan_generated:   { icon: Leaf,         color: "#32D74B", bg: "rgba(50,215,75,0.10)",   border: "rgba(50,215,75,0.25)"  },
  plan_error:       { icon: X,            color: "#FF453A", bg: "rgba(255,69,58,0.10)",   border: "rgba(255,69,58,0.25)"  },
  symptom_logged:   { icon: Activity,     color: "#0A84FF", bg: "rgba(10,132,255,0.10)",  border: "rgba(10,132,255,0.25)" },
  medication_added: { icon: Pill,         color: "#32D74B", bg: "rgba(50,215,75,0.10)",   border: "rgba(50,215,75,0.25)"  },
  dose_logged:      { icon: CheckCircle2, color: "#32D74B", bg: "rgba(50,215,75,0.10)",   border: "rgba(50,215,75,0.25)"  },
  insights_ready:   { icon: Brain,        color: "#BF5AF2", bg: "rgba(191,90,242,0.10)",  border: "rgba(191,90,242,0.25)" },
  doctor_saved:     { icon: Stethoscope,  color: "#0A84FF", bg: "rgba(10,132,255,0.10)",  border: "rgba(10,132,255,0.25)" },
  export_ready:     { icon: Download,     color: "#FF9F0A", bg: "rgba(255,159,10,0.10)",  border: "rgba(255,159,10,0.25)" },
};

// ── Relative time ─────────────────────────────────────────────────────────────

function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  if (diff < 60_000) return "just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return `${Math.floor(diff / 86_400_000)}d ago`;
}

// ── Notification row ──────────────────────────────────────────────────────────

function NotificationRow({ n }: { n: AppNotification }) {
  const { markRead, remove } = useNotificationStore();
  const cfg = TYPE_CONFIG[n.type];
  const Icon = cfg.icon;

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.15 }}
      onClick={() => markRead(n.id)}
      className="flex gap-3 px-4 py-3 cursor-pointer transition-colors duration-100"
      style={{
        borderBottom: "1px solid var(--border-subtle)",
        background: n.read ? "" : "rgba(10,132,255,0.025)",
      }}
      onMouseOver={(e) => {
        (e.currentTarget as HTMLElement).style.background = n.read
          ? "var(--bg-hover)"
          : "rgba(10,132,255,0.045)";
      }}
      onMouseOut={(e) => {
        (e.currentTarget as HTMLElement).style.background = n.read ? "" : "rgba(10,132,255,0.025)";
      }}
    >
      {/* Icon */}
      <div
        className="p-2 rounded-xl shrink-0 mt-0.5"
        style={{
          background: cfg.bg,
          border: `1px solid ${cfg.border}`,
        }}
      >
        <Icon className="w-3.5 h-3.5" style={{ color: cfg.color }} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p
            className="text-xs font-semibold leading-tight"
            style={{ color: n.read ? "var(--label-secondary)" : "var(--label-primary)" }}
          >
            {n.title}
          </p>
          <div className="flex items-center gap-1.5 shrink-0">
            {!n.read && (
              <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: "var(--accent-blue)" }} />
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                remove(n.id);
              }}
              className="p-0.5 rounded transition-colors"
              style={{ color: "var(--label-quaternary)" }}
              onMouseOver={(e) => { (e.currentTarget as HTMLElement).style.color = "var(--label-secondary)"; }}
              onMouseOut={(e) => { (e.currentTarget as HTMLElement).style.color = "var(--label-quaternary)"; }}
              aria-label="Dismiss"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        </div>
        <p className="text-xs mt-0.5 leading-snug" style={{ color: "var(--label-secondary)" }}>{n.body}</p>
        <p className="text-[10px] font-mono mt-1" style={{ color: "var(--label-tertiary)" }}>
          {relativeTime(n.timestamp)}
        </p>
      </div>
    </motion.div>
  );
}

// ── Panel ─────────────────────────────────────────────────────────────────────

export function NotificationPanel({ onClose }: { onClose: () => void }) {
  const { notifications, markAllRead, clearAll } = useNotificationStore();
  const ref = useRef<HTMLDivElement>(null);
  const unread = notifications.filter((n) => !n.read).length;

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: -8, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -8, scale: 0.96 }}
      transition={{ duration: 0.18, ease: "easeOut" }}
      className="absolute right-0 top-full mt-2 w-80 rounded-2xl overflow-hidden z-50"
      style={{
        background: "var(--glass-bg)",
        border: "1px solid var(--border-default)",
        boxShadow: "var(--glass-shadow-lg)",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3"
        style={{ borderBottom: "1px solid var(--border-subtle)" }}
      >
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4" style={{ color: "var(--accent-blue)" }} />
          <span className="text-sm font-semibold" style={{ color: "var(--label-primary)" }}>Notifications</span>
          {unread > 0 && (
            <span
              className="px-1.5 py-0.5 rounded-full text-[10px] font-bold leading-none"
              style={{ background: "var(--accent-blue)", color: "#fff" }}
            >
              {unread}
            </span>
          )}
        </div>
        <div className="flex items-center gap-0.5">
          {unread > 0 && (
            <button
              onClick={markAllRead}
              className="p-1.5 rounded-lg transition-colors"
              style={{ color: "var(--label-tertiary)" }}
              onMouseOver={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--bg-hover)"; (e.currentTarget as HTMLElement).style.color = "var(--label-secondary)"; }}
              onMouseOut={(e) => { (e.currentTarget as HTMLElement).style.background = ""; (e.currentTarget as HTMLElement).style.color = "var(--label-tertiary)"; }}
              title="Mark all as read"
            >
              <CheckCheck className="w-3.5 h-3.5" />
            </button>
          )}
          {notifications.length > 0 && (
            <button
              onClick={clearAll}
              className="p-1.5 rounded-lg transition-colors"
              style={{ color: "var(--label-tertiary)" }}
              onMouseOver={(e) => { (e.currentTarget as HTMLElement).style.background = "rgba(255,69,58,0.10)"; (e.currentTarget as HTMLElement).style.color = "#FF453A"; }}
              onMouseOut={(e) => { (e.currentTarget as HTMLElement).style.background = ""; (e.currentTarget as HTMLElement).style.color = "var(--label-tertiary)"; }}
              title="Clear all"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg transition-colors"
            style={{ color: "var(--label-tertiary)" }}
            onMouseOver={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--bg-hover)"; (e.currentTarget as HTMLElement).style.color = "var(--label-secondary)"; }}
            onMouseOut={(e) => { (e.currentTarget as HTMLElement).style.background = ""; (e.currentTarget as HTMLElement).style.color = "var(--label-tertiary)"; }}
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* List */}
      <div className="max-h-[420px] overflow-y-auto">
        {notifications.length === 0 ? (
          <div className="py-12 flex flex-col items-center gap-3">
            <div
              className="w-12 h-12 rounded-2xl flex items-center justify-center"
              style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)" }}
            >
              <Bell className="w-5 h-5" style={{ color: "var(--label-tertiary)" }} />
            </div>
            <p className="text-sm font-medium" style={{ color: "var(--label-secondary)" }}>All caught up</p>
            <p className="text-xs text-center max-w-[200px] leading-relaxed" style={{ color: "var(--label-tertiary)" }}>
              Activity updates will appear here as you use the app
            </p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {notifications.map((n) => (
              <NotificationRow key={n.id} n={n} />
            ))}
          </AnimatePresence>
        )}
      </div>

      {/* Footer */}
      {notifications.length > 0 && (
        <div className="px-4 py-2.5" style={{ borderTop: "1px solid var(--border-subtle)" }}>
          <p className="text-[10px] font-mono text-center" style={{ color: "var(--label-tertiary)" }}>
            {notifications.length} notification{notifications.length !== 1 ? "s" : ""}
            {unread > 0 ? ` · ${unread} unread` : " · all read"}
          </p>
        </div>
      )}
    </motion.div>
  );
}
