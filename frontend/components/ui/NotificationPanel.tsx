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
  report_analyzed: {
    icon: FileText, color: "text-cyan",
    bg: "bg-cyan/10", border: "border-cyan/25",
  },
  report_generated: {
    icon: Sparkles, color: "text-cyan",
    bg: "bg-cyan/10", border: "border-cyan/25",
  },
  plan_generated: {
    icon: Leaf, color: "text-green-400",
    bg: "bg-green-400/10", border: "border-green-400/25",
  },
  symptom_logged: {
    icon: Activity, color: "text-cyan",
    bg: "bg-cyan/10", border: "border-cyan/25",
  },
  medication_added: {
    icon: Pill, color: "text-green-400",
    bg: "bg-green-400/10", border: "border-green-400/25",
  },
  dose_logged: {
    icon: CheckCircle2, color: "text-green-400",
    bg: "bg-green-400/10", border: "border-green-400/25",
  },
  insights_ready: {
    icon: Brain, color: "text-purple-400",
    bg: "bg-purple-400/10", border: "border-purple-400/25",
  },
  doctor_saved: {
    icon: Stethoscope, color: "text-cyan",
    bg: "bg-cyan/10", border: "border-cyan/25",
  },
  export_ready: {
    icon: Download, color: "text-amber-400",
    bg: "bg-amber-400/10", border: "border-amber-400/25",
  },
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
      className={cn(
        "flex gap-3 px-4 py-3 cursor-pointer transition-colors duration-100",
        "border-b border-white/[0.04] last:border-b-0",
        n.read
          ? "hover:bg-white/[0.02]"
          : "bg-cyan/[0.025] hover:bg-cyan/[0.045]"
      )}
    >
      {/* Icon */}
      <div
        className={cn(
          "p-2 rounded-xl border shrink-0 mt-0.5",
          cfg.bg, cfg.border
        )}
      >
        <Icon className={cn("w-3.5 h-3.5", cfg.color)} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p
            className={cn(
              "text-xs font-semibold leading-tight",
              n.read ? "text-slate-400" : "text-white"
            )}
          >
            {n.title}
          </p>
          <div className="flex items-center gap-1.5 shrink-0">
            {!n.read && (
              <span className="w-1.5 h-1.5 rounded-full bg-cyan shrink-0" />
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                remove(n.id);
              }}
              className="p-0.5 rounded text-slate-700 hover:text-slate-400 transition-colors"
              aria-label="Dismiss"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        </div>
        <p className="text-xs text-slate-500 mt-0.5 leading-snug">{n.body}</p>
        <p className="text-[10px] text-slate-600 font-mono mt-1">
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
        background: "rgba(10,15,30,0.98)",
        border: "1px solid rgba(0,212,255,0.15)",
        boxShadow:
          "0 24px 64px rgba(0,0,0,0.75), 0 0 40px rgba(0,212,255,0.05)",
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-cyan" />
          <span className="text-sm font-semibold text-white">Notifications</span>
          {unread > 0 && (
            <span className="px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-cyan text-navy-900 leading-none">
              {unread}
            </span>
          )}
        </div>
        <div className="flex items-center gap-0.5">
          {unread > 0 && (
            <button
              onClick={markAllRead}
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-white/5 transition-colors"
              title="Mark all as read"
            >
              <CheckCheck className="w-3.5 h-3.5" />
            </button>
          )}
          {notifications.length > 0 && (
            <button
              onClick={clearAll}
              className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-white/5 transition-colors"
              title="Clear all"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-white/5 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* List */}
      <div className="max-h-[420px] overflow-y-auto scrollbar-thin scrollbar-track-transparent scrollbar-thumb-slate-700">
        {notifications.length === 0 ? (
          <div className="py-12 flex flex-col items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-navy-800 border border-glass-border flex items-center justify-center">
              <Bell className="w-5 h-5 text-slate-600" />
            </div>
            <p className="text-sm text-slate-500 font-medium">All caught up</p>
            <p className="text-xs text-slate-600 text-center max-w-[200px] leading-relaxed">
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
        <div className="px-4 py-2.5 border-t border-white/[0.04]">
          <p className="text-[10px] text-slate-600 font-mono text-center">
            {notifications.length} notification{notifications.length !== 1 ? "s" : ""}
            {unread > 0 ? ` · ${unread} unread` : " · all read"}
          </p>
        </div>
      )}
    </motion.div>
  );
}
