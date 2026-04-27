import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { RiskLevel, Severity } from "./types";

// ── Tailwind class merging ────────────────────
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ── BMI & Health Score ────────────────────────
export function calculateBMI(weightKg: number, heightCm: number): number {
  const heightM = heightCm / 100;
  return Math.round((weightKg / (heightM * heightM)) * 10) / 10;
}

export function getBMICategory(bmi: number): {
  label: string;
  color: string;
} {
  if (bmi < 18.5) return { label: "Underweight", color: "text-amber" };
  if (bmi < 25.0) return { label: "Normal", color: "text-green" };
  if (bmi < 30.0) return { label: "Overweight", color: "text-amber" };
  return { label: "Obese", color: "text-red" };
}

export function calculateMetabolicAge(
  age: number,
  bmi: number,
  conditions: string[]
): number {
  let metabolicAge = age;
  if (bmi < 18.5) metabolicAge += 3;
  else if (bmi >= 25 && bmi < 30) metabolicAge += 3;
  else if (bmi >= 30) metabolicAge += 7;
  else metabolicAge -= 2;
  metabolicAge += conditions.length * 1.5;
  return Math.max(18, Math.round(metabolicAge));
}

export function calculateHealthScore(params: {
  age: number;
  bmi: number;
  conditions: string[];
  medications: string[];
}): number {
  let score = 80;

  // BMI penalty
  if (params.bmi < 18.5) score -= 8;
  else if (params.bmi >= 25 && params.bmi < 30) score -= 6;
  else if (params.bmi >= 30 && params.bmi < 35) score -= 14;
  else if (params.bmi >= 35) score -= 22;
  else score += 5; // Normal BMI bonus

  // Age factor
  if (params.age > 60) score -= 6;
  else if (params.age > 45) score -= 3;
  else if (params.age < 30) score += 5;

  // Conditions penalty
  score -= params.conditions.length * 5;

  // Medications penalty (mild — could be managing conditions)
  score -= params.medications.length * 2;

  return Math.max(5, Math.min(100, Math.round(score)));
}

// ── Risk Level ────────────────────────────────
export function getRiskConfig(risk: RiskLevel): {
  label: string;
  color: string;
  bg: string;
  border: string;
  score: number;
} {
  switch (risk) {
    case "low":
      return {
        label: "Low Risk",
        color: "text-green",
        bg: "bg-green/10",
        border: "border-green/30",
        score: 20,
      };
    case "moderate":
      return {
        label: "Moderate",
        color: "text-amber",
        bg: "bg-amber/10",
        border: "border-amber/30",
        score: 50,
      };
    case "high":
      return {
        label: "High Risk",
        color: "text-red",
        bg: "bg-red/10",
        border: "border-red/30",
        score: 75,
      };
    case "critical":
      return {
        label: "Critical",
        color: "text-red",
        bg: "bg-red/20",
        border: "border-red/50",
        score: 95,
      };
  }
}

export function getSeverityConfig(severity: Severity): {
  color: string;
  bg: string;
  border: string;
  dot: string;
} {
  switch (severity) {
    case "normal":
      return {
        color: "text-green",
        bg: "bg-green/10",
        border: "border-green/20",
        dot: "bg-green",
      };
    case "borderline":
      return {
        color: "text-amber",
        bg: "bg-amber/10",
        border: "border-amber/20",
        dot: "bg-amber",
      };
    case "critical":
      return {
        color: "text-red",
        bg: "bg-red/10",
        border: "border-red/20",
        dot: "bg-red",
      };
  }
}

// ── RANO ──────────────────────────────────────
export function getRANOConfig(category: "CR" | "PR" | "SD" | "PD"): {
  label: string;
  description: string;
  color: string;
  bg: string;
} {
  switch (category) {
    case "CR":
      return {
        label: "Complete Response",
        description: "≥95% reduction",
        color: "text-green",
        bg: "bg-green/10",
      };
    case "PR":
      return {
        label: "Partial Response",
        description: "≥50% decrease",
        color: "text-cyan",
        bg: "bg-cyan/10",
      };
    case "SD":
      return {
        label: "Stable Disease",
        description: "No significant change",
        color: "text-amber",
        bg: "bg-amber/10",
      };
    case "PD":
      return {
        label: "Progressive Disease",
        description: "≥25% increase",
        color: "text-red",
        bg: "bg-red/10",
      };
  }
}

// ── Formatters ────────────────────────────────
export function formatVolume(mm3: number): string {
  if (mm3 >= 1000) return `${(mm3 / 1000).toFixed(2)} cm³`;
  return `${mm3.toFixed(1)} mm³`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatRelativeDate(iso: string): string {
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diff = now - then;
  const days = Math.floor(diff / 86_400_000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
  return formatDate(iso);
}

export function formatPercent(value: number, decimals = 1): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

export function formatConfidence(value: number): string {
  const pct = Math.round(value * 100);
  if (pct >= 85) return `${pct}% confidence`;
  if (pct >= 65) return `${pct}% confidence (moderate)`;
  return `${pct}% confidence (low)`;
}

// ── Report type labels ─────────────────────────
export function getReportTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    brain_mri: "Brain MRI",
    xray: "X-Ray",
    blood_report: "Blood Report",
    ct: "CT Scan",
    ultrasound: "Ultrasound",
    unknown: "Medical Document",
  };
  return labels[type] ?? "Medical Document";
}

// ── Local storage helpers ─────────────────────
export function generateUserId(): string {
  return `user_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

export function setLocalUserId(id: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem("anatom_user_id", id);
}

/**
 * Always returns a string user-id — auto-generates and persists one if none
 * exists yet. This removes the need for `string | null` guards across the app.
 */
export function getLocalUserId(): string {
  if (typeof window === "undefined") return "ssr_placeholder";
  const stored = localStorage.getItem("anatom_user_id");
  if (stored) return stored;
  const fresh = generateUserId();
  localStorage.setItem("anatom_user_id", fresh);
  return fresh;
}
