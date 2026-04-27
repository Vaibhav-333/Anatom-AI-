"use client";

const RISK_CONFIG = {
  low: { label: "LOW RISK", bg: "bg-green/10", border: "border-green/40", text: "text-green", dot: "bg-green" },
  medium: { label: "MEDIUM RISK", bg: "bg-amber-500/10", border: "border-amber-500/40", text: "text-amber-400", dot: "bg-amber-400" },
  high: { label: "HIGH RISK", bg: "bg-red-500/10", border: "border-red-500/40", text: "text-red-400", dot: "bg-red-400" },
  critical: { label: "CRITICAL", bg: "bg-purple-500/10", border: "border-purple-500/40", text: "text-purple-400", dot: "bg-purple-400" },
};

export function RiskBadge({ level, size = "md" }: { level: string; size?: "sm" | "md" | "lg" }) {
  const cfg = RISK_CONFIG[level as keyof typeof RISK_CONFIG] ?? RISK_CONFIG.low;
  const sz = size === "sm" ? "text-xs px-2 py-0.5" : size === "lg" ? "text-sm px-4 py-2" : "text-xs px-3 py-1";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border font-bold font-mono ${cfg.bg} ${cfg.border} ${cfg.text} ${sz}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot} animate-pulse`} />
      {cfg.label}
    </span>
  );
}
