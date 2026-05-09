"use client";
import { Check, X, StopCircle } from "lucide-react";
import WeeklyScoreRing from "./WeeklyScoreRing";
import { MedicationResponse, AdherenceStats } from "@/lib/healthTrackerStore";

const FREQ_LABEL: Record<string, string> = {
  once_daily: "1×/day", twice_daily: "2×/day",
  thrice_daily: "3×/day", as_needed: "As needed",
};

interface Props {
  medication: MedicationResponse;
  adherence?: AdherenceStats;
  todayStatus?: "taken" | "missed" | null;
  onLogDose: (medId: string, status: "taken" | "missed") => void;
  onDeactivate: (medId: string) => void;
}

export default function MedicationCard({ medication, adherence, todayStatus, onLogDose, onDeactivate }: Props) {
  const pct = Math.round(adherence?.adherence_pct ?? 0);

  return (
    <div className="rounded-2xl p-5 flex flex-col gap-4"
      style={{ background: "rgba(13,22,39,0.8)", border: "1px solid rgba(0,212,255,0.12)" }}>
      <div className="flex justify-between items-start">
        <div>
          <h4 className="text-sm font-semibold" style={{ color: "var(--label-primary)" }}>{medication.name}</h4>
          <p className="text-xs mt-0.5" style={{ color: "var(--label-secondary)" }}>{medication.dosage} · {FREQ_LABEL[medication.frequency]}</p>
          {medication.end_date && (
            <p className="text-xs mt-0.5" style={{ color: "var(--label-tertiary)" }}>Until {medication.end_date}</p>
          )}
        </div>
        <WeeklyScoreRing score={pct} size="sm" label={`${pct}%`} />
      </div>

      {adherence && adherence.total_doses > 0 && (
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded-lg py-2" style={{ background: "rgba(0,255,136,0.08)" }}>
            <p className="text-sm font-bold text-green-400">{adherence.taken}</p>
            <p className="text-xs" style={{ color: "var(--label-tertiary)" }}>Taken</p>
          </div>
          <div className="rounded-lg py-2" style={{ background: "rgba(255,59,59,0.08)" }}>
            <p className="text-sm font-bold text-red-400">{adherence.missed}</p>
            <p className="text-xs" style={{ color: "var(--label-tertiary)" }}>Missed</p>
          </div>
          <div className="rounded-lg py-2" style={{ background: "rgba(0,212,255,0.08)" }}>
            <p className="text-sm font-bold text-cyan-400">{adherence.total_doses}</p>
            <p className="text-xs" style={{ color: "var(--label-tertiary)" }}>Total</p>
          </div>
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={() => onLogDose(medication.id, "taken")}
          disabled={todayStatus === "taken"}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-semibold transition-all"
          style={{
            background: todayStatus === "taken" ? "rgba(0,255,136,0.25)" : "rgba(0,255,136,0.12)",
            color: "#00FF88", border: `1px solid ${todayStatus === "taken" ? "#00FF88" : "#00FF8833"}`,
          }}>
          <Check size={13} /> {todayStatus === "taken" ? "Taken ✓" : "Mark Taken"}
        </button>
        <button
          onClick={() => onLogDose(medication.id, "missed")}
          disabled={todayStatus === "missed"}
          className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all"
          style={{
            background: "rgba(255,59,59,0.08)", color: "#FF3B3B",
            border: "1px solid rgba(255,59,59,0.2)",
          }}>
          <X size={13} />
        </button>
        <button onClick={() => onDeactivate(medication.id)}
          className="flex items-center justify-center px-3 py-2 rounded-xl"
          style={{ background: "var(--bg-elevated)", color: "var(--label-secondary)" }}
          title="Stop medication">
          <StopCircle size={13} />
        </button>
      </div>
    </div>
  );
}
