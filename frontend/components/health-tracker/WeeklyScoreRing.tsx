"use client";
import { motion } from "framer-motion";

interface Props {
  score: number;
  size?: "sm" | "md" | "lg";
  label?: string;
  trend?: string;
}

const SIZE_MAP = { sm: 80, md: 120, lg: 160 };
const STROKE_MAP = { sm: 8, md: 10, lg: 12 };

function scoreColor(score: number) {
  if (score >= 71) return "#00FF88";
  if (score >= 41) return "#FFB800";
  return "#FF3B3B";
}

export default function WeeklyScoreRing({ score, size = "md", label, trend }: Props) {
  const dim = SIZE_MAP[size];
  const stroke = STROKE_MAP[size];
  const r = (dim - stroke * 2) / 2;
  const circumference = 2 * Math.PI * r;
  const filled = circumference * (score / 100);
  const color = scoreColor(score);

  const trendIcon = trend === "improving" ? "↑" : trend === "worsening" ? "↓" : "→";
  const trendColor = trend === "improving" ? "#00FF88" : trend === "worsening" ? "#FF3B3B" : "#8899AA";

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: dim, height: dim }}>
        <svg width={dim} height={dim} className="-rotate-90">
          <circle
            cx={dim / 2} cy={dim / 2} r={r}
            stroke="rgba(255,255,255,0.08)" strokeWidth={stroke} fill="none"
          />
          <motion.circle
            cx={dim / 2} cy={dim / 2} r={r}
            stroke={color} strokeWidth={stroke} fill="none"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: circumference - filled }}
            transition={{ duration: 1.2, ease: "easeOut" }}
            style={{ filter: `drop-shadow(0 0 6px ${color})` }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-bold" style={{ fontSize: dim * 0.22, color }}>{score}</span>
          {trend && (
            <span style={{ fontSize: dim * 0.14, color: trendColor }}>{trendIcon}</span>
          )}
        </div>
      </div>
      {label && <span className="text-xs text-gray-400">{label}</span>}
    </div>
  );
}
