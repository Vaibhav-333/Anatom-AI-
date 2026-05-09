"use client";
import { NutritionInfo } from "@/lib/lifestyleStore";

const MACROS = [
  { key: "protein_g" as keyof NutritionInfo, label: "Protein", color: "#00FF88", unit: "g", max: 100 },
  { key: "carbs_g" as keyof NutritionInfo, label: "Carbs", color: "#00D4FF", unit: "g", max: 300 },
  { key: "fat_g" as keyof NutritionInfo, label: "Fat", color: "#A78BFA", unit: "g", max: 80 },
  { key: "fiber_g" as keyof NutritionInfo, label: "Fiber", color: "#FFB800", unit: "g", max: 40 },
];

interface Props {
  nutrition: NutritionInfo;
}

export default function NutritionSummaryBar({ nutrition }: Props) {
  return (
    <div className="rounded-2xl p-5 space-y-4"
      style={{ background: "rgba(13,22,39,0.85)", border: "1px solid rgba(0,212,255,0.12)" }}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-white">Daily Nutrition</span>
        <span className="text-2xl font-bold" style={{ color: "#FFB800" }}>
          {nutrition.calories} <span className="text-sm font-normal text-gray-400">kcal</span>
        </span>
      </div>

      <div className="space-y-3">
        {MACROS.map((m) => {
          const val = Number(nutrition[m.key]);
          const pct = Math.min(100, (val / m.max) * 100);
          return (
            <div key={m.key}>
              <div className="flex justify-between text-xs mb-1">
                <span style={{ color: "var(--label-secondary)" }}>{m.label}</span>
                <span style={{ color: m.color }}>{val}{m.unit}</span>
              </div>
              <div className="h-2 rounded-full" style={{ background: "var(--bg-elevated)" }}>
                <div className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${pct}%`, background: m.color, boxShadow: `0 0 6px ${m.color}66` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
