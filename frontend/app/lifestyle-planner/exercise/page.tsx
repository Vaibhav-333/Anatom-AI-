"use client";
import { useEffect } from "react";
import ExercisePlanCard from "@/components/lifestyle-planner/ExercisePlanCard";
import { PageHero } from "@/components/ui/PageHero";
import { useLifestyleStore } from "@/lib/lifestyleStore";
import { lifestyleApi } from "@/lib/lifestyleApi";
import { getLocalUserId } from "@/lib/utils";
import { PAGE_IMAGES } from "@/lib/pageImages";

export default function ExercisePage() {
  const { latestPlan, setLatestPlan } = useLifestyleStore();
  const userId = getLocalUserId();

  useEffect(() => {
    if (!latestPlan) {
      lifestyleApi.getLatestPlan(userId).then((r) => setLatestPlan(r.data)).catch(() => {});
    }
  }, [userId]);

  if (!latestPlan) {
    return (
      <div className="p-6 max-w-3xl mx-auto text-center py-16 text-gray-500 text-sm">
        No plan generated yet. Visit the <a href="/lifestyle-planner" className="text-cyan-400 underline">Lifestyle Hub</a> to generate your first plan.
      </div>
    );
  }

  const totalMin = (latestPlan.exercises ?? []).reduce((s, e) => s + e.duration_min, 0);

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <PageHero src={PAGE_IMAGES.exercise} opacity={40} objectPosition="center 40%" accentColor="rgba(0,255,136,0.22)">
        <div className="p-5">
          <h1 className="text-2xl font-bold text-white">Exercise Plan</h1>
          <p className="text-sm text-gray-400 mt-1">
            {latestPlan.activity_level} intensity · {totalMin} min · {latestPlan.plan_date}
          </p>
        </div>
      </PageHero>

      {latestPlan.activity_level === "sedentary" && (
        <div className="rounded-xl p-4 text-sm text-gray-300"
          style={{ background: "rgba(0,212,255,0.08)", border: "1px solid rgba(0,212,255,0.2)" }}>
          🛌 Rest day recommended. Focus on recovery and gentle breathing exercises.
        </div>
      )}

      {/* Workout overview banner */}
      <div className="relative rounded-2xl overflow-hidden h-36">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={PAGE_IMAGES.exercise} alt="" loading="lazy" decoding="async" aria-hidden
          className="absolute inset-0 w-full h-full object-cover pointer-events-none select-none"
          style={{ opacity: 0.48, objectPosition: "center 35%" }} />
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: "linear-gradient(to right, rgba(10,15,30,0.90) 0%, rgba(10,15,30,0.44) 55%, rgba(10,15,30,0.12) 100%)" }} />
        <div className="absolute bottom-0 left-0 right-0 h-px pointer-events-none"
          style={{ background: "linear-gradient(90deg, transparent, rgba(0,255,136,0.55), transparent)" }} />
        <div className="relative h-full flex items-center px-6 gap-8">
          <div>
            <p className="text-[11px] text-green-400 font-semibold uppercase tracking-widest mb-1">Your Workout Plan</p>
            <h3 className="text-white font-bold text-lg leading-tight">
              {latestPlan.activity_level.charAt(0).toUpperCase() + latestPlan.activity_level.slice(1)} Intensity Training
            </h3>
            <p className="text-slate-400 text-sm mt-1.5">Tailored exercises matched to your fitness level and health conditions.</p>
          </div>
          <div className="ml-auto shrink-0 text-right">
            <p className="text-2xl font-bold text-green-400">{totalMin}</p>
            <p className="text-xs text-slate-500">min / session</p>
            <p className="text-lg font-semibold text-cyan-400 mt-1">{(latestPlan.exercises ?? []).length}</p>
            <p className="text-xs text-slate-500">exercises</p>
          </div>
        </div>
      </div>

      <ExercisePlanCard exercises={latestPlan.exercises} activityLevel={latestPlan.activity_level} />

      {(latestPlan.avoid_list ?? []).length > 0 && (
        <div className="rounded-2xl p-5" style={{ background: "rgba(255,59,59,0.06)", border: "1px solid rgba(255,59,59,0.2)" }}>
          <p className="text-sm font-semibold text-red-400 mb-2">Activities to avoid</p>
          <div className="flex flex-wrap gap-2">
            {(latestPlan.avoid_list ?? []).filter((item) =>
              ["strenuous","heavy lifting","running","swimming","gym"].some((kw) => item.toLowerCase().includes(kw))
            ).map((item, i) => (
              <span key={i} className="px-3 py-1 rounded-full text-xs"
                style={{ background: "rgba(255,59,59,0.15)", color: "#FF3B3B" }}>
                {item}
              </span>
            ))}
            {(latestPlan.avoid_list ?? []).filter((item) =>
              !["strenuous","heavy lifting","running","swimming","gym"].some((kw) => item.toLowerCase().includes(kw))
            ).length === (latestPlan.avoid_list ?? []).length && (
              <p className="text-xs text-gray-500">No specific activity restrictions.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
