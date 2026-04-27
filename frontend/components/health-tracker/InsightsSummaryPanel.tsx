"use client";
import { Lightbulb } from "lucide-react";
import InsightAlertCard from "./InsightAlertCard";
import WeeklyScoreRing from "./WeeklyScoreRing";
import { InsightsResponse } from "@/lib/healthTrackerStore";

const TREND_BADGE: Record<string, { label: string; color: string }> = {
  improving: { label: "Improving", color: "#00FF88" },
  stable:    { label: "Stable",    color: "#00D4FF" },
  worsening: { label: "Worsening", color: "#FF3B3B" },
};

interface Props {
  insights: InsightsResponse;
  compact?: boolean;
}

export default function InsightsSummaryPanel({ insights, compact }: Props) {
  const badge = TREND_BADGE[insights.trend] ?? TREND_BADGE.stable;
  const topAlerts = compact ? insights.alerts.slice(0, 2) : insights.alerts;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 flex-wrap">
        <WeeklyScoreRing score={Math.round(insights.weekly_score)} size="md" trend={insights.trend} label="Weekly Score" />
        <div className="flex flex-col gap-2">
          <span
            className="px-3 py-1 rounded-full text-xs font-semibold"
            style={{ background: `${badge.color}22`, color: badge.color, border: `1px solid ${badge.color}55` }}
          >
            {badge.label}
          </span>
          {insights.correlation_notes.slice(0, 2).map((note, i) => (
            <p key={i} className="text-xs text-gray-400">{note}</p>
          ))}
        </div>
      </div>

      {topAlerts.length > 0 && (
        <div className="space-y-2">
          {topAlerts.map((a, i) => <InsightAlertCard key={i} alert={a} />)}
        </div>
      )}

      {!compact && insights.suggestions.length > 0 && (
        <div className="rounded-xl p-4" style={{ background: "rgba(0,212,255,0.06)", border: "1px solid rgba(0,212,255,0.15)" }}>
          <div className="flex items-center gap-2 mb-2">
            <Lightbulb size={14} className="text-cyan-400" />
            <span className="text-xs font-semibold text-cyan-400">Suggestions</span>
          </div>
          <ul className="space-y-1">
            {insights.suggestions.map((s, i) => (
              <li key={i} className="text-xs text-gray-300 flex gap-2"><span className="text-cyan-500">•</span>{s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
