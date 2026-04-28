"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Utensils, Dumbbell, Lightbulb, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";
import DynamicAdjustmentBanner from "@/components/lifestyle-planner/DynamicAdjustmentBanner";
import LifestylePlannerForm from "@/components/lifestyle-planner/LifestylePlannerForm";
import { PageHero } from "@/components/ui/PageHero";
import { useLifestyleStore, LifestylePlanRequest } from "@/lib/lifestyleStore";
import { lifestyleApi } from "@/lib/lifestyleApi";
import { getLocalUserId } from "@/lib/utils";
import { PAGE_IMAGES } from "@/lib/pageImages";
import { useNotificationStore } from "@/lib/notificationStore";

const NAV_CARDS = [
  { label: "Diet Plan", desc: "Daily meals & nutrition", href: "/lifestyle-planner/diet", icon: Utensils, color: "#FFB800", img: PAGE_IMAGES.navCards.diet },
  { label: "Exercise", desc: "Workouts & movement", href: "/lifestyle-planner/exercise", icon: Dumbbell, color: "#00FF88", img: PAGE_IMAGES.navCards.exercise },
  { label: "Recommendations", desc: "Preventive care & tips", href: "/lifestyle-planner/recommendations", icon: Lightbulb, color: "#A78BFA", img: PAGE_IMAGES.navCards.recommendations },
];

export default function LifestylePlannerHub() {
  const router = useRouter();
  const { latestPlan, isGenerating, setLatestPlan, setGenerating, reportPreload, setReportPreload } = useLifestyleStore();
  const addNotification = useNotificationStore((s) => s.addNotification);
  const userId = getLocalUserId() ?? "anonymous";

  useEffect(() => {
    lifestyleApi.getLatestPlan(userId).then((r) => setLatestPlan(r.data)).catch(() => {});
  }, [userId]);

  const handleGenerate = async (req: LifestylePlanRequest) => {
    setGenerating(true);
    try {
      const res = await lifestyleApi.generatePlan(req);
      setLatestPlan(res.data);
      addNotification(
        "plan_generated",
        "Lifestyle Plan Generated",
        `Your personalised ${(res.data.goal ?? "").replace("_", " ")} plan with diet and exercise is ready.`
      );
    } catch {
      addNotification(
        "plan_error",
        "Generation Failed",
        "Could not generate your lifestyle plan. Please try again."
      );
    } finally { setGenerating(false); }
  };

  // Auto-generate when arriving from the diagnostic report page
  useEffect(() => {
    if (!reportPreload) return;
    const req = { ...reportPreload };
    setReportPreload(null); // consume immediately so re-renders don't re-fire
    void handleGenerate(req);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-8">
      <PageHero src={PAGE_IMAGES.lifestyle} opacity={40} objectPosition="center 30%" accentColor="rgba(0,255,136,0.22)">
        <div className="p-5">
          <h1 className="text-2xl font-bold text-white">Lifestyle Planner</h1>
          <p className="text-sm text-gray-400 mt-1">Personalised diet, exercise, and preventive care — built around your health.</p>
        </div>
      </PageHero>

      {latestPlan?.auto_adjusted && <DynamicAdjustmentBanner />}

      {latestPlan && (
        <div className="rounded-2xl p-5"
          style={{ background: "rgba(13,22,39,0.85)", border: "1px solid rgba(0,212,255,0.15)" }}>
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-xs text-gray-400">Current Plan · {latestPlan.plan_date}</p>
              <h2 className="text-lg font-bold text-white capitalize mt-0.5">
                {(latestPlan.goal ?? "").replace("_", " ")} — {latestPlan.activity_level} activity
              </h2>
            </div>
            <button onClick={() => handleGenerate({
              user_id: userId,
              goal: latestPlan.goal as LifestylePlanRequest["goal"],
              dietary_pref: latestPlan.dietary_pref,
              restrictions: [],
              activity_level: latestPlan.activity_level as LifestylePlanRequest["activity_level"],
            })} disabled={isGenerating}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium"
              style={{ background: "rgba(0,212,255,0.12)", color: "#00D4FF" }}>
              <RefreshCw size={12} className={isGenerating ? "animate-spin" : ""} /> Refresh Plan
            </button>
          </div>

          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="rounded-xl py-3" style={{ background: "rgba(255,184,0,0.08)" }}>
              <p className="text-lg font-bold text-amber-400">{latestPlan.daily_nutrition?.calories ?? "—"}</p>
              <p className="text-xs text-gray-500">kcal / day</p>
            </div>
            <div className="rounded-xl py-3" style={{ background: "rgba(0,255,136,0.08)" }}>
              <p className="text-lg font-bold text-green-400">{(latestPlan.exercises ?? []).reduce((s, e) => s + e.duration_min, 0)}</p>
              <p className="text-xs text-gray-500">min exercise</p>
            </div>
            <div className="rounded-xl py-3" style={{ background: "rgba(0,212,255,0.08)" }}>
              <p className="text-lg font-bold text-cyan-400">{(latestPlan.avoid_list ?? []).length}</p>
              <p className="text-xs text-gray-500">things to avoid</p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {NAV_CARDS.map((card, i) => (
          <motion.button key={card.href} onClick={() => router.push(card.href)}
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            className="relative rounded-2xl p-5 text-left hover:scale-105 transition-transform overflow-hidden group"
            style={{ background: "rgba(13,22,39,0.85)", border: `1px solid ${card.color}33` }}>
            {/* Card background image */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={card.img} alt="" loading="lazy" decoding="async" aria-hidden
              className="absolute right-0 top-0 bottom-0 w-28 h-full object-cover pointer-events-none select-none transition-transform duration-500 group-hover:scale-110"
              style={{ opacity: 0.42 }} />
            <div className="absolute right-0 top-0 bottom-0 w-28 pointer-events-none"
              style={{ background: "linear-gradient(to right, rgba(13,22,39,1) 0%, rgba(13,22,39,0.4) 70%, rgba(13,22,39,0.1) 100%)" }} />
            <card.icon size={22} style={{ color: card.color }} className="relative mb-3" />
            <p className="relative text-sm font-semibold text-white">{card.label}</p>
            <p className="relative text-xs text-gray-400 mt-1">{card.desc}</p>
          </motion.button>
        ))}
      </div>

      {!latestPlan && (
        <LifestylePlannerForm userId={userId} onGenerate={handleGenerate} loading={isGenerating} />
      )}
    </div>
  );
}
