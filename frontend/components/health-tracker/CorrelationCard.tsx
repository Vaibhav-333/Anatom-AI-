"use client";
import { GitBranch } from "lucide-react";

interface Props {
  notes: string[];
}

export default function CorrelationCard({ notes }: Props) {
  if (!notes.length) return null;
  return (
    <div className="rounded-xl p-4 space-y-2"
      style={{ background: "rgba(167,139,250,0.08)", border: "1px solid rgba(167,139,250,0.2)" }}>
      <div className="flex items-center gap-2 mb-1">
        <GitBranch size={14} style={{ color: "#A78BFA" }} />
        <span className="text-xs font-semibold" style={{ color: "#A78BFA" }}>Correlations Detected</span>
      </div>
      {notes.map((note, i) => (
        <p key={i} className="text-xs text-gray-300 flex gap-2">
          <span style={{ color: "#A78BFA" }}>•</span>{note}
        </p>
      ))}
    </div>
  );
}
