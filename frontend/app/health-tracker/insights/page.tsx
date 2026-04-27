"use client";
import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import InsightsSummaryPanel from "@/components/health-tracker/InsightsSummaryPanel";
import CorrelationCard from "@/components/health-tracker/CorrelationCard";
import PredictionMiniChart from "@/components/health-tracker/PredictionMiniChart";
import { PageHero } from "@/components/ui/PageHero";
import { useHealthTrackerStore } from "@/lib/healthTrackerStore";
import { healthTrackerApi } from "@/lib/healthTrackerApi";
import { getLocalUserId } from "@/lib/utils";
import { PAGE_IMAGES } from "@/lib/pageImages";
import { useNotificationStore } from "@/lib/notificationStore";

export default function InsightsPage() {
  const { insights, trendData, setInsights, setTrendData } = useHealthTrackerStore();
  const [loading, setLoading] = useState(false);
  const userId = getLocalUserId();
  const addNotification = useNotificationStore((s) => s.addNotification);

  const load = async () => {
    setLoading(true);
    try {
      const [insRes, trendRes] = await Promise.all([
        healthTrackerApi.getInsights(userId, 14),
        healthTrackerApi.getTrends(userId),
      ]);
      setInsights(insRes.data);
      setTrendData(trendRes.data);
      if (insRes.data) {
        addNotification(
          "insights_ready",
          "AI Insights Ready",
          `Pattern analysis complete — ${insRes.data.suggestions?.length ?? 0} recommendation(s) generated.`
        );
      }
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [userId]);

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <PageHero src={PAGE_IMAGES.insights} opacity={42} objectPosition="center 30%" accentColor="rgba(167,139,250,0.25)">
        <div className="p-5 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">AI Health Insights</h1>
            <p className="text-sm text-gray-400 mt-1">Pattern detection, anomaly alerts, and 3-day prediction.</p>
          </div>
          <button onClick={load} disabled={loading}
            className="btn-secondary flex items-center gap-2 px-4 py-2 text-sm shrink-0">
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} /> Refresh
          </button>
        </div>
      </PageHero>

      {!insights && !loading && (
        <div className="text-center py-16 text-gray-500 text-sm">
          No insights yet. Log at least 3 days of symptoms to see patterns.
        </div>
      )}

      {insights && (
        <div className="space-y-6">
          <div className="rounded-2xl p-6"
            style={{ background: "rgba(13,22,39,0.85)", border: "1px solid rgba(0,212,255,0.15)" }}>
            <InsightsSummaryPanel insights={insights} />
          </div>

          {insights.correlation_notes.length > 0 && (
            <CorrelationCard notes={insights.correlation_notes} />
          )}

          {trendData.length >= 3 && (
            <PredictionMiniChart
              historical={trendData}
              prediction={insights.prediction_next_3_days}
            />
          )}

          {/* Suggestions detail */}
          {insights.suggestions.length > 0 && (
            <div className="rounded-2xl p-5"
              style={{ background: "rgba(13,22,39,0.8)", border: "1px solid rgba(0,212,255,0.12)" }}>
              <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-3">Recommendations</h3>
              <ul className="space-y-2">
                {insights.suggestions.map((s, i) => (
                  <li key={i} className="flex gap-3 text-sm text-gray-300">
                    <span className="text-cyan-500 mt-0.5">→</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
