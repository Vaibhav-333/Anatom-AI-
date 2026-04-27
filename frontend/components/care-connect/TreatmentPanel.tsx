"use client";

import { AlertTriangle, Leaf } from "lucide-react";
import { LinkedMedicalText } from "@/components/report/LinkedMedicalText";

interface Props {
  suggestions: string[];
}

export function TreatmentPanel({ suggestions }: Props) {
  if (!suggestions.length) return null;

  return (
    <div className="bg-navy-800/60 border border-glass-border rounded-2xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Leaf className="w-4 h-4 text-green" />
        <h3 className="font-semibold text-white text-sm">General Treatment Approach</h3>
      </div>
      <ul className="space-y-2">
        {suggestions.map((s, i) => (
          <li key={i} className="flex items-start gap-2.5 text-sm text-slate-300">
            <span className="w-5 h-5 rounded-full bg-green/10 border border-green/30 text-green text-xs flex items-center justify-center shrink-0 mt-0.5">{i + 1}</span>
            <LinkedMedicalText text={s} />
          </li>
        ))}
      </ul>
      <div className="mt-4 flex items-start gap-2 bg-amber-500/5 border border-amber-500/20 rounded-xl p-3">
        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <p className="text-xs text-amber-300/80 leading-relaxed">
          These are general wellness suggestions only. They do <strong>not</strong> constitute medical prescriptions,
          clinical diagnoses, or professional medical advice. Always consult a qualified healthcare professional.
        </p>
      </div>
    </div>
  );
}
