"use client";
import { CalendarHeatmapPoint } from "@/lib/healthTrackerStore";
import { ChevronLeft, ChevronRight } from "lucide-react";

const DAYS = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function intensityToColor(v: number) {
  if (v === 0) return "var(--bg-elevated)";
  if (v < 0.3) return "#00FF8833";
  if (v < 0.6) return "#FFB80055";
  return "#FF3B3B66";
}

interface Props {
  data: CalendarHeatmapPoint[];
  year: number;
  month: number;
  onMonthChange: (year: number, month: number) => void;
  onDayClick?: (date: string) => void;
}

export default function SymptomCalendarHeatmap({ data, year, month, onMonthChange, onDayClick }: Props) {
  const map = Object.fromEntries(data.map((d) => [d.date, d.intensity]));
  const firstDay = new Date(year, month - 1, 1).getDay();
  const daysInMonth = new Date(year, month, 0).getDate();
  const cells: (number | null)[] = [...Array(firstDay).fill(null), ...Array.from({length: daysInMonth}, (_, i) => i + 1)];

  const prev = () => month === 1 ? onMonthChange(year - 1, 12) : onMonthChange(year, month - 1);
  const next = () => month === 12 ? onMonthChange(year + 1, 1) : onMonthChange(year, month + 1);

  return (
    <div className="rounded-2xl p-5" style={{ background: "rgba(13,22,39,0.7)", border: "1px solid rgba(0,212,255,0.12)" }}>
      <div className="flex items-center justify-between mb-4">
        <button onClick={prev} className="p-1 rounded-lg" style={{ color: "var(--label-secondary)" }}><ChevronLeft size={16} /></button>
        <span className="text-sm font-medium" style={{ color: "var(--label-primary)" }}>{MONTHS[month - 1]} {year}</span>
        <button onClick={next} className="p-1 rounded-lg" style={{ color: "var(--label-secondary)" }}><ChevronRight size={16} /></button>
      </div>

      <div className="grid grid-cols-7 gap-1 mb-1">
        {DAYS.map((d) => <div key={d} className="text-center text-xs" style={{ color: "var(--label-tertiary)" }}>{d}</div>)}
      </div>

      <div className="grid grid-cols-7 gap-1">
        {cells.map((day, i) => {
          if (!day) return <div key={`empty-${i}`} />;
          const dateStr = `${year}-${String(month).padStart(2,"0")}-${String(day).padStart(2,"0")}`;
          const intensity = map[dateStr] ?? 0;
          return (
            <button key={dateStr} onClick={() => onDayClick?.(dateStr)}
              className="aspect-square rounded-md flex items-center justify-center text-xs transition-transform hover:scale-110"
              style={{ background: intensityToColor(intensity), color: "#ccc" }}
              title={intensity > 0 ? `Severity: ${Math.round(intensity * 100)}%` : "No data"}>
              {day}
            </button>
          );
        })}
      </div>

      <div className="flex items-center gap-3 mt-4 justify-end">
        <span className="text-xs" style={{ color: "var(--label-tertiary)" }}>Severity:</span>
        {[0,0.25,0.55,0.85].map((v, i) => (
          <div key={i} className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm" style={{ background: intensityToColor(v) }} />
            <span className="text-xs" style={{ color: "var(--label-tertiary)" }}>{["None","Low","Med","High"][i]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
