"use client";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer,
} from "recharts";
import { SymptomTrendPoint } from "@/lib/healthTrackerStore";

type Metric = "avg_pain" | "avg_mood" | "avg_sleep" | "avg_fever";

const METRIC_CONFIG: Record<Metric, { label: string; color: string; domain: [number, number] }> = {
  avg_pain:  { label: "Pain",        color: "#FF3B3B", domain: [0, 10] },
  avg_mood:  { label: "Mood",        color: "#00D4FF", domain: [1, 5] },
  avg_sleep: { label: "Sleep (h)",   color: "#A78BFA", domain: [0, 12] },
  avg_fever: { label: "Fever (°C)",  color: "#FFB800", domain: [35, 42] },
};

interface Props {
  data: SymptomTrendPoint[];
  metrics: Metric[];
  onMetricToggle: (m: Metric) => void;
}

export default function SymptomTrendChart({ data, metrics, onMetricToggle }: Props) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-48 text-sm" style={{ color: "var(--label-secondary)" }}>
        Not enough data to show trends yet. Keep logging!
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {(Object.keys(METRIC_CONFIG) as Metric[]).map((m) => {
          const active = metrics.includes(m);
          return (
            <button key={m} onClick={() => onMetricToggle(m)}
              className="px-3 py-1 rounded-full text-xs font-medium transition-all"
              style={{
                background: active ? `${METRIC_CONFIG[m].color}22` : "var(--bg-elevated)",
                color: active ? METRIC_CONFIG[m].color : "var(--label-secondary)",
                border: `1px solid ${active ? METRIC_CONFIG[m].color : "transparent"}`,
              }}>
              {METRIC_CONFIG[m].label}
            </button>
          );
        })}
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
          <XAxis dataKey="date" tick={{ fill: "#8899AA", fontSize: 10 }}
            tickFormatter={(v: string) => v.substring(5)} />
          <YAxis tick={{ fill: "#8899AA", fontSize: 10 }} />
          <Tooltip
            contentStyle={{ background: "#0D1627", border: "1px solid #00D4FF33", borderRadius: 8 }}
            labelStyle={{ color: "#00D4FF", fontSize: 11 }}
            itemStyle={{ fontSize: 11 }} />
          <Legend wrapperStyle={{ fontSize: 11, color: "#8899AA" }} />
          {metrics.map((m) => (
            <Line key={m} type="monotone" dataKey={m}
              name={METRIC_CONFIG[m].label} stroke={METRIC_CONFIG[m].color}
              strokeWidth={2} dot={{ r: 3, fill: METRIC_CONFIG[m].color }}
              connectNulls activeDot={{ r: 5 }} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
