"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Activity, Pill, Brain, Download, Flame } from "lucide-react";
import { motion } from "framer-motion";
import WeeklyScoreRing from "@/components/health-tracker/WeeklyScoreRing";
import BadgeGrid from "@/components/health-tracker/BadgeGrid";
import InsightsSummaryPanel from "@/components/health-tracker/InsightsSummaryPanel";
import { PageHero } from "@/components/ui/PageHero";
import { useHealthTrackerStore } from "@/lib/healthTrackerStore";
import { healthTrackerApi } from "@/lib/healthTrackerApi";
import { getLocalUserId } from "@/lib/utils";
import { PAGE_IMAGES } from "@/lib/pageImages";

const NAV_CARDS = [
  { label: "Symptoms", desc: "Log & track your daily symptoms", href: "/health-tracker/symptoms", icon: Activity, color: "#00D4FF", img: PAGE_IMAGES.navCards.symptoms },
  { label: "Medications", desc: "Track doses & adherence", href: "/health-tracker/medications", icon: Pill, color: "#00FF88", img: PAGE_IMAGES.navCards.medications },
  { label: "AI Insights", desc: "Patterns, alerts & predictions", href: "/health-tracker/insights", icon: Brain, color: "#A78BFA", img: PAGE_IMAGES.navCards.insights },
  { label: "Export", desc: "Download & share PDF report", href: "/health-tracker/export", icon: Download, color: "#FFB800", img: PAGE_IMAGES.navCards.export },
];

export default function HealthTrackerHub() {
  const router = useRouter();
  const { insights, weeklyScores, setInsights, setWeeklyScores } = useHealthTrackerStore();
  const [loading, setLoading] = useState(true);
  const userId = getLocalUserId();

  useEffect(() => {
    (async () => {
      try {
        const [insRes, scoreRes] = await Promise.all([
          healthTrackerApi.getInsights(userId, 14),
          healthTrackerApi.getScores(userId, 4),
        ]);
        if (insRes.data && typeof insRes.data === "object") setInsights(insRes.data);
        setWeeklyScores(Array.isArray(scoreRes.data) ? scoreRes.data : []);
      } catch { /* no data yet */ }
      finally { setLoading(false); }
    })();
  }, [userId]);

  const latest = weeklyScores[0];

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-8">
      <PageHero src={PAGE_IMAGES.healthTracker} opacity={38} objectPosition="center 35%">
        <div className="p-5">
          <h1 className="text-2xl font-bold text-white">Symptom Tracker</h1>
          <p className="text-sm text-gray-400 mt-1">Monitor what's happening to your body — daily logs, trends, and AI alerts.</p>
        </div>
      </PageHero>

      {/* Top row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Score */}
        <div className="rounded-2xl p-6 flex items-center gap-5 relative overflow-hidden"
          style={{ background: "rgba(13,22,39,0.85)", border: "1px solid rgba(0,212,255,0.15)" }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={PAGE_IMAGES.healthTracker} alt="" loading="lazy" decoding="async" aria-hidden
            className="absolute inset-0 w-full h-full object-cover pointer-events-none select-none"
            style={{ opacity: 0.22, objectPosition: "center 40%" }} />
          <div className="absolute inset-0 pointer-events-none"
            style={{ background: "rgba(13,22,39,0.52)" }} />
          <div className="relative">
            <WeeklyScoreRing
              score={latest ? Math.round(latest.score) : 0}
              size="lg"
              trend={latest?.trend}
              label="Weekly Score"
            />
          </div>
          <div className="relative">
            <p className="text-xs text-gray-400">This Week</p>
            {latest && (
              <div className="mt-2 space-y-1">
                {latest.streak_days > 0 && (
                  <div className="flex items-center gap-1 text-xs text-amber-400">
                    <Flame size={12} />
                    <span>{latest.streak_days}-day streak</span>
                  </div>
                )}
                <BadgeGrid badges={latest.badges} />
              </div>
            )}
          </div>
        </div>

        {/* Compact insights */}
        <div className="md:col-span-2 rounded-2xl p-5 relative overflow-hidden"
          style={{ background: "rgba(13,22,39,0.85)", border: "1px solid rgba(0,212,255,0.15)" }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={PAGE_IMAGES.insights} alt="" loading="lazy" decoding="async" aria-hidden
            className="absolute inset-0 w-full h-full object-cover pointer-events-none select-none"
            style={{ opacity: 0.24, objectPosition: "center 25%" }} />
          <div className="absolute inset-0 pointer-events-none"
            style={{ background: "rgba(13,22,39,0.52)" }} />
          <div className="relative">
            {insights && !loading
              ? <InsightsSummaryPanel insights={insights} compact />
              : <p className="text-sm text-gray-500">
                  {loading ? "Loading insights…" : "Log symptoms to see AI insights."}
                </p>
            }
          </div>
        </div>
      </div>

      {/* Nav cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {NAV_CARDS.map((card, i) => (
          <motion.button
            key={card.href}
            onClick={() => router.push(card.href)}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 }}
            className="relative rounded-2xl p-5 text-left hover:scale-105 transition-transform overflow-hidden group"
            style={{ background: "rgba(13,22,39,0.85)", border: `1px solid ${card.color}33` }}>
            {/* Card background image */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={card.img} alt="" loading="lazy" decoding="async" aria-hidden
              className="absolute right-0 top-0 bottom-0 w-24 h-full object-cover pointer-events-none select-none transition-transform duration-500 group-hover:scale-110"
              style={{ opacity: 0.42 }} />
            <div className="absolute right-0 top-0 bottom-0 w-24 pointer-events-none"
              style={{ background: "linear-gradient(to right, rgba(13,22,39,1) 0%, rgba(13,22,39,0.4) 70%, rgba(13,22,39,0.05) 100%)" }} />
            <card.icon size={22} style={{ color: card.color }} className="relative mb-3" />
            <p className="relative text-sm font-semibold text-white">{card.label}</p>
            <p className="relative text-xs text-gray-400 mt-1">{card.desc}</p>
          </motion.button>
        ))}
      </div>
    </div>
  );
}
