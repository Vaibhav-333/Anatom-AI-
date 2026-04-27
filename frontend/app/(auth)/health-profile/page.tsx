"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain, Loader2, AlertCircle, CheckCircle2, ChevronRight, ChevronLeft,
  User, Activity, Pill, Leaf,
} from "lucide-react";
import { authApi, ApiError } from "@/lib/authApi";
import { useAuthStore } from "@/lib/authStore";

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------

const BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"];

const CONDITIONS = [
  "Diabetes", "Hypertension", "Heart Disease", "Asthma", "COPD",
  "Kidney Disease", "Thyroid Disorder", "Cancer", "Arthritis",
  "Depression / Anxiety", "Epilepsy", "Anemia", "None",
];

const ALLERGIES = [
  "Penicillin", "Aspirin", "NSAIDs", "Sulfa Drugs", "Latex",
  "Peanuts", "Tree Nuts", "Shellfish", "Gluten", "Dairy",
  "Pollen", "Dust Mites", "None",
];

const FAMILY_HISTORY = [
  "Heart Disease", "Diabetes", "Cancer", "Stroke", "Hypertension",
  "Mental Health Disorders", "Kidney Disease", "Alzheimer's", "None",
];

type Step = 1 | 2 | 3;

interface FormData {
  age: string;
  gender: string;
  heightCm: string;
  weightKg: string;
  bloodGroup: string;
  conditions: string[];
  allergies: string[];
  smoking: boolean;
  alcohol: string;
  activityLevel: string;
  familyHistory: string[];
}

const INITIAL: FormData = {
  age: "", gender: "", heightCm: "", weightKg: "",
  bloodGroup: "", conditions: [], allergies: [],
  smoking: false, alcohol: "none", activityLevel: "moderate",
  familyHistory: [],
};

// ---------------------------------------------------------------------------
// Step indicator
// ---------------------------------------------------------------------------

const STEPS = [
  { n: 1, label: "Basic Info", icon: User },
  { n: 2, label: "Medical", icon: Pill },
  { n: 3, label: "Lifestyle", icon: Leaf },
];

