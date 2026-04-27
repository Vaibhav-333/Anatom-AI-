"use client";
import { Timer, Zap } from "lucide-react";
import { ExerciseEntry } from "@/lib/lifestyleStore";

const INTENSITY_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  light:    { bg: "#00D4FF18", color: "#00D4FF", label: "Light" },
  moderate: { bg: "#FFB80018", color: "#FFB800", label: "Moderate" },
  heavy:    { bg: "#FF3B3B18", color: "#FF3B3B", label: "Active" },
};

interface Props {
  exercises: ExerciseEntry[];
  activityLevel: string;
}

export default function ExercisePlanCard({ exercises, activityLevel }: Props) {
  const totalMin = exercises.reduce((s, e) => s + e.duration_min, 0);

  if (!exercises.length) {
    return (
      <div className="rounded-2xl p-6 text-center text-gray-500 text-sm"
        style={{ background: "rgba(13,22,39,0.8)", border: "1px solid rgba(255,255,255,0.06)" }}>
        Rest day recommended. Focus on recovery and light stretching.
      </div>
    );
  }

  return (
    <div className="rounded-2xl p-5 space-y-4"
      style={{ background: "rgba(13,22,39,0.85)", border: "1px solid rgba(0,255,136,0.15)" }}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap size={16} className="text-green-400" />
          <span className="text-sm font-semibold text-white">Exercise Plan</span>
        </div>
        <span className="text-xs text-gray-400 flex items-center gap-1">
          <Timer size={11} />{totalMin} min total
        </span>
      </div>

      <div className="space-y-3">
        {exercises.map((ex, i) => {
          const sty = INTENSITY_STYLE[ex.intensity] ?? INTENSITY_STYLE.light;
          return (
            <div key={i} className="rounded-xl p-4"
              style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
              <div className="flex justify-between items-start mb-2">
                <p className="text-sm font-medium text-white">{ex.name}</p>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">{ex.duration_min} min</span>
                  <span className="px-2 py-0.5 rounded-full text-xs" style={{ background: sty.bg, color: sty.color }}>
                    {sty.label}
                  </span>
                </div>
              </div>
              <p className="text-xs text-gray-400">{ex.instructions}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
