"use client";
import { useState } from "react";
import { Plus, X, Thermometer } from "lucide-react";

interface FormState {
  pain_level: number;
  fever: string;
  feverUnit: "C" | "F";
  fatigue: "" | "low" | "medium" | "high";
  mood: number;
  sleep_hours: string;
  custom_symptoms: string[];
  notes: string;
}

const INITIAL: FormState = {
  pain_level: 0, fever: "", feverUnit: "C",
  fatigue: "", mood: 3, sleep_hours: "", custom_symptoms: [], notes: "",
};

interface Props {
  userId: string;
  onSubmit: (payload: object) => Promise<void>;
  loading?: boolean;
}

export default function SymptomLogForm({ userId, onSubmit, loading }: Props) {
  const [form, setForm] = useState<FormState>(INITIAL);
  const [customInput, setCustomInput] = useState("");

  const set = (k: keyof FormState, v: unknown) =>
    setForm((p) => ({ ...p, [k]: v }));

  const addCustom = () => {
    const trimmed = customInput.trim();
    if (trimmed && !form.custom_symptoms.includes(trimmed)) {
      set("custom_symptoms", [...form.custom_symptoms, trimmed]);
    }
    setCustomInput("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload: Record<string, unknown> = { user_id: userId };
    if (form.pain_level > 0) payload.pain_level = form.pain_level;
    if (form.fever) {
      if (form.feverUnit === "C") payload.fever_celsius = parseFloat(form.fever);
      else payload.fever_fahrenheit = parseFloat(form.fever);
    }
    if (form.fatigue) payload.fatigue = form.fatigue;
    if (form.mood) payload.mood = form.mood;
    if (form.sleep_hours) payload.sleep_hours = parseFloat(form.sleep_hours);
    if (form.custom_symptoms.length) payload.custom_symptoms = form.custom_symptoms;
    if (form.notes) payload.notes = form.notes;
    await onSubmit(payload);
    setForm(INITIAL);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5 p-5 rounded-2xl" style={{ background: "rgba(13,22,39,0.85)", border: "1px solid rgba(0,212,255,0.15)" }}>
      <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider">Log Today's Symptoms</h3>

      {/* Pain */}
      <div>
        <label className="text-xs text-gray-400 mb-1 block">Pain Level: <span className="text-white font-bold">{form.pain_level}/10</span></label>
        <input type="range" min={0} max={10} value={form.pain_level}
          onChange={(e) => set("pain_level", Number(e.target.value))}
          className="w-full accent-cyan-400" />
        <div className="flex justify-between text-xs text-gray-500 mt-0.5">
          <span>None</span><span>Moderate</span><span>Severe</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Fever */}
        <div>
          <label className="text-xs text-gray-400 mb-1 block flex items-center gap-1"><Thermometer size={12} />Fever</label>
          <div className="flex gap-1">
            <input type="number" step="0.1" placeholder="e.g. 37.5" value={form.fever}
              onChange={(e) => set("fever", e.target.value)}
              className="input-field flex-1 text-sm" />
            <button type="button"
              onClick={() => set("feverUnit", form.feverUnit === "C" ? "F" : "C")}
              className="px-2 rounded-lg text-xs font-bold"
              style={{ background: "rgba(0,212,255,0.15)", color: "#00D4FF" }}>
              °{form.feverUnit}
            </button>
          </div>
        </div>

        {/* Sleep */}
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Sleep (hours)</label>
          <input type="number" step="0.5" min={0} max={24} placeholder="e.g. 7.5" value={form.sleep_hours}
            onChange={(e) => set("sleep_hours", e.target.value)}
            className="input-field w-full text-sm" />
        </div>
      </div>

      {/* Fatigue */}
      <div>
        <label className="text-xs text-gray-400 mb-2 block">Fatigue</label>
        <div className="flex gap-2">
          {(["low", "medium", "high"] as const).map((f) => (
            <button key={f} type="button"
              onClick={() => set("fatigue", form.fatigue === f ? "" : f)}
              className="flex-1 py-1.5 rounded-lg text-xs font-medium capitalize transition-all"
              style={{
                background: form.fatigue === f ? (f === "high" ? "#FF3B3B33" : f === "medium" ? "#FFB80033" : "#00FF8833") : "rgba(255,255,255,0.05)",
                color: form.fatigue === f ? (f === "high" ? "#FF3B3B" : f === "medium" ? "#FFB800" : "#00FF88") : "#8899AA",
                border: `1px solid ${form.fatigue === f ? (f === "high" ? "#FF3B3B" : f === "medium" ? "#FFB800" : "#00FF88") : "transparent"}`,
              }}>
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Mood */}
      <div>
        <label className="text-xs text-gray-400 mb-2 block">Mood: <span className="text-white">{["😞","😕","😐","🙂","😊"][form.mood - 1]}</span></label>
        <div className="flex gap-2">
          {[1,2,3,4,5].map((m) => (
            <button key={m} type="button" onClick={() => set("mood", m)}
              className="flex-1 py-1.5 rounded-lg text-xs transition-all"
              style={{
                background: form.mood === m ? "rgba(0,212,255,0.2)" : "rgba(255,255,255,0.05)",
                border: `1px solid ${form.mood === m ? "#00D4FF" : "transparent"}`,
                color: form.mood === m ? "#00D4FF" : "#8899AA",
              }}>
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Custom Symptoms */}
      <div>
        <label className="text-xs text-gray-400 mb-1 block">Custom Symptoms</label>
        <div className="flex gap-2">
          <input value={customInput} onChange={(e) => setCustomInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addCustom(); }}}
            placeholder="e.g. headache" className="input-field flex-1 text-sm" />
          <button type="button" onClick={addCustom}
            className="px-3 rounded-lg" style={{ background: "rgba(0,212,255,0.15)", color: "#00D4FF" }}>
            <Plus size={14} />
          </button>
        </div>
        {form.custom_symptoms.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {form.custom_symptoms.map((s) => (
              <span key={s} className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs"
                style={{ background: "rgba(0,212,255,0.12)", color: "#00D4FF", border: "1px solid rgba(0,212,255,0.3)" }}>
                {s}
                <button type="button" onClick={() => set("custom_symptoms", form.custom_symptoms.filter((x) => x !== s))}>
                  <X size={10} />
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Notes */}
      <div>
        <label className="text-xs text-gray-400 mb-1 block">Notes</label>
        <textarea value={form.notes} onChange={(e) => set("notes", e.target.value)}
          rows={2} placeholder="Any additional observations..."
          className="input-field w-full text-sm resize-none" />
      </div>

      <button type="submit" disabled={loading}
        className="btn-primary w-full py-2.5 text-sm font-semibold">
        {loading ? "Saving…" : "Log Symptoms"}
      </button>
    </form>
  );
}
