"use client";

import { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, Minus, Activity, Siren, Clock } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { AlertBox } from "@/components/ui/AlertBox";
import type { GuidanceResponse, RiskLevel, DietRecommendation, RedFlag } from "@/lib/types";

// ── Props ──────────────────────────────────────────────────────────────────
interface GuidancePanelProps {
  guidance: GuidanceResponse;
  riskLevel: RiskLevel;
  reportId?: string;
}

// ── Timeline column (optionally checkable) ─────────────────────────────────
function TimelineColumn({
  label,
  items,
  accent,
  checkedKeys,
  onToggle,
}: {
  label: string;
  items: string[];
  accent: string;
  checkedKeys?: Set<string>;
  onToggle?: (key: string) => void;
}) {
  const checkable = Boolean(checkedKeys && onToggle);
  return (
    <div className="p-3 rounded-xl bg-navy-700 border border-glass-border">
      <p className={`text-xs font-semibold uppercase tracking-widest mb-2.5 ${accent}`}>
        {label}
      </p>
      <ul className="space-y-1.5">
        {items.slice(0, 5).map((action, i) => {
          const key = `${label}-${i}`;
          const checked = checkedKeys?.has(key) ?? false;
          return (
            <li key={i} className="flex items-start gap-2 text-xs leading-relaxed">
              {checkable ? (
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggle!(key)}
                  className="mt-0.5 shrink-0 cursor-pointer accent-cyan-400"
                />
              ) : (
                <span className={`shrink-0 mt-0.5 ${accent}`}>→</span>
              )}
              <span className={checked ? "line-through text-slate-600" : "text-slate-400"}>
                {action}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ── Nutrition card ─────────────────────────────────────────────────────────
function NutritionCard({ items }: { items: DietRecommendation[] }) {
  const directionIcon = (dir: "up" | "down" | "neutral") => {
    if (dir === "up") return <TrendingUp className="w-3.5 h-3.5 text-green-400 shrink-0" />;
    if (dir === "down") return <TrendingDown className="w-3.5 h-3.5 text-red-400 shrink-0" />;
    return <Minus className="w-3.5 h-3.5 text-slate-500 shrink-0" />;
  };
  const dirColor = (dir: "up" | "down" | "neutral") => {
    if (dir === "up") return "text-green-400";
    if (dir === "down") return "text-red-400";
    return "text-slate-400";
  };

  return (
    <GlassCard>
      <h4 className="section-title text-sm mb-3">Nutrition</h4>
      <div className="space-y-2.5">
        {items.slice(0, 6).map((item, i) => (
          <div key={i} className="flex items-start gap-2.5">
            {directionIcon(item.direction)}
            <div>
              <span className={`text-xs font-semibold ${dirColor(item.direction)}`}>
                {item.nutrient}
              </span>
              <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{item.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}

// ── Exercise card ──────────────────────────────────────────────────────────
function ExerciseCard({ guidance }: { guidance: GuidanceResponse["exercise_guidance"] }) {
  return (
    <GlassCard>
      <div className="flex items-center gap-2 mb-3">
        <Activity className="w-4 h-4 text-cyan shrink-0" />
        <h4 className="section-title text-sm">Exercise</h4>
      </div>
      <p className="text-xs text-slate-500 mb-3">
        Frequency: <span className="text-cyan">{guidance.frequency}</span>
      </p>
      <div className="space-y-2">
        {guidance.recommended.slice(0, 4).map((ex, i) => (
          <div key={i} className="flex items-center justify-between py-1.5 border-b border-glass-border last:border-0">
            <span className="text-xs text-slate-300">{ex.name}</span>
            <span className="text-xs text-slate-500 font-mono">
              {ex.duration}{ex.frequency ? ` · ${ex.frequency}` : ""}
            </span>
          </div>
        ))}
      </div>
      {guidance.avoid.length > 0 && (
        <div className="mt-3 p-2.5 rounded-lg bg-red-500/5 border border-red-500/20">
          <p className="text-xs text-red-400 font-medium mb-1">Avoid:</p>
          {guidance.avoid.map((a, i) => (
            <p key={i} className="text-xs text-slate-500">• {a}</p>
          ))}
        </div>
      )}
    </GlassCard>
  );
}

// ── Red flags card ─────────────────────────────────────────────────────────
function RedFlagsCard({ flags }: { flags: RedFlag[] }) {
  if (!flags || flags.length === 0) return null;

  const severityConfig = (sev: RedFlag["severity"]) => {
    if (sev === "er") return {
      bg: "bg-red-500/10 border-red-500/30",
      dot: "bg-red-500 animate-pulse",
      label: "EMERGENCY",
      color: "text-red-400",
    };
    if (sev === "urgent") return {
      bg: "bg-amber-500/10 border-amber-500/30",
      dot: "bg-amber-500",
      label: "URGENT",
      color: "text-amber-400",
    };
    return {
      bg: "bg-slate-700/50 border-glass-border",
      dot: "bg-slate-500",
      label: "MONITOR",
      color: "text-slate-400",
    };
  };

  return (
    <GlassCard className="border border-red-500/20">
      <div className="flex items-center gap-2 mb-3">
        <Siren className="w-4 h-4 text-red-400 shrink-0" />
        <h4 className="section-title text-sm text-red-400">Red Flags</h4>
      </div>
      <div className="space-y-2.5">
        {flags.map((flag, i) => {
          const cfg = severityConfig(flag.severity);
          return (
            <div key={i} className={`flex items-start gap-3 p-3 rounded-lg border ${cfg.bg}`}>
              <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${cfg.dot}`} />
              <div>
                <p className={`text-xs font-semibold ${cfg.color}`}>
                  <span className="mr-1.5">[{cfg.label}]</span>
                  {flag.sign}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">{flag.action}</p>
              </div>
            </div>
          );
        })}
      </div>
    </GlassCard>
  );
}

// ── Consequence timeline card ───────────────────────────────────────────────
function ConsequenceCard({ text }: { text: string }) {
  if (!text) return null;
  return (
    <GlassCard className="border border-amber-500/20">
      <div className="flex items-center gap-2 mb-2">
        <Clock className="w-4 h-4 text-amber-400 shrink-0" />
        <h4 className="section-title text-sm text-amber-400">If Left Untreated</h4>
      </div>
      <p className="text-xs text-slate-400 leading-relaxed">{text}</p>
    </GlassCard>
  );
}

// ── Main GuidancePanel ─────────────────────────────────────────────────────
export function GuidancePanel({ guidance, riskLevel, reportId }: GuidancePanelProps) {
  const storageKey = reportId ? `guidance_checklist_${reportId}` : null;

  const [checkedKeys, setCheckedKeys] = useState<Set<string>>(new Set());

  // Load checklist state from localStorage on mount
  useEffect(() => {
    if (!storageKey) return;
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) setCheckedKeys(new Set(JSON.parse(stored) as string[]));
    } catch {
      // ignore parse errors
    }
  }, [storageKey]);

  const handleToggle = (key: string) => {
    setCheckedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      if (storageKey) {
        try { localStorage.setItem(storageKey, JSON.stringify(Array.from(next))); } catch { /* quota */ }
      }
      return next;
    });
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <GlassCard>
        <h3 className="section-title text-base mb-1">Health Guidance</h3>
        <p className="text-xs text-slate-500">AI-generated wellness plan based on your report findings.</p>
      </GlassCard>

      {/* Red flags — shown first if present */}
      {guidance.red_flags && guidance.red_flags.length > 0 && (
        <RedFlagsCard flags={guidance.red_flags} />
      )}

      {/* 3-column timeline (24h + 7d are checkable) */}
      <GlassCard>
        <h4 className="section-title text-sm mb-3">Action Plan</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <TimelineColumn
            label="Next 24 Hours"
            items={guidance.immediate_actions}
            accent="text-red-400"
            checkedKeys={checkedKeys}
            onToggle={handleToggle}
          />
          <TimelineColumn
            label="This Week"
            items={guidance.weekly_plan}
            accent="text-amber-400"
            checkedKeys={checkedKeys}
            onToggle={handleToggle}
          />
          <TimelineColumn
            label="This Month"
            items={guidance.monthly_plan}
            accent="text-green-400"
          />
        </div>
      </GlassCard>

      {/* Consequence timeline */}
      {guidance.consequence_timeline && (
        <ConsequenceCard text={guidance.consequence_timeline} />
      )}

      {/* Nutrition + Exercise side by side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {guidance.diet_recommendations && guidance.diet_recommendations.length > 0 && (
          <NutritionCard items={guidance.diet_recommendations} />
        )}
        {guidance.exercise_guidance && (
          <ExerciseCard guidance={guidance.exercise_guidance} />
        )}
      </div>

      {/* Warning signs */}
      {guidance.warning_signs && guidance.warning_signs.length > 0 && (
        <AlertBox variant="warning" title="Watch for these warning signs">
          <ul className="space-y-1 mt-1">
            {guidance.warning_signs.map((w, i) => (
              <li key={i} className="text-xs">• {w}</li>
            ))}
          </ul>
        </AlertBox>
      )}

      {/* Supplements */}
      {guidance.supplements && guidance.supplements.length > 0 && (
        <GlassCard>
          <h4 className="section-title text-sm mb-2">Supplements to Consider</h4>
          <ul className="space-y-1">
            {guidance.supplements.map((s, i) => (
              <li key={i} className="text-xs text-slate-400 flex items-start gap-2">
                <span className="text-cyan shrink-0">•</span>{s}
              </li>
            ))}
          </ul>
        </GlassCard>
      )}

      {/* Disclaimer */}
      <p className="text-xs text-slate-600 text-center leading-relaxed px-4">
        {guidance.disclaimer}
      </p>
    </div>
  );
}
