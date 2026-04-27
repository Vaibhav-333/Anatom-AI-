"use client";
import { AlertTriangle, TrendingUp, TrendingDown, Bell, Info } from "lucide-react";
import { InsightAlert } from "@/lib/healthTrackerStore";

const SEV_STYLES: Record<string, { border: string; bg: string; icon: string; text: string }> = {
  critical: { border: "#FF3B3B", bg: "#FF3B3B18", icon: "#FF3B3B", text: "#FF3B3B" },
  warning:  { border: "#FFB800", bg: "#FFB80018", icon: "#FFB800", text: "#FFB800" },
  info:     { border: "#00D4FF", bg: "#00D4FF18", icon: "#00D4FF", text: "#00D4FF" },
};

const TYPE_ICONS: Record<string, React.ElementType> = {
  anomaly:      AlertTriangle,
  deterioration:TrendingDown,
  improvement:  TrendingUp,
  reminder:     Bell,
};

export default function InsightAlertCard({ alert }: { alert: InsightAlert }) {
  const sev = SEV_STYLES[alert.severity] ?? SEV_STYLES.info;
  const Icon = TYPE_ICONS[alert.type] ?? Info;

  return (
    <div
      className="flex gap-3 rounded-xl p-4"
      style={{ background: sev.bg, borderLeft: `3px solid ${sev.border}` }}
    >
      <Icon size={18} style={{ color: sev.icon, flexShrink: 0, marginTop: 2 }} />
      <div>
        <p className="text-sm font-semibold" style={{ color: sev.text }}>{alert.title}</p>
        <p className="text-xs text-gray-400 mt-0.5">{alert.message}</p>
      </div>
    </div>
  );
}
