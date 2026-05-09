"use client";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  Legend, ResponsiveContainer,
} from "recharts";

interface DayEntry { date: string; taken_count: number; missed_count: number; }

interface Props {
  data: DayEntry[];
}

export default function AdherenceChart({ data }: Props) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-40 text-sm" style={{ color: "var(--label-secondary)" }}>
        No adherence data yet.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 5, right: 10, left: -15, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
        <XAxis dataKey="date" tick={{ fontSize: 9, fill: "#8899AA" }}
          tickFormatter={(v: string) => v.slice(5)} />
        <YAxis tick={{ fontSize: 9, fill: "#8899AA" }} />
        <Tooltip contentStyle={{ background: "#0D1627", border: "1px solid #00D4FF33", borderRadius: 8, fontSize: 11 }} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Bar dataKey="taken_count" name="Taken" fill="#00FF88" radius={[3,3,0,0]} />
        <Bar dataKey="missed_count" name="Missed" fill="#FF3B3B" radius={[3,3,0,0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
