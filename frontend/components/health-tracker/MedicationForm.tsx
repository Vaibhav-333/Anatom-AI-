"use client";
import { useState } from "react";

interface Props {
  userId: string;
  onSubmit: (payload: object) => Promise<void>;
  loading?: boolean;
  onCancel?: () => void;
}

export default function MedicationForm({ userId, onSubmit, loading, onCancel }: Props) {
  const [form, setForm] = useState({
    name: "", dosage: "", frequency: "once_daily",
    duration_days: "", start_date: new Date().toISOString().slice(0, 10),
  });

  const set = (k: string, v: string) => setForm((p) => ({ ...p, [k]: v }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload: Record<string, unknown> = {
      user_id: userId, name: form.name, dosage: form.dosage,
      frequency: form.frequency, start_date: form.start_date,
    };
    if (form.duration_days) payload.duration_days = parseInt(form.duration_days);
    await onSubmit(payload);
    setForm({ name: "", dosage: "", frequency: "once_daily", duration_days: "", start_date: new Date().toISOString().slice(0, 10) });
  };

  return (
    <form onSubmit={handleSubmit} className="p-5 rounded-2xl space-y-4"
      style={{ background: "rgba(13,22,39,0.85)", border: "1px solid rgba(0,212,255,0.15)" }}>
      <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider">Add Medication</h3>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Medication Name *</label>
          <input required value={form.name} onChange={(e) => set("name", e.target.value)}
            placeholder="e.g. Paracetamol" className="input-field w-full text-sm" />
        </div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Dosage *</label>
          <input required value={form.dosage} onChange={(e) => set("dosage", e.target.value)}
            placeholder="e.g. 500mg" className="input-field w-full text-sm" />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Frequency</label>
          <select value={form.frequency} onChange={(e) => set("frequency", e.target.value)}
            className="input-field w-full text-sm">
            <option value="once_daily">Once daily</option>
            <option value="twice_daily">Twice daily</option>
            <option value="thrice_daily">Three times daily</option>
            <option value="as_needed">As needed</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Duration (days)</label>
          <input type="number" value={form.duration_days} onChange={(e) => set("duration_days", e.target.value)}
            placeholder="Leave blank if ongoing" className="input-field w-full text-sm" />
        </div>
      </div>

      <div>
        <label className="text-xs text-gray-400 mb-1 block">Start Date</label>
        <input type="date" value={form.start_date} onChange={(e) => set("start_date", e.target.value)}
          className="input-field w-full text-sm" />
      </div>

      <div className="flex gap-3">
        <button type="submit" disabled={loading} className="btn-primary flex-1 py-2 text-sm font-semibold">
          {loading ? "Adding…" : "Add Medication"}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} className="btn-secondary flex-1 py-2 text-sm">
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
