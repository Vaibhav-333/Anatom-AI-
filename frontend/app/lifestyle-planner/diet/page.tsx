"use client";
import { useEffect } from "react";
import NutritionSummaryBar from "@/components/lifestyle-planner/NutritionSummaryBar";
import MealPlanCard from "@/components/lifestyle-planner/MealPlanCard";
import AvoidListCard from "@/components/lifestyle-planner/AvoidListCard";
import { PageHero } from "@/components/ui/PageHero";
import { useLifestyleStore } from "@/lib/lifestyleStore";
import { lifestyleApi } from "@/lib/lifestyleApi";
import { getLocalUserId } from "@/lib/utils";
import { PAGE_IMAGES } from "@/lib/pageImages";

const MEAL_SLOTS = ["breakfast", "lunch", "dinner", "snacks"];

export default function DietPage() {
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

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <PageHero src={PAGE_IMAGES.diet} opacity={42} objectPosition="center 60%" accentColor="rgba(255,184,0,0.25)">
        <div className="p-5">
          <h1 className="text-2xl font-bold text-white">Diet Plan</h1>
          <p className="text-sm text-gray-400 mt-1">
            {(latestPlan.dietary_pref ?? "").replace("_", " ")} · {latestPlan.plan_date}
          </p>
        </div>
      </PageHero>

      <NutritionSummaryBar nutrition={latestPlan.daily_nutrition} />

      {/* Meal inspiration banner */}
      <div className="relative rounded-2xl overflow-hidden h-40">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={PAGE_IMAGES.diet} alt="" loading="lazy" decoding="async" aria-hidden
          className="absolute inset-0 w-full h-full object-cover pointer-events-none select-none"
          style={{ opacity: 0.45, objectPosition: "center 55%" }} />
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: "linear-gradient(to right, rgba(10,15,30,0.92) 0%, rgba(10,15,30,0.50) 55%, rgba(10,15,30,0.12) 100%)" }} />
        <div className="absolute bottom-0 left-0 right-0 h-px pointer-events-none"
          style={{ background: "linear-gradient(90deg, transparent, rgba(255,184,0,0.55), transparent)" }} />
        <div className="relative h-full flex items-center px-6 gap-8">
          <div>
            <p className="text-[11px] text-amber-400 font-semibold uppercase tracking-widest mb-1">Personalised Nutrition</p>
            <h3 className="text-white font-bold text-lg leading-tight">Balanced Meals for Your Goals</h3>
            <p className="text-slate-400 text-sm mt-1.5 max-w-xs leading-snug">Every meal crafted around your dietary preferences and daily calorie targets.</p>
          </div>
          <div className="ml-auto shrink-0 text-right">
            <p className="text-2xl font-bold text-amber-400">{latestPlan.daily_nutrition.calories}</p>
            <p className="text-xs text-slate-500">kcal / day</p>
            <p className="text-lg font-semibold text-green-400 mt-1">{latestPlan.daily_nutrition.protein_g}g</p>
            <p className="text-xs text-slate-500">protein</p>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {MEAL_SLOTS.map((slot) => {
          const meals = latestPlan.meals[slot] ?? [];
          if (!meals.length) return null;
          return <MealPlanCard key={slot} mealType={slot} meals={meals} />;
        })}
      </div>

      <AvoidListCard items={latestPlan.avoid_list} />
    </div>
  );
}
