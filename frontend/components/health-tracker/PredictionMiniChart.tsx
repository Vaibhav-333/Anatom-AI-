"use client";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { SymptomTrendPoint } from "@/lib/healthTrackerStore";

interface Props {
  historical: SymptomTrendPoint[];
  prediction: { pain: number; mood: number };
}

export default function PredictionMiniChart({ historical, prediction }: Props) {
  const last7 = historical.slice(-7);
  const lastDate = last7[last7.length - 1]?.date ?? "";
  const fakeDay = (offset: number) => {
    if (!lastDate) return `+${offset}d`;
    const d = new Date(lastDate);
    d.setDate(d.getDate() + offset);
    return d.toISOString().slice(5, 10);
  };

  const chartData = [
    ...last7.map((p) => ({ date: p.date.slice(5), pain: p.avg_pain, predicted: null })),
    { date: fakeDay(1), pain: null, predicted: prediction.pain },
    { date: fakeDay(2), pain: null, predicted: prediction.pain },
    { date: fakeDay(3), pain: null, predicted: prediction.pain },
  ];

  return (
    <div className="rounded-xl p-4" style={{ background: "rgba(0,212,255,0.06)", border: "1px solid rgba(0,212,255,0.15)" }}>
      <p className="text-xs font-semibold text-cyan-400 mb-3">3-Day Pain Forecast</p>
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={chartData} margin={{ top: 0, right: 8, left: -20, bottom: 0 }}>
          <XAxis dataKey="date" tick={{ fontSize: 9, fill: "#8899AA" }} />
          <YAxis domain={[0, 10]} tick={{ fontSize: 9, fill: "#8899AA" }} />
          <Tooltip contentStyle={{ background: "#0D1627", border: "1px solid #00D4FF33", borderRadius: 6, fontSize: 10 }} />
          <Line dataKey="pain" stroke="#FF3B3B" strokeWidth={2} dot={{ r: 2 }} connectNulls name="Actual" />
          <Line dataKey="predicted" stroke="#FFB800" strokeWidth={2} strokeDasharray="4 3"
            dot={{ r: 3, fill: "#FFB800" }} name="Predicted" />
          <ReferenceLine x={lastDate.slice(5)} stroke="var(--border-default)" strokeDasharray="3 3" />
        </LineChart>
      </ResponsiveContainer>
      <p className="text-xs mt-1" style={{ color: "var(--label-tertiary)" }}>
        Predicted avg pain next 3 days: <span className="text-amber-400 font-semibold">{prediction.pain.toFixed(1)}/10</span>
      </p>
    </div>
  );
}
