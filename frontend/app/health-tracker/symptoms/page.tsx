"use client";
import { useEffect, useState } from "react";
import SymptomLogForm from "@/components/health-tracker/SymptomLogForm";
import SymptomTimeline from "@/components/health-tracker/SymptomTimeline";
import SymptomCalendarHeatmap from "@/components/health-tracker/SymptomCalendarHeatmap";
import SymptomTrendChart from "@/components/health-tracker/SymptomTrendChart";
import { PageHero } from "@/components/ui/PageHero";
import { useHealthTrackerStore } from "@/lib/healthTrackerStore";
import { healthTrackerApi } from "@/lib/healthTrackerApi";
import { getLocalUserId } from "@/lib/utils";
import { PAGE_IMAGES } from "@/lib/pageImages";
import { useNotificationStore } from "@/lib/notificationStore";

type Metric = "avg_pain" | "avg_mood" | "avg_sleep" | "avg_fever";

export default function SymptomsPage() {
  const {
    symptomLogs, trendData, heatmapData,
    heatmapYear, heatmapMonth,
    addSymptomLog, removeSymptomLog, setSymptomLogs,
    setTrendData, setHeatmapData, setHeatmapMonth,
    trendPeriod, setTrendPeriod,
  } = useHealthTrackerStore();

  const [logLoading, setLogLoading] = useState(false);
  const [activeMetrics, setActiveMetrics] = useState<Metric[]>(["avg_pain", "avg_sleep"]);
  const userId = getLocalUserId();
  const addNotification = useNotificationStore((s) => s.addNotification);

  const loadAll = async () => {
    try {
      const [logsRes, trendRes, heatRes] = await Promise.all([
        healthTrackerApi.getSymptoms(userId, { limit: 50 }),
        healthTrackerApi.getTrends(userId, { period: trendPeriod }),
        healthTrackerApi.getHeatmap(userId, heatmapYear, heatmapMonth),
      ]);
      setSymptomLogs(Array.isArray(logsRes.data) ? logsRes.data : []);
      setTrendData(Array.isArray(trendRes.data) ? trendRes.data : []);
      setHeatmapData(Array.isArray(heatRes.data) ? heatRes.data : []);
    } catch { /* API not available */ }
  };

  useEffect(() => { loadAll(); }, [trendPeriod, heatmapYear, heatmapMonth]);

  const handleLog = async (payload: object) => {
    setLogLoading(true);
    try {
      const res = await healthTrackerApi.logSymptom(payload);
      addSymptomLog(res.data);
      addNotification(
        "symptom_logged",
        "Symptom Log Saved",
        "Your daily symptom entry has been recorded and trends updated."
      );
      // Refresh trends
      const [trendRes, heatRes] = await Promise.all([
        healthTrackerApi.getTrends(userId, { period: trendPeriod }),
        healthTrackerApi.getHeatmap(userId, heatmapYear, heatmapMonth),
      ]);
      setTrendData(trendRes.data);
      setHeatmapData(heatRes.data);
    } finally { setLogLoading(false); }
  };

  const handleDelete = async (id: string) => {
    await healthTrackerApi.deleteSymptomLog(id);
    removeSymptomLog(id);
  };

  const toggleMetric = (m: Metric) =>
    setActiveMetrics((prev) => prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m]);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-8">
      <PageHero src={PAGE_IMAGES.symptoms} opacity={38} objectPosition="center 40%">
        <div className="p-5">
          <h1 className="text-2xl font-bold text-white">Symptom Log</h1>
          <p className="text-sm text-gray-400 mt-1">Log and track your daily symptoms over time.</p>
        </div>
      </PageHero>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SymptomLogForm userId={userId} onSubmit={handleLog} loading={logLoading} />

        <div className="rounded-2xl p-5 space-y-4"
          style={{ background: "rgba(13,22,39,0.8)", border: "1px solid rgba(0,212,255,0.12)" }}>
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider">Trends</h3>
            <div className="flex gap-1">
              {(["weekly","monthly"] as const).map((p) => (
                <button key={p} onClick={() => setTrendPeriod(p)}
                  className="px-2 py-0.5 rounded-lg text-xs transition-all capitalize"
                  style={{
                    background: trendPeriod === p ? "rgba(0,212,255,0.2)" : "rgba(255,255,255,0.04)",
                    color: trendPeriod === p ? "#00D4FF" : "#8899AA",
                  }}>
                  {p}
                </button>
              ))}
            </div>
          </div>
          <SymptomTrendChart data={trendData} metrics={activeMetrics} onMetricToggle={toggleMetric} />
        </div>
      </div>

      <SymptomCalendarHeatmap
        data={heatmapData} year={heatmapYear} month={heatmapMonth}
        onMonthChange={(y, m) => setHeatmapMonth(y, m)}
      />

      <div className="rounded-2xl p-5"
        style={{ background: "rgba(13,22,39,0.8)", border: "1px solid rgba(0,212,255,0.12)" }}>
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Timeline</h3>
        <SymptomTimeline logs={symptomLogs} onDelete={handleDelete} />
      </div>
    </div>
  );
}
