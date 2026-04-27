"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus, Heart } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ScoreHistoryPoint } from "@/lib/types";

// ── Apple Health colour mapping ───────────────────────────────────────────────
const COLORS = {
  good:     { hex: "#32D74B", label: "Good",     tw: "text-[#32D74B]" },
  moderate: { hex: "#FF9F0A", label: "Moderate",  tw: "text-[#FF9F0A]" },
  critical: { hex: "#FF453A", label: "Critical",  tw: "text-[#FF453A]" },
  none:     { hex: "#636366", label: "No data",   tw: "text-[#636366]" },
};

function getScoreConfig(score: number | null) {
  if (score === null) return COLORS.none;
  if (score >= 71) return COLORS.good;
  if (score >= 41) return COLORS.moderate;
  return COLORS.critical;
}

// ── Sparkline ─────────────────────────────────────────────────────────────────
function Sparkline({ data, color }: { data: number[]; color: string }) {
  if (data.length < 2) return null;
  const W = 76; const H = 22;
  const min = Math.min(...data); const max = Math.max(...data);
  const range = max - min || 1;
  const pts = data
    .map((v, i) => `${(i / (data.length - 1)) * W},${H - ((v - min) / range) * H}`)
    .join(" ");
  const gradId = `hs-${color.replace("#", "")}`;
  return (
    <svg width={W} height={H} className="overflow-visible">
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={color} stopOpacity="0.18" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon fill={`url(#${gradId})`} points={`0,${H} ${pts} ${W},${H}`} />
      <polyline fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" points={pts} />
      {/* tail dot */}
      {(() => {
        const last = data[data.length - 1];
        const x = W; const y = H - ((last - min) / range) * H;
        return <circle cx={x} cy={y} r="2.5" fill={color} />;
      })()}
    </svg>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────
interface HealthScoreCardProps {
  score: number | null;
  history: ScoreHistoryPoint[];
  bodyAge?: number;
}

export function HealthScoreCard({ score, history, bodyAge }: HealthScoreCardProps) {
  const [display, setDisplay] = useState(0);
  const cfg = getScoreConfig(score);
  const sparkData = history.map((h) => h.score);
  const delta = history.length >= 2
    ? history[history.length - 1].score - history[0].score
    : null;

  useEffect(() => {
    if (score === null) return;
    let raf: number;
    const start = performance.now();
    const dur = 1400;
    const step = (now: number) => {
      const p = Math.min((now - start) / dur, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(Math.round(eased * score));
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [score]);

  const R = 18;
  const circumference = 2 * Math.PI * R;

  return (
    <div className="flex flex-col gap-2 h-full">
      <div className="flex items-start justify-between">
        <div>
          <p className="metric-label">Health Score</p>
          <div className="flex items-end gap-1.5 mt-1.5">
            <span className={cn("font-mono text-[30px] font-bold leading-none tracking-tight", cfg.tw)}>
              {score !== null ? display : "—"}
            </span>
            {score !== null && (
              <span className="text-[13px] mb-0.5 font-mono" style={{ color: "#636366" }}>
                /100
              </span>
            )}
          </div>
          <span className={cn("text-[11px] font-semibold mt-1 block tracking-wide", cfg.tw)}>
            {cfg.label}
          </span>
          {bodyAge !== undefined && (
            <span className="text-[10px] font-mono mt-0.5 block" style={{ color: "#636366" }}>
              body age {bodyAge}y
            </span>
          )}
        </div>

        {/* Animated ring — Apple Activity ring style */}
        <div className="relative w-14 h-14 shrink-0">
          <svg viewBox="0 0 44 44" className="w-full h-full -rotate-90">
            {/* Track */}
            <circle cx="22" cy="22" r={R} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="4.5" />
            {/* Fill */}
            {score !== null && (
              <motion.circle
                cx="22" cy="22" r={R}
                fill="none"
                stroke={cfg.hex}
                strokeWidth="4.5"
                strokeLinecap="round"
                strokeDasharray={circumference}
                initial={{ strokeDashoffset: circumference }}
                animate={{ strokeDashoffset: circumference * (1 - score / 100) }}
                transition={{ duration: 1.4, ease: [0.4, 0, 0.2, 1] }}
                style={{ filter: `drop-shadow(0 0 4px ${cfg.hex}80)` }}
              />
            )}
          </svg>
          <Heart className="w-4 h-4 absolute inset-0 m-auto" style={{ color: "#FF2D55" }} />
        </div>
      </div>

      {/* Sparkline + delta */}
      <div
        className="flex items-end justify-between mt-auto pt-2.5"
        style={{ borderTop: "1px solid rgba(84,84,88,0.35)" }}
      >
        {sparkData.length >= 2 ? (
          <Sparkline data={sparkData} color={cfg.hex} />
        ) : (
          <span className="text-[10px] font-mono" style={{ color: "#8E8E93" }}>
            no history
          </span>
        )}
        {delta !== null && (
          <div
            className={cn(
              "flex items-center gap-0.5 text-[11px] font-mono font-semibold",
              delta > 0 ? "text-[#32D74B]" : delta < 0 ? "text-[#FF453A]" : "text-[#636366]"
            )}
          >
            {delta > 0 ? <TrendingUp className="w-3 h-3" /> : delta < 0 ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
            {delta > 0 ? "+" : ""}{delta}
          </div>
        )}
      </div>
    </div>
  );
}
