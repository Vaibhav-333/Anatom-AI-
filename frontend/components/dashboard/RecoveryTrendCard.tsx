"use client";

import { TrendingUp, TrendingDown, Minus, Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ScoreHistoryPoint } from "@/lib/types";

function Sparkline({ data, color }: { data: number[]; color: string }) {
  if (data.length < 2) return null;
  const W = 80; const H = 30;
  const min = Math.min(...data); const max = Math.max(...data);
  const range = max - min || 1;
  const pts = data
    .map((v, i) => `${(i / (data.length - 1)) * W},${H - ((v - min) / range) * (H - 2) + 1}`)
    .join(" ");
  const gradId = `rt-${color.replace("#", "")}`;
  return (
    <svg width={W} height={H} className="overflow-visible">
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon fill={`url(#${gradId})`} points={`0,${H} ${pts} ${W},${H}`} />
      <polyline fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" points={pts} />
      {(() => {
        const last = data[data.length - 1];
        const x = W; const y = H - ((last - min) / range) * (H - 2) + 1;
        return <circle cx={x} cy={y} r="2.5" fill={color} />;
      })()}
    </svg>
  );
}

interface RecoveryTrendCardProps { history: ScoreHistoryPoint[]; }

export function RecoveryTrendCard({ history }: RecoveryTrendCardProps) {
  const sparkData = history.map((h) => h.score);
  const hasData = sparkData.length >= 2;
  const delta = hasData ? sparkData[sparkData.length - 1] - sparkData[0] : null;
  const pctStr =
    hasData && sparkData[0] > 0 && delta !== null
      ? ((delta / sparkData[0]) * 100).toFixed(1)
      : null;

  const trending = delta === null ? "none" : delta > 0 ? "up" : delta < 0 ? "down" : "none";
  const colorHex = trending === "up" ? "#32D74B" : trending === "down" ? "#FF453A" : "#636366";
  const textTw   = trending === "up" ? "text-[#32D74B]" : trending === "down" ? "text-[#FF453A]" : "text-[#636366]";
  const statusLabel = trending === "up" ? "Improving" : trending === "down" ? "Declining" : hasData ? "Stable" : "No history";

  return (
    <div className="flex flex-col gap-2 h-full">
      <div className="flex items-start justify-between">
        <div>
          <p className="metric-label">Recovery Trend</p>
          <div className="flex items-center gap-1.5 mt-1.5">
            {trending === "up"   ? <TrendingUp   className="w-5 h-5 text-[#32D74B]" /> :
             trending === "down" ? <TrendingDown  className="w-5 h-5 text-[#FF453A]" /> :
                                   <Minus         className="w-5 h-5 text-[#636366]" />}
            <span className={cn("font-mono text-[24px] font-bold leading-none tracking-tight", textTw)}>
              {pctStr !== null ? `${delta! > 0 ? "+" : ""}${pctStr}%` : "—"}
            </span>
          </div>
          <span className={cn("text-[11px] font-semibold mt-1 block tracking-wide", textTw)}>
            {statusLabel}
          </span>
        </div>

        <div
          className="p-2 rounded-xl shrink-0"
          style={{
            background: "rgba(255,255,255,0.06)",
          }}
        >
          <Activity className="w-5 h-5" style={{ color: "#8E8E93" }} />
        </div>
      </div>

      <div className="mt-auto pt-2.5" style={{ borderTop: "1px solid rgba(84,84,88,0.35)" }}>
        {hasData ? (
          <div className="flex items-end justify-between">
            <Sparkline data={sparkData} color={colorHex} />
            <span className="text-[10px] font-mono" style={{ color: "#636366" }}>
              {history.length}d span
            </span>
          </div>
        ) : (
          <p className="text-[10px] font-mono" style={{ color: "#636366" }}>
            upload a report to track trends
          </p>
        )}
      </div>
    </div>
  );
}
