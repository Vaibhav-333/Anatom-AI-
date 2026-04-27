"use client";
import { ShieldCheck } from "lucide-react";

interface Props {
  items: string[];
}

export default function PreventiveCareCard({ items }: Props) {
  if (!items.length) return null;
  return (
    <div className="rounded-2xl p-5 space-y-3"
      style={{ background: "rgba(0,255,136,0.06)", border: "1px solid rgba(0,255,136,0.2)" }}>
      <div className="flex items-center gap-2">
        <ShieldCheck size={14} className="text-green-400" />
        <span className="text-sm font-semibold text-green-400">Preventive Care Tips</span>
      </div>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex gap-3 text-sm text-gray-300">
            <span className="text-green-400 mt-0.5 flex-shrink-0">✓</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
