"use client";

import { ProbableCondition } from "@/lib/careConnectApi";
import { LinkedMedicalText } from "@/components/report/LinkedMedicalText";

export function ConditionTable({ conditions }: { conditions: ProbableCondition[] }) {
  if (!conditions.length) return null;

  return (
    <div className="overflow-hidden rounded-xl border border-glass-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-glass-border bg-navy-800/60">
            <th className="px-4 py-2.5 text-left text-xs font-semibold text-cyan uppercase tracking-wider">Condition</th>
            <th className="px-4 py-2.5 text-left text-xs font-semibold text-cyan uppercase tracking-wider w-40">Likelihood</th>
            <th className="px-4 py-2.5 text-left text-xs font-semibold text-cyan uppercase tracking-wider hidden md:table-cell">Description</th>
          </tr>
        </thead>
        <tbody>
          {conditions.map((c, i) => (
            <tr key={i} className="border-b border-glass-border/50 last:border-0 hover:bg-navy-700/30 transition-colors">
              <td className="px-4 py-3 font-medium text-white">
                <LinkedMedicalText text={c.name} />
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 bg-navy-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-cyan rounded-full transition-all duration-700"
                      style={{ width: `${c.confidence_pct}%` }}
                    />
                  </div>
                  <span className="text-xs text-slate-400 font-mono w-8">{c.confidence_pct}%</span>
                </div>
              </td>
              <td className="px-4 py-3 text-slate-400 text-xs hidden md:table-cell leading-relaxed">
                <LinkedMedicalText text={c.description} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
