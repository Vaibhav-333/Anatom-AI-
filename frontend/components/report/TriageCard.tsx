"use client";

import { motion } from "framer-motion";
import { AlertTriangle, ShieldCheck, AlertCircle, Siren } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import type { TriageResult, TriageLevel } from "@/lib/types";

// ── Config per triage level ─────────────────────────────────────────────────

interface LevelConfig {
  label: string;
  emoji: string;
  icon: React.ReactNode;
  border: string;
  bg: string;
  badge: string;
  badgeBg: string;
  glow: string;
}

const LEVEL_CONFIGS: Record<TriageLevel, LevelConfig> = {
  low: {
    label: "Low",
    emoji: "🟢",
    icon: <ShieldCheck className="w-5 h-5 text-emerald-400" />,
    border: "border-emerald-500/30",
    bg: "bg-emerald-500/5",
    badge: "text-emerald-400",
    badgeBg: "bg-emerald-500/10 border border-emerald-500/20",
    glow: "shadow-emerald-500/10",
  },
  moderate: {
    label: "Moderate",
    emoji: "🟡",
    icon: <AlertCircle className="w-5 h-5 text-amber-400" />,
    border: "border-amber-500/30",
    bg: "bg-amber-500/5",
    badge: "text-amber-400",
    badgeBg: "bg-amber-500/10 border border-amber-500/20",
    glow: "shadow-amber-500/10",
  },
  high: {
    label: "High",
    emoji: "🔴",
    icon: <AlertTriangle className="w-5 h-5 text-red-400" />,
    border: "border-red-500/40",
    bg: "bg-red-500/8",
    badge: "text-red-400",
    badgeBg: "bg-red-500/10 border border-red-500/25",
    glow: "shadow-red-500/15",
  },
  emergency: {
    label: "Emergency",
    emoji: "🚨",
    icon: <Siren className="w-5 h-5 text-red-300" />,
    border: "border-red-400/60",
    bg: "bg-red-500/12",
    badge: "text-red-300",
    badgeBg: "bg-red-500/20 border border-red-400/40",
    glow: "shadow-red-500/25",
  },
};

// ── Component ───────────────────────────────────────────────────────────────

interface TriageCardProps {
  triage: TriageResult | null | undefined;
}

export function TriageCard({ triage }: TriageCardProps) {
  // Unavailable state — show subtle placeholder
  if (!triage) {
    return (
      <GlassCard>
        <div className="flex items-center gap-2 text-slate-600">
          <ShieldCheck className="w-4 h-4" />
          <span className="text-xs">Triage analysis not available for this report.</span>
        </div>
      </GlassCard>
    );
  }

  const level = triage.level in LEVEL_CONFIGS ? triage.level : "low";
  const cfg = LEVEL_CONFIGS[level];

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
    >
      <GlassCard className={`border ${cfg.border} ${cfg.bg} shadow-lg ${cfg.glow}`}>
        {/* Header row */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            {cfg.icon}
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-0.5">
                AI Triage Assessment
              </p>
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-sm font-bold ${cfg.badge}`}>
                  Risk Level:
                </span>
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${cfg.badgeBg} ${cfg.badge}`}>
                  {cfg.emoji} {cfg.label}
                </span>
              </div>
            </div>
          </div>

          {/* Emergency pulse indicator */}
          {level === "emergency" && (
            <span className="relative flex h-3 w-3 mt-1 shrink-0">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
            </span>
          )}
        </div>

        {/* Recommendation */}
        <div className="mt-3 pl-8">
          <p className={`text-sm font-medium ${cfg.badge}`}>
            {triage.recommendation}
          </p>

          {/* Explanation */}
          {triage.explanation && (
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              {triage.explanation}
            </p>
          )}

          {/* Triggered-by chips */}
          {triage.triggered_by?.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              <span className="text-xs text-slate-600 font-medium self-center">
                Contributing factors:
              </span>
              {triage.triggered_by.map((factor, i) => (
                <span
                  key={i}
                  className={`text-xs px-2 py-0.5 rounded-full ${cfg.badgeBg} ${cfg.badge}`}
                >
                  {factor}
                </span>
              ))}
            </div>
          )}
        </div>
      </GlassCard>
    </motion.div>
  );
}
