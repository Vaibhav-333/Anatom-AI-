"use client";

import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { User, Save, Plus, X } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageHero } from "@/components/ui/PageHero";
import { PAGE_IMAGES } from "@/lib/pageImages";
import { GlassCard } from "@/components/ui/GlassCard";
import { NeonButton } from "@/components/ui/NeonButton";
import { MetricRow } from "@/components/ui/MetricRow";
import { AlertBox } from "@/components/ui/AlertBox";
import { SectionDivider } from "@/components/ui/PageHeader";
import { createProfile, getProfile } from "@/lib/api";
import {
  calculateBMI,
  calculateHealthScore,
  calculateMetabolicAge,
  getBMICategory,
  getLocalUserId,
  setLocalUserId,
  generateUserId,
} from "@/lib/utils";

const BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

const COMMON_CONDITIONS = [
  "Hypertension", "Type 2 Diabetes", "Asthma", "Heart Disease",
  "High Cholesterol", "Anxiety", "Depression", "Arthritis",
  "Thyroid Disorder", "Obesity", "GERD", "Migraine",
];

// ---------------------------------------------------------------------------
// Animated health score gauge (SVG arc)
// ---------------------------------------------------------------------------
function HealthGauge({ score }: { score: number }) {
  const radius = 44;
  const stroke = 7;
  const normalised = Math.max(0, Math.min(100, score));
  const circumference = Math.PI * radius; // half-circle
  const dash = (normalised / 100) * circumference;

  // Colour transitions: green ≥ 70, amber 40–69, red < 40
  const colour =
    normalised >= 70 ? "#00FF88" : normalised >= 40 ? "#FFB800" : "#FF3B3B";

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={110} height={62} viewBox="0 0 110 62">
        {/* Track */}
        <path
          d="M 7 55 A 48 48 0 0 1 103 55"
          fill="none"
          stroke="rgba(255,255,255,0.07)"
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        {/* Animated fill */}
        <motion.path
          d="M 7 55 A 48 48 0 0 1 103 55"
          fill="none"
          stroke={colour}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${circumference} ${circumference}`}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - dash }}
          transition={{ duration: 1.2, ease: "easeOut" }}
          style={{ filter: `drop-shadow(0 0 6px ${colour}80)` }}
        />
        {/* Score text */}
        <text x="55" y="50" textAnchor="middle" fontSize="18" fontWeight="700"
          fill={colour} fontFamily="JetBrains Mono, monospace">
          {normalised}
        </text>
      </svg>
      <p className="metric-label text-xs">Health Score / 100</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
type FormState = {
  name: string;
  age: number;
  gender: "male" | "female" | "other";
  height_cm: number;
  weight_kg: number;
  blood_type: string;
  conditions: string[];
  medications: string[];
};

const defaultForm: FormState = {
  name: "",
  age: 30,
  gender: "male",
  height_cm: 170,
  weight_kg: 70,
  blood_type: "O+",
  conditions: [],
  medications: [],
};

export default function ProfilePage() {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [conditionInput, setConditionInput] = useState("");
  const [medInput, setMedInput] = useState("");
  const [form, setForm] = useState<FormState>(defaultForm);
  // Server-returned metrics (override client computation after save/load)
  const [serverScore, setServerScore] = useState<number | null>(null);
  const [serverBmi, setServerBmi] = useState<number | null>(null);
  const [serverMetAge, setServerMetAge] = useState<number | null>(null);
  const lastSavedHashRef = useRef<string | null>(null);

  // ── Load on mount ──────────────────────────────
  useEffect(() => {
    const userId = getLocalUserId();

    // Try backend first; fall back to localStorage
    async function loadProfile() {
      if (userId) {
        try {
          const profile = await getProfile(userId);
          const loaded: FormState = {
            name: profile.name,
            age: profile.age,
            gender: profile.gender as FormState["gender"],
            height_cm: profile.height_cm,
            weight_kg: profile.weight_kg,
            blood_type: profile.blood_type ?? "O+",
            conditions: profile.conditions,
            medications: profile.medications,
          };
          setForm(loaded);
          setServerScore(profile.health_score);
          if (profile.bmi) setServerBmi(profile.bmi);
          if (profile.metabolic_age) setServerMetAge(profile.metabolic_age);
          lastSavedHashRef.current = JSON.stringify(loaded);
          return;
        } catch {
          // Backend unreachable — fall through to localStorage
        }
      }

      const localRaw = localStorage.getItem("anatom_profile");
      if (localRaw) {
        try {
          const parsed = JSON.parse(localRaw) as FormState;
          setForm(parsed);
          lastSavedHashRef.current = JSON.stringify(parsed);
        } catch {}
      }
    }

    loadProfile();
  }, []);

  // ── Derived metrics (live as user types) ──────
  const bmi = serverBmi ?? calculateBMI(form.weight_kg, form.height_cm);
  const bmiCat = getBMICategory(bmi);
  const healthScore =
    serverScore ??
    calculateHealthScore({
      age: form.age,
      bmi,
      conditions: form.conditions,
      medications: form.medications,
    });
  const metabolicAge =
    serverMetAge ?? calculateMetabolicAge(form.age, bmi, form.conditions);
  const ageDelta = metabolicAge - form.age;

  // Recompute client-side whenever form changes (clears server overrides)
  const handleFormChange = (patch: Partial<FormState>) => {
    setForm((f) => ({ ...f, ...patch }));
    setServerScore(null);
    setServerBmi(null);
    setServerMetAge(null);
  };

  // ── Save ───────────────────────────────────────
  const handleSave = async () => {
    const currentHash = JSON.stringify(form);
    if (currentHash === lastSavedHashRef.current) {
      // Nothing changed — flash "Saved!" without re-hitting backend
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      return;
    }

    setSaving(true);
    setSaveError(false);

    let userId = getLocalUserId();
    if (!userId) {
      userId = generateUserId();
      setLocalUserId(userId);
    }

    try {
      const profile = await createProfile({
        user_id: userId,
        name: form.name,
        age: form.age,
        gender: form.gender,
        height_cm: form.height_cm,
        weight_kg: form.weight_kg,
        blood_type: form.blood_type || undefined,
        conditions: form.conditions,
        medications: form.medications,
      });
      // Adopt server-computed metrics
      setServerScore(profile.health_score);
      if (profile.bmi) setServerBmi(profile.bmi);
      if (profile.metabolic_age) setServerMetAge(profile.metabolic_age);
    } catch {
      setSaveError(true);
    }

    // Always persist locally as fallback
    localStorage.setItem("anatom_profile", JSON.stringify(form));
    lastSavedHashRef.current = currentHash;
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
    setSaving(false);
  };

  const addCondition = (cond: string) => {
    const trimmed = cond.trim();
    if (trimmed && !form.conditions.includes(trimmed)) {
      handleFormChange({ conditions: [...form.conditions, trimmed] });
    }
    setConditionInput("");
  };

  const addMed = () => {
    const trimmed = medInput.trim();
    if (trimmed && !form.medications.includes(trimmed)) {
      handleFormChange({ medications: [...form.medications, trimmed] });
    }
    setMedInput("");
  };

  const field = (label: string, children: React.ReactNode) => (
    <div>
      <label className="metric-label block mb-1.5">{label}</label>
      {children}
    </div>
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-3xl mx-auto space-y-6"
    >
      <PageHero src={PAGE_IMAGES.profile} opacity={36} objectPosition="center 20%" accentColor="rgba(0,255,136,0.20)">
        <PageHeader
          title="Health Profile"
          subtitle="Your personal health data — used to personalize AI analysis"
          icon={<User className="w-5 h-5" />}
          actions={
            <NeonButton
              onClick={handleSave}
              loading={saving}
              variant={saved ? "green" : "cyan"}
              icon={<Save className="w-4 h-4" />}
            >
              {saved ? "Saved!" : "Save Profile"}
            </NeonButton>
          }
        />
      </PageHero>

      {/* Live health metrics */}
      <div className="grid grid-cols-3 gap-4">
        {/* Animated gauge */}
        <GlassCard className="flex flex-col items-center justify-center py-3">
          <HealthGauge score={healthScore} />
        </GlassCard>

        {/* BMI */}
        <GlassCard className="text-center">
          <MetricRow
            label="BMI"
            value={bmi}
            color={bmiCat.color.replace("text-", "") as "cyan" | "green" | "amber" | "red"}
            size="lg"
            className="items-center"
          />
          <p className={`text-xs font-medium mt-1 ${bmiCat.color}`}>{bmiCat.label}</p>
        </GlassCard>

        {/* Metabolic Age */}
        <GlassCard className="text-center">
          <MetricRow
            label="Metabolic Age"
            value={metabolicAge}
            unit="yrs"
            color={ageDelta > 0 ? "amber" : "green"}
            size="lg"
            className="items-center"
          />
          {ageDelta !== 0 && (
            <p className={`text-xs font-semibold mt-1 ${ageDelta > 0 ? "text-amber" : "text-green"}`}>
              {ageDelta > 0 ? `+${ageDelta} older` : `${ageDelta} younger`}
            </p>
          )}
        </GlassCard>
      </div>

      {/* Personal info */}
      <GlassCard>
        <h3 className="section-title mb-4">Personal Information</h3>
        <div className="grid grid-cols-2 gap-4">
          {field("Full Name",
            <input
              className="input-field"
              placeholder="Enter your name"
              value={form.name}
              onChange={(e) => handleFormChange({ name: e.target.value })}
            />
          )}
          {field("Age",
            <input
              className="input-field"
              type="number"
              min={1} max={120}
              value={form.age}
              onChange={(e) => handleFormChange({ age: Number(e.target.value) })}
            />
          )}
          {field("Gender",
            <select
              className="input-field"
              value={form.gender}
              onChange={(e) => handleFormChange({ gender: e.target.value as FormState["gender"] })}
            >
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other / Prefer not to say</option>
            </select>
          )}
          {field("Blood Type",
            <select
              className="input-field"
              value={form.blood_type}
              onChange={(e) => handleFormChange({ blood_type: e.target.value })}
            >
              {BLOOD_TYPES.map((b) => <option key={b}>{b}</option>)}
            </select>
          )}
        </div>
      </GlassCard>

      {/* Physical stats */}
      <GlassCard>
        <h3 className="section-title mb-4">Physical Stats</h3>
        <div className="grid grid-cols-2 gap-4">
          {field("Height (cm)",
            <input
              className="input-field"
              type="number"
              min={100} max={250}
              value={form.height_cm}
              onChange={(e) => handleFormChange({ height_cm: Number(e.target.value) })}
            />
          )}
          {field("Weight (kg)",
            <input
              className="input-field"
              type="number"
              min={20} max={300}
              value={form.weight_kg}
              onChange={(e) => handleFormChange({ weight_kg: Number(e.target.value) })}
            />
          )}
        </div>
      </GlassCard>

      {/* Known conditions */}
      <GlassCard>
        <h3 className="section-title mb-4">Known Conditions</h3>
        <div className="flex flex-wrap gap-2 mb-3">
          {COMMON_CONDITIONS.map((cond) => (
            <button
              key={cond}
              onClick={() => addCondition(cond)}
              className={`text-xs px-2.5 py-1 rounded-full border transition-all ${
                form.conditions.includes(cond)
                  ? "border-cyan/40 bg-cyan/10 text-cyan"
                  : "border-glass-border text-slate-500 hover:border-cyan/20 hover:text-slate-300"
              }`}
            >
              {cond}
            </button>
          ))}
        </div>
        <div className="flex gap-2 mt-3">
          <input
            className="input-field flex-1"
            placeholder="Add custom condition..."
            value={conditionInput}
            onChange={(e) => setConditionInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addCondition(conditionInput)}
          />
          <NeonButton size="sm" onClick={() => addCondition(conditionInput)} icon={<Plus className="w-3.5 h-3.5" />}>Add</NeonButton>
        </div>
        {form.conditions.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {form.conditions.map((c) => (
              <span key={c} className="badge-warning flex items-center gap-1.5">
                {c}
                <button onClick={() => handleFormChange({ conditions: form.conditions.filter((x) => x !== c) })}>
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}
      </GlassCard>

      {/* Medications */}
      <GlassCard>
        <h3 className="section-title mb-4">Current Medications</h3>
        <div className="flex gap-2">
          <input
            className="input-field flex-1"
            placeholder="Add medication name..."
            value={medInput}
            onChange={(e) => setMedInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addMed()}
          />
          <NeonButton size="sm" onClick={addMed} icon={<Plus className="w-3.5 h-3.5" />}>Add</NeonButton>
        </div>
        {form.medications.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {form.medications.map((m) => (
              <span key={m} className="badge-info flex items-center gap-1.5">
                {m}
                <button onClick={() => handleFormChange({ medications: form.medications.filter((x) => x !== m) })}>
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}
      </GlassCard>

      <SectionDivider />

      {saveError && (
        <AlertBox variant="warning">
          Could not reach the backend — profile saved locally only. Start the Python server to enable cloud sync.
        </AlertBox>
      )}

      <AlertBox variant="info">
        Your health data is stored in a local SQLite database on this machine and backed up in your browser.
        It is never sent to third parties and is only used to personalise your AI health analysis.
        <strong className="block mt-1 text-slate-300">Not medical advice.</strong>
      </AlertBox>
    </motion.div>
  );
}
