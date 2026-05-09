"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, ShieldAlert, Shield } from "lucide-react";
import { cn } from "@/lib/utils";
import type { RiskLevel } from "@/lib/types";

// Apple Health palette
const riskConfig: Record<
  RiskLevel,
  { label: string; hex: string; tw: string; iconBg: string; pct: number; Icon: React.ElementType }
> = {
  low: {
    label: "Low Risk",
    hex: "#32D74B",
    tw: "text-[#32D74B]",
    iconBg: "rgba(50,215,75,0.14)",
    pct: 18,
    Icon: ShieldCheck,
  },
  moderate: {
    label: "Moderate",
    hex: "#FF9F0A",
    tw: "text-[#FF9F0A]",
    iconBg: "rgba(255,159,10,0.14)",
    pct: 52,
    Icon: ShieldAlert,
  },
  high: {
    label: "High Risk",
    hex: "#FF453A",
    tw: "text-[#FF453A]",
    iconBg: "rgba(255,69,58,0.14)",
    pct: 80,
    Icon: ShieldAlert,
  },
  critical: {
    label: "Critical",
    hex: "#FF453A",
    tw: "text-[#FF453A]",
    iconBg: "rgba(255,69,58,0.14)",
    pct: 95,
    Icon: Shield,
  },
};

function inferRiskFromScore(score: number | null): RiskLevel {
  if (score === null) return "low";
  if (score >= 71) return "low";
  if (score >= 41) return "moderate";
  return "high";
}

interface RiskLevelCardProps {
  riskLevel?: RiskLevel | null;
  healthScore?: number | null;
}

export function RiskLevelCard({ riskLevel, healthScore }: RiskLevelCardProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { const t = setTimeout(() => setMounted(true), 400); return () => clearTimeout(t); }, []);

  const level: RiskLevel = riskLevel ?? inferRiskFromScore(healthScore ?? null);
  const cfg = riskConfig[level];
  const Icon = cfg.Icon;

  return (
    <div className="flex flex-col gap-3 h-full">
      <div className="flex items-start justify-between">
        <div>
          <p className="metric-label">Risk Level</p>
          <p className={cn("text-[20px] font-bold mt-1.5 leading-tight tracking-tight", cfg.tw)}>
            {cfg.label}
          </p>
        </div>
        <div
          className="p-2 rounded-xl shrink-0"
          style={{
            background: cfg.iconBg,
            }}
        >
          <Icon className={cn("w-5 h-5", cfg.tw)} />
        </div>
      </div>

      <div className="mt-auto space-y-2">
        <div
          className="flex justify-between text-[9.5px] font-mono font-semibold px-0.5 tracking-widest"
          style={{ color: "var(--label-tertiary)" }}
        >
          <span>LOW</span>
          <span>MED</span>
          <span>HIGH</span>
        </div>

        {/* Track */}
        <div
          className="relative h-[5px] w-full rounded-full overflow-hidden"
          style={{ background: "var(--bg-elevated)" }}
        >
          {/* Gradient backdrop */}
          <div
            className="absolute inset-0 rounded-full opacity-25"
            style={{ background: "linear-gradient(90deg, #32D74B 0%, #FF9F0A 50%, #FF453A 100%)" }}
          />
          {/* Active fill */}
          <motion.div
            className="h-full rounded-full"
            style={{ background: cfg.hex }}
            initial={{ width: "0%" }}
            animate={{ width: mounted ? `${cfg.pct}%` : "0%" }}
            transition={{ duration: 1.2, ease: [0.4, 0, 0.2, 1] }}
          />
        </div>

        <div className="flex justify-between items-center px-0.5">
          <span className="text-[10px] font-mono" style={{ color: "var(--label-tertiary)" }}>
            {riskLevel ? "from report" : healthScore ? "from score" : "no data"}
          </span>
          <span className={cn("text-[11px] font-mono font-bold", cfg.tw)}>{cfg.pct}%</span>
        </div>
      </div>
    </div>
  );
}
