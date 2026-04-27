"use client";
import { Ban } from "lucide-react";

interface Props {
  items: string[];
}

export default function AvoidListCard({ items }: Props) {
  if (!items.length) return null;
  return (
    <div className="rounded-2xl p-5"
      style={{ background: "rgba(255,59,59,0.06)", border: "1px solid rgba(255,59,59,0.2)" }}>
      <div className="flex items-center gap-2 mb-3">
        <Ban size={14} className="text-red-400" />
        <span className="text-sm font-semibold text-red-400">Foods & Activities to Avoid</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {items.map((item, i) => (
          <span key={i} className="px-3 py-1 rounded-full text-xs font-medium"
            style={{ background: "rgba(255,59,59,0.15)", color: "#FF3B3B", border: "1px solid rgba(255,59,59,0.3)" }}>
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
