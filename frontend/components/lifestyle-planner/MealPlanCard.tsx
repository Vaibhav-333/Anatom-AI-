"use client";
import { useState } from "react";
import { ChevronDown, ChevronUp, Clock } from "lucide-react";
import { MealEntry } from "@/lib/lifestyleStore";

const SLOT_COLORS: Record<string, string> = {
  breakfast: "#FFB800", lunch: "#00D4FF",
  dinner: "#A78BFA", snacks: "#00FF88",
};

interface Props {
  mealType: string;
  meals: MealEntry[];
}

export default function MealPlanCard({ mealType, meals }: Props) {
  const [open, setOpen] = useState(mealType === "breakfast");
  const color = SLOT_COLORS[mealType] ?? "#8899AA";
  const totalCal = meals.reduce((s, m) => s + m.nutrition.calories, 0);

  return (
    <div className="rounded-2xl overflow-hidden"
      style={{ background: "rgba(13,22,39,0.85)", border: `1px solid ${color}33` }}>
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-4">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full" style={{ background: color }} />
          <span className="text-sm font-semibold capitalize text-white">{mealType}</span>
          <span className="text-xs text-gray-500">{totalCal} kcal</span>
        </div>
        {open ? <ChevronUp size={14} className="text-gray-500" /> : <ChevronDown size={14} className="text-gray-500" />}
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3">
          {meals.map((meal, i) => (
            <div key={i} className="rounded-xl p-3" style={{ background: `${color}0A` }}>
              <div className="flex justify-between items-start mb-1">
                <p className="text-sm font-medium text-white">{meal.name}</p>
                <span className="flex items-center gap-1 text-xs text-gray-500">
                  <Clock size={10} />{meal.prep_time_min}m
                </span>
              </div>
              <p className="text-xs text-gray-400 mb-2">{meal.description}</p>
              <div className="flex flex-wrap gap-2">
                {[
                  { label: `${meal.nutrition.calories} kcal`, col: "#FFB800" },
                  { label: `${meal.nutrition.protein_g}g protein`, col: "#00FF88" },
                  { label: `${meal.nutrition.carbs_g}g carbs`, col: "#00D4FF" },
                  { label: `${meal.nutrition.fat_g}g fat`, col: "#A78BFA" },
                ].map((chip) => (
                  <span key={chip.label} className="px-2 py-0.5 rounded-full text-xs"
                    style={{ background: `${chip.col}18`, color: chip.col }}>
                    {chip.label}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
