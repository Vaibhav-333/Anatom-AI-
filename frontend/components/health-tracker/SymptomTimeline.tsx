"use client";
import { Trash2, Thermometer, Moon, Activity } from "lucide-react";
import { SymptomLogResponse } from "@/lib/healthTrackerStore";

const FATIGUE_COLOR: Record<string, string> = {
  low: "#00FF88", medium: "#FFB800", high: "#FF3B3B"
};

interface Props {
  logs: SymptomLogResponse[];
  onDelete: (id: string) => void;
}

function groupByDate(logs: SymptomLogResponse[]) {
  const groups: Record<string, SymptomLogResponse[]> = {};
  for (const log of logs) {
    if (!groups[log.date_key]) groups[log.date_key] = [];
    groups[log.date_key].push(log);
  }
  return groups;
}

function PainBar({ level }: { level: number | null }) {
  if (level === null) return null;
  const color = level >= 7 ? "#FF3B3B" : level >= 4 ? "#FFB800" : "#00FF88";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full" style={{ background: "var(--bg-elevated)" }}>
        <div className="h-full rounded-full" style={{ width: `${level * 10}%`, background: color }} />
      </div>
      <span className="text-xs font-bold" style={{ color }}>{level}/10</span>
    </div>
  );
}

export default function SymptomTimeline({ logs, onDelete }: Props) {
  if (!logs.length) {
    return (
      <div className="text-center py-12 text-sm" style={{ color: "var(--label-secondary)" }}>
        No symptoms logged yet. Use the form above to start tracking.
      </div>
    );
  }
  const groups = groupByDate(logs);

  return (
    <div className="space-y-6">
      {Object.entries(groups).map(([date, entries]) => (
        <div key={date}>
          <div className="flex items-center gap-3 mb-3">
            <div className="h-px flex-1" style={{ background: "rgba(0,212,255,0.15)" }} />
            <span className="text-xs text-cyan-400 font-medium px-2 py-0.5 rounded-full"
              style={{ background: "rgba(0,212,255,0.08)", border: "1px solid rgba(0,212,255,0.2)" }}>
              {date}
            </span>
            <div className="h-px flex-1" style={{ background: "rgba(0,212,255,0.15)" }} />
          </div>

          <div className="space-y-3">
            {entries.map((log) => (
              <div key={log.id} className="group rounded-xl p-4"
                style={{ background: "rgba(13,22,39,0.7)", border: "1px solid rgba(0,212,255,0.1)" }}>
                <div className="flex justify-between items-start mb-3">
                  <span className="text-xs" style={{ color: "var(--label-tertiary)" }}>{log.logged_at.substring(11, 16)}</span>
                  <button onClick={() => onDelete(log.id)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity hover:text-red-400" style={{ color: "var(--label-tertiary)" }}>
                    <Trash2 size={14} />
                  </button>
                </div>

                <div className="space-y-2">
                  {log.pain_level !== null && (
                    <div className="space-y-1">
                      <span className="text-xs flex items-center gap-1" style={{ color: "var(--label-secondary)" }}><Activity size={10} />Pain</span>
                      <PainBar level={log.pain_level} />
                    </div>
                  )}

                  <div className="flex flex-wrap gap-2 mt-2">
                    {log.fatigue && (
                      <span className="px-2 py-0.5 rounded-full text-xs" style={{ background: `${FATIGUE_COLOR[log.fatigue]}22`, color: FATIGUE_COLOR[log.fatigue] }}>
                        Fatigue: {log.fatigue}
                      </span>
                    )}
                    {log.fever_celsius !== null && (
                      <span className="px-2 py-0.5 rounded-full text-xs flex items-center gap-1"
                        style={{ background: "rgba(255,59,59,0.15)", color: "#FF3B3B" }}>
                        <Thermometer size={10} />{log.fever_celsius}°C
                      </span>
                    )}
                    {log.sleep_hours !== null && (
                      <span className="px-2 py-0.5 rounded-full text-xs flex items-center gap-1"
                        style={{ background: "rgba(167,139,250,0.15)", color: "#A78BFA" }}>
                        <Moon size={10} />{log.sleep_hours}h sleep
                      </span>
                    )}
                    {log.mood !== null && (
                      <span className="px-2 py-0.5 rounded-full text-xs"
                        style={{ background: "rgba(0,212,255,0.12)", color: "#00D4FF" }}>
                        Mood {["😞","😕","😐","🙂","😊"][log.mood - 1]}
                      </span>
                    )}
                    {log.custom_symptoms.map((s) => (
                      <span key={s} className="px-2 py-0.5 rounded-full text-xs"
                        style={{ background: "rgba(255,184,0,0.12)", color: "#FFB800" }}>
                        {s}
                      </span>
                    ))}
                  </div>
                  {log.notes && <p className="text-xs mt-1 italic" style={{ color: "var(--label-tertiary)" }}>"{log.notes}"</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
