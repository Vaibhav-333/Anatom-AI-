"use client";
import { useState } from "react";
import { Sparkles } from "lucide-react";
import { LifestylePlanRequest } from "@/lib/lifestyleStore";

const GOALS = [
  { value: "recovery", label: "Recovery", desc: "Focus on healing", color: "#00D4FF" },
  { value: "fitness", label: "Fitness", desc: "Build strength", color: "#00FF88" },
  { value: "chronic_management", label: "Chronic Care", desc: "Long-term balance", color: "#A78BFA" },
] as const;

const ACTIVITY_LEVELS = [
  { value: "sedentary", label: "Rest" },
  { value: "light", label: "Light" },
  { value: "moderate", label: "Moderate" },
  { value: "heavy", label: "Active" },
] as const;

const RESTRICTIONS = ["Gluten-free", "Dairy-free", "Nut-free", "Low-sodium", "Diabetic-friendly", "Low-fat"];
const DIET_PREFS = ["vegetarian", "vegan", "non_vegetarian", "keto"];

interface Props {
  userId: string;
  onGenerate: (req: LifestylePlanRequest) => Promise<void>;
  loading: boolean;
  initialValues?: Partial<LifestylePlanRequest>;
}

export default function LifestylePlannerForm({ userId, onGenerate, loading, initialValues }: Props) {
  const [goal, setGoal] = useState<LifestylePlanRequest["goal"]>(initialValues?.goal ?? "recovery");
  const [diet, setDiet] = useState(initialValues?.dietary_pref ?? "vegetarian");
  const [activity, setActivity] = useState<LifestylePlanRequest["activity_level"]>(initialValues?.activity_level ?? "light");
  const [restrictions, setRestrictions] = useState<string[]>(initialValues?.restrictions ?? []);

  const toggleRestriction = (r: string) =>
    setRestrictions((p) => p.includes(r) ? p.filter((x) => x !== r) : [...p, r]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onGenerate({ user_id: userId, goal, dietary_pref: diet, restrictions, activity_level: activity });
  };

  return (
    <form onSubmit={handleSubmit} className="rounded-2xl p-6 space-y-6"
      style={{ background: "rgba(13,22,39,0.85)", border: "1px solid rgba(0,212,255,0.15)" }}>
      <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider">Generate Lifestyle Plan</h3>

      {/* Goal */}
      <div>
        <label className="text-xs mb-2 block" style={{ color: "var(--label-secondary)" }}>Your Goal</label>
        <div className="grid grid-cols-3 gap-3">
          {GOALS.map((g) => (
            <button key={g.value} type="button" onClick={() => setGoal(g.value)}
              className="rounded-xl p-3 text-left transition-all"
              style={{
                background: goal === g.value ? `${g.color}22` : "var(--bg-elevated)",
                border: `1px solid ${goal === g.value ? g.color : "transparent"}`,
              }}>
              <p className="text-xs font-semibold" style={{ color: goal === g.value ? g.color : "var(--label-primary)" }}>{g.label}</p>
              <p className="text-xs mt-0.5" style={{ color: "var(--label-tertiary)" }}>{g.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Diet */}
      <div>
        <label className="text-xs mb-2 block" style={{ color: "var(--label-secondary)" }}>Dietary Preference</label>
        <div className="grid grid-cols-4 gap-2">
          {DIET_PREFS.map((d) => (
            <button key={d} type="button" onClick={() => setDiet(d)}
              className="py-2 rounded-xl text-xs font-medium capitalize transition-all"
              style={{
                background: diet === d ? "rgba(0,212,255,0.2)" : "var(--bg-elevated)",
                color: diet === d ? "#00D4FF" : "var(--label-secondary)",
                border: `1px solid ${diet === d ? "#00D4FF" : "transparent"}`,
              }}>
              {d.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Activity */}
      <div>
        <label className="text-xs mb-2 block" style={{ color: "var(--label-secondary)" }}>Activity Level</label>
        <div className="grid grid-cols-4 gap-2">
          {ACTIVITY_LEVELS.map((al) => (
            <button key={al.value} type="button" onClick={() => setActivity(al.value)}
              className="py-2 rounded-xl text-xs font-medium transition-all"
              style={{
                background: activity === al.value ? "rgba(0,255,136,0.2)" : "var(--bg-elevated)",
                color: activity === al.value ? "#00FF88" : "var(--label-secondary)",
                border: `1px solid ${activity === al.value ? "#00FF88" : "transparent"}`,
              }}>
              {al.label}
            </button>
          ))}
        </div>
      </div>

      {/* Restrictions */}
      <div>
        <label className="text-xs mb-2 block" style={{ color: "var(--label-secondary)" }}>Dietary Restrictions</label>
        <div className="flex flex-wrap gap-2">
          {RESTRICTIONS.map((r) => (
            <button key={r} type="button" onClick={() => toggleRestriction(r)}
              className="px-3 py-1 rounded-full text-xs font-medium transition-all"
              style={{
                background: restrictions.includes(r) ? "rgba(255,184,0,0.2)" : "var(--bg-elevated)",
                color: restrictions.includes(r) ? "#FFB800" : "var(--label-secondary)",
                border: `1px solid ${restrictions.includes(r) ? "#FFB800" : "transparent"}`,
              }}>
              {r}
            </button>
          ))}
        </div>
      </div>

      <button type="submit" disabled={loading}
        className="btn-primary w-full py-3 text-sm font-semibold flex items-center justify-center gap-2">
        {loading ? (
          <><span className="animate-spin">⟳</span> Generating Plan…</>
        ) : (
          <><Sparkles size={14} /> Generate My Plan</>
        )}
      </button>
    </form>
  );
}