function StepBar({ current }: { current: Step }) {
  return (
    <div className="flex items-center gap-0 mb-8">
      {STEPS.map((s, i) => {
        const Icon = s.icon;
        return (
          <div key={s.n} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center gap-1 flex-shrink-0">
              <div className={`w-9 h-9 rounded-full flex items-center justify-center border-2 transition-all duration-300
                ${current > s.n ? "bg-emerald-500 border-emerald-500 text-white"
                  : current === s.n ? "bg-cyan-500 border-cyan-500 text-white shadow-[0_0_16px_rgba(34,211,238,0.4)]"
                  : "bg-transparent border-slate-600 text-slate-500"}`}
              >
                {current > s.n ? <CheckCircle2 className="w-5 h-5" /> : <Icon className="w-4 h-4" />}
              </div>
              <span className={`text-[10px] font-medium ${
                current === s.n ? "text-cyan-400" : current > s.n ? "text-emerald-400" : "text-slate-500"
              }`}>{s.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`flex-1 h-[2px] mx-2 mt-[-14px] rounded transition-all duration-500 ${
                current > s.n ? "bg-emerald-500" : "bg-slate-700"
              }`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Multi-select chip group
// ---------------------------------------------------------------------------

function ChipGroup({
  options, selected, onChange, exclusive,
}: {
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
  exclusive?: string; // If this value is selected, clear all others
}) {
  function toggle(opt: string) {
    if (opt === exclusive) {
      onChange(selected.includes(opt) ? [] : [opt]);
      return;
    }
    const without = selected.filter((s) => s !== exclusive);
    if (without.includes(opt)) {
      onChange(without.filter((s) => s !== opt));
    } else {
      onChange([...without, opt]);
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          onClick={() => toggle(opt)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all
            ${selected.includes(opt)
              ? "bg-cyan-500/20 border-cyan-500 text-cyan-300"
              : "bg-slate-800/50 border-slate-600 text-slate-400 hover:border-slate-500"
            }`}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Form field helpers
// ---------------------------------------------------------------------------

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-300 mb-2">{label}</label>
      {children}
    </div>
  );
}

function NumberInput({
  value, onChange, placeholder, min, max, unit,
}: {
  value: string; onChange: (v: string) => void;
  placeholder: string; min?: number; max?: number; unit?: string;
}) {
  return (
    <div className="relative">
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        min={min} max={max}
        className="w-full px-4 py-3 rounded-xl bg-slate-800/70 border border-slate-600 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/30 transition-all pr-14"
      />
      {unit && (
        <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 text-sm">{unit}</span>
      )}
    </div>
  );
}

function Select({
  value, onChange, options, placeholder,
}: {
  value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[]; placeholder?: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-4 py-3 rounded-xl bg-slate-800/70 border border-slate-600 text-white focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/30 transition-all"
    >
      {placeholder && <option value="" disabled>{placeholder}</option>}
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function HealthProfilePage() {
  const router = useRouter();
  const { user, updateHealthProfileDone } = useAuthStore();

  const [step, setStep] = useState<Step>(1);
  const [form, setForm] = useState<FormData>(INITIAL);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  function set<K extends keyof FormData>(key: K) {
    return (value: FormData[K]) => setForm((f) => ({ ...f, [key]: value }));
  }

  // Validate per-step before advancing
  function validateStep1(): string | null {
    if (!form.age || Number(form.age) < 1 || Number(form.age) > 129) return "Please enter a valid age (1–129).";
    if (!form.gender) return "Please select your gender.";
    if (!form.heightCm || Number(form.heightCm) <= 0) return "Please enter a valid height.";
    if (!form.weightKg || Number(form.weightKg) <= 0) return "Please enter a valid weight.";
    if (!form.bloodGroup) return "Please select your blood group.";
    return null;
  }

  function handleNext() {
    setError("");
    if (step === 1) {
      const err = validateStep1();
      if (err) { setError(err); return; }
    }
    setStep((s) => (s < 3 ? ((s + 1) as Step) : s));
  }

  async function handleSubmit() {
    setError("");
    setSaving(true);
    try {
      await authApi.saveHealthProfile({
        age: Number(form.age),
        gender: form.gender,
        height_cm: Number(form.heightCm),
        weight_kg: Number(form.weightKg),
        blood_group: form.bloodGroup,
        conditions: form.conditions,
        allergies: form.allergies,
        smoking: form.smoking,
        alcohol: form.alcohol,
        activity_level: form.activityLevel,
        family_history: form.familyHistory,
      });
      updateHealthProfileDone(true);
      router.replace("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save profile. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  const bmi = form.heightCm && form.weightKg
    ? (Number(form.weightKg) / ((Number(form.heightCm) / 100) ** 2)).toFixed(1)
    : null;

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-lg"
      >
        {/* Header */}
        <div className="flex items-center gap-3 justify-center mb-8">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/30">
            <Brain className="w-6 h-6 text-white" />
          </div>
          <span className="text-2xl font-bold tracking-tight text-white">
            Anatom<span className="text-cyan-400"> AI</span>
          </span>
        </div>

        {/* Info banner */}
        <div className="flex items-center gap-3 p-4 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-sm mb-6">
          <Activity className="w-5 h-5 flex-shrink-0" />
          <span>Complete your health profile to unlock personalised AI insights and your dashboard.</span>
        </div>

        {/* Card */}
        <div className="bg-slate-900/80 border border-slate-700/60 rounded-2xl p-8 shadow-2xl backdrop-blur-xl">
          <StepBar current={step} />

          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.22 }}
              className="space-y-5"
            >

              {/* ── Step 1: Basic Info ── */}
              {step === 1 && (
                <>
                  <h2 className="text-xl font-bold text-white mb-1">Basic Information</h2>
                  <p className="text-slate-400 text-sm mb-5">Tell us about yourself for personalised care.</p>

                  <div className="grid grid-cols-2 gap-4">
                    <Field label="Age">
                      <NumberInput value={form.age} onChange={set("age")} placeholder="e.g. 28" min={1} max={129} unit="yrs" />
                    </Field>
                    <Field label="Gender">
                      <Select value={form.gender} onChange={set("gender")}
                        placeholder="Select"
                        options={[
                          { value: "male", label: "Male" },
                          { value: "female", label: "Female" },
                          { value: "non_binary", label: "Non-binary" },
                          { value: "prefer_not_to_say", label: "Prefer not to say" },
                        ]}
                      />
                    </Field>
                    <Field label="Height">
                      <NumberInput value={form.heightCm} onChange={set("heightCm")} placeholder="170" min={50} max={250} unit="cm" />
                    </Field>
                    <Field label="Weight">
                      <NumberInput value={form.weightKg} onChange={set("weightKg")} placeholder="65" min={10} max={400} unit="kg" />
                    </Field>
                  </div>

                  {bmi && (
                    <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700 text-sm flex items-center gap-2">
                      <span className="text-slate-400">BMI:</span>
                      <span className={`font-bold ${Number(bmi) < 18.5 || Number(bmi) >= 30 ? "text-amber-400" : "text-emerald-400"}`}>
                        {bmi}
                      </span>
                      <span className="text-slate-500">
                        {Number(bmi) < 18.5 ? "— Underweight" : Number(bmi) < 25 ? "— Normal" : Number(bmi) < 30 ? "— Overweight" : "— Obese"}
                      </span>
                    </div>
                  )}

                  <Field label="Blood Group">
                    <div className="flex flex-wrap gap-2">
                      {BLOOD_GROUPS.map((bg) => (
                        <button key={bg} type="button" onClick={() => set("bloodGroup")(bg)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                            form.bloodGroup === bg
                              ? "bg-red-500/20 border-red-400 text-red-300"
                              : "bg-slate-800/50 border-slate-600 text-slate-400 hover:border-slate-500"
                          }`}>
                          {bg}
                        </button>
                      ))}
                    </div>
                  </Field>
                </>
              )}

              {/* ── Step 2: Medical History ── */}
              {step === 2 && (
                <>
                  <h2 className="text-xl font-bold text-white mb-1">Medical History</h2>
                  <p className="text-slate-400 text-sm mb-5">Select all that apply. This helps personalise your AI analysis.</p>

                  <Field label="Existing Conditions">
                    <ChipGroup options={CONDITIONS} selected={form.conditions}
                      onChange={set("conditions")} exclusive="None" />
                  </Field>

                  <Field label="Known Allergies">
                    <ChipGroup options={ALLERGIES} selected={form.allergies}
                      onChange={set("allergies")} exclusive="None" />
                  </Field>

                  <Field label="Family Medical History">
                    <ChipGroup options={FAMILY_HISTORY} selected={form.familyHistory}
                      onChange={set("familyHistory")} exclusive="None" />
                  </Field>
                </>
              )}

              {/* ── Step 3: Lifestyle ── */}
              {step === 3 && (
                <>
                  <h2 className="text-xl font-bold text-white mb-1">Lifestyle</h2>
                  <p className="text-slate-400 text-sm mb-5">Your lifestyle choices directly impact your health score.</p>

                  <Field label="Physical Activity Level">
                    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                      {[
                        { value: "sedentary", label: "Sedentary", desc: "Little to no exercise" },
                        { value: "light", label: "Light", desc: "1–3 days/week" },
                        { value: "moderate", label: "Moderate", desc: "3–5 days/week" },
                        { value: "active", label: "Active", desc: "6–7 days/week" },
                        { value: "very_active", label: "Very Active", desc: "Intense daily" },
                      ].map((opt) => (
                        <button key={opt.value} type="button" onClick={() => set("activityLevel")(opt.value)}
                          className={`p-3 rounded-xl border text-left transition-all ${
                            form.activityLevel === opt.value
                              ? "bg-cyan-500/15 border-cyan-500 text-white"
                              : "bg-slate-800/50 border-slate-600 text-slate-400 hover:border-slate-500"
                          }`}>
                          <div className="font-medium text-sm">{opt.label}</div>
                          <div className="text-xs opacity-60 mt-0.5">{opt.desc}</div>
                        </button>
                      ))}
                    </div>
                  </Field>

                  <Field label="Smoking">
                    <div className="flex gap-2">
                      {[{ v: false, l: "Non-smoker" }, { v: true, l: "Smoker" }].map(({ v, l }) => (
                        <button key={l} type="button" onClick={() => set("smoking")(v)}
                          className={`flex-1 py-2.5 rounded-xl border text-sm font-medium transition-all ${
                            form.smoking === v
                              ? "bg-cyan-500/15 border-cyan-500 text-cyan-300"
                              : "bg-slate-800/50 border-slate-600 text-slate-400"
                          }`}>
                          {l}
                        </button>
                      ))}
                    </div>
                  </Field>

                  <Field label="Alcohol Consumption">
                    <Select value={form.alcohol} onChange={set("alcohol")}
                      options={[
                        { value: "none", label: "None" },
                        { value: "occasional", label: "Occasional (1–2/week)" },
                        { value: "moderate", label: "Moderate (3–4/week)" },
                        { value: "heavy", label: "Heavy (daily)" },
                      ]}
                    />
                  </Field>
                </>
              )}
            </motion.div>
          </AnimatePresence>

          {/* Error */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-4 flex items-center gap-2.5 p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm"
              >
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Navigation buttons */}
          <div className="flex gap-3 mt-7">
            {step > 1 && (
              <button
                type="button"
                onClick={() => { setError(""); setStep((s) => (s - 1) as Step); }}
                className="flex items-center gap-1.5 px-5 py-3 rounded-xl border border-slate-600 text-slate-300 hover:bg-slate-800 transition-all text-sm font-medium"
              >
                <ChevronLeft className="w-4 h-4" /> Back
              </button>
            )}
            <button
              type="button"
              onClick={step < 3 ? handleNext : handleSubmit}
              disabled={saving}
              className="flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-semibold text-sm bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 transition-all shadow-lg shadow-cyan-500/20"
            >
              {saving ? (
                <><Loader2 className="w-4 h-4 animate-spin" />Saving…</>
              ) : step < 3 ? (
                <>Continue <ChevronRight className="w-4 h-4" /></>
              ) : (
                <>Complete Setup <CheckCircle2 className="w-4 h-4" /></>
              )}
            </button>
          </div>

          {step === 2 && (
            <button
              type="button"
              onClick={() => { setError(""); setStep(3); }}
              className="mt-3 w-full text-center text-sm text-slate-500 hover:text-slate-400 transition-colors"
            >
              Skip for now
            </button>
          )}
        </div>

        <p className="mt-4 text-center text-xs text-slate-600">
          Your health data is encrypted and never shared without your consent.
        </p>
      </motion.div>
    </div>
  );
}
