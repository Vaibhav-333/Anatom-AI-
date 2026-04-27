"use client";

import { useMemo } from "react";

interface Props {
  password: string;
}

interface Criterion {
  label: string;
  met: boolean;
}

function evaluate(password: string): { score: number; criteria: Criterion[] } {
  const criteria: Criterion[] = [
    { label: "At least 8 characters", met: password.length >= 8 },
    { label: "Uppercase letter", met: /[A-Z]/.test(password) },
    { label: "Lowercase letter", met: /[a-z]/.test(password) },
    { label: "Number", met: /\d/.test(password) },
    { label: "Special character", met: /[!@#$%^&*()_+\-=\[\]{}|;':",./<>?]/.test(password) },
  ];
  const score = criteria.filter((c) => c.met).length;
  return { score, criteria };
}

const LEVELS = [
  { label: "Very Weak", color: "bg-red-500" },
  { label: "Weak", color: "bg-orange-500" },
  { label: "Fair", color: "bg-yellow-400" },
  { label: "Good", color: "bg-blue-400" },
  { label: "Strong", color: "bg-emerald-400" },
];

export function PasswordStrengthBar({ password }: Props) {
  const { score, criteria } = useMemo(() => evaluate(password), [password]);

  if (!password) return null;

  const level = LEVELS[Math.max(0, score - 1)] ?? LEVELS[0];

  return (
    <div className="mt-2 space-y-2">
      {/* Bar */}
      <div className="flex gap-1">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-all duration-300 ${
              i < score ? level.color : "bg-slate-700"
            }`}
          />
        ))}
      </div>
      <p className={`text-xs font-medium ${level.color.replace("bg-", "text-")}`}>
        {level.label}
      </p>
      {/* Criteria checklist */}
      <ul className="grid grid-cols-2 gap-x-4 gap-y-0.5">
        {criteria.map((c) => (
          <li key={c.label} className="flex items-center gap-1.5 text-xs">
            <span
              className={`text-[10px] ${c.met ? "text-emerald-400" : "text-slate-500"}`}
            >
              {c.met ? "✓" : "○"}
            </span>
            <span className={c.met ? "text-slate-300" : "text-slate-500"}>
              {c.label}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
