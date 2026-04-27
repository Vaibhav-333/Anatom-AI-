"use client";

import { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
import { FileText, CheckCircle, Flame, TrendingUp, ArrowUp, ArrowDown, Minus } from "lucide-react";
import { LineChart, Line, ResponsiveContainer, Tooltip } from "recharts";
import type { ScoreHistoryPoint } from "@/lib/types";

// ── Ring color by score ────────────────────────────────────────────────────
function ringColor(score: number): string {
  if (score >= 80) return "#00D4FF";   // cyan
  if (score >= 60) return "#22c55e";   // green
  if (score >= 40) return "#f59e0b";   // amber
  return "#ef4444";                    // red
}

// ── Achievement badge data ─────────────────────────────────────────────────
const BADGES = [
  {
    id: "all-clear",
    icon: CheckCircle,
    label: "All Clear",
    check: (score: number) => score >= 80,
  },
  {
    id: "uploaded",
    icon: FileText,
    label: "First Report",
    check: (_score: number) => true, // always earned once on this page
  },
  {
    id: "streak",
    icon: Flame,
    label: "On Track",
    check: (score: number) => score >= 60,
  },
  {
    id: "improving",
    icon: TrendingUp,
    label: "Improving",
    check: (score: number) => score >= 50,
  },
];

// ── Props ──────────────────────────────────────────────────────────────────
interface HealthScoreRingProps {
  score: number;
  bodyAge?: number;
  history?: ScoreHistoryPoint[];
  animate?: boolean;
}

// ── SVG Ring ──────────────────────────────────────────────────────────────
function ScoreRing({
  score,
  color,
  animate,
}: {
  score: number;
  color: string;
  animate: boolean;
}) {
  const r = 52;
  const circ = 2 * Math.PI * r;
  const filled = (score / 100) * circ;
  const dash = circ - filled;

  return (
    <svg width="140" height="140" viewBox="0 0 140 140" className="block">
      {/* Track */}
      <circle cx="70" cy="70" r={r} fill="none" stroke="#1e293b" strokeWidth="10" />
      {/* Progress */}
      <motion.circle
        cx="70"
        cy="70"
        r={r}
        fill="none"
        stroke={color}
        strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={`${circ}`}
        initial={{ strokeDashoffset: circ }}
        animate={{ strokeDashoffset: animate ? dash : dash }}
        transition={{ duration: 1.2, ease: "easeOut", delay: 0.2 }}
        transform="rotate(-90 70 70)"
        style={{ filter: `drop-shadow(0 0 6px ${color}88)` }}
      />
    </svg>
  );
}

// ── Sparkline tooltip ──────────────────────────────────────────────────────
function SparkTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-navy-800 border border-glass-border rounded px-2 py-1 text-xs text-slate-300">
      {payload[0].value}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────
export function HealthScoreRing({
  score,
  bodyAge,
  history = [],
  animate = true,
}: HealthScoreRingProps) {
  const color = ringColor(score);

  // Load earned badges from localStorage
  const [earnedBadges, setEarnedBadges] = useState<Set<string>>(new Set());
  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem("anatom-badges") ?? "[]");
      const earned = new Set<string>(stored);
      // Check new badges
      BADGES.forEach((b) => {
        if (b.check(score)) earned.add(b.id);
      });
      localStorage.setItem("anatom-badges", JSON.stringify(Array.from(earned)));
      setEarnedBadges(earned);
    } catch {
      setEarnedBadges(new Set());
    }
  }, [score]);

  // Trend: compare last 2 history points
  const trend: "up" | "down" | "flat" =
    history.length >= 2
      ? history[history.length - 1].score > history[history.length - 2].score
        ? "up"
        : history[history.length - 1].score < history[history.length - 2].score
        ? "down"
        : "flat"
      : "flat";

  const TrendIcon =
    trend === "up" ? ArrowUp : trend === "down" ? ArrowDown : Minus;
  const trendColor =
    trend === "up" ? "text-green-400" : trend === "down" ? "text-red-400" : "text-slate-500";

  return (
    <div className="flex flex-col items-center gap-3">
      {/* Ring + center text */}
      <div className="relative w-[140px] h-[140px]">
        <ScoreRing score={score} color={color} animate={animate} />
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.span
            className="text-3xl font-bold font-mono"
            style={{ color }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
          >
            {Math.round(score)}
          </motion.span>
          <span className="text-xs text-slate-500">/ 100</span>
          {bodyAge !== undefined && (
            <span className="text-xs text-slate-600 mt-0.5">
              Body age <span className="text-slate-400">{bodyAge}</span>
            </span>
          )}
        </div>
      </div>

      {/* Trend indicator */}
      <div className={`flex items-center gap-1 text-xs ${trendColor}`}>
        <TrendIcon className="w-3 h-3" />
        <span>{trend === "flat" ? "Stable" : trend === "up" ? "Improving" : "Declining"}</span>
      </div>

      {/* Achievement badges */}
      <div className="flex gap-2">
        {BADGES.map((b) => {
          const earned = earnedBadges.has(b.id);
          const Icon = b.icon;
          return (
            <div
              key={b.id}
              title={b.label}
              className={`flex flex-col items-center gap-0.5 transition-opacity ${
                earned ? "opacity-100" : "opacity-20"
              }`}
            >
              <Icon className="w-4 h-4 text-cyan" />
              <span className="text-[9px] text-slate-600">{b.label}</span>
            </div>
          );
        })}
      </div>

      {/* Sparkline */}
      {history.length > 2 && (
        <div className="w-full h-10">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history}>
              <Line
                type="monotone"
                dataKey="score"
                stroke={color}
                strokeWidth={1.5}
                dot={false}
              />
              <Tooltip content={<SparkTooltip />} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
