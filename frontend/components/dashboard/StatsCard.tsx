"use client";

import { FileText, Activity, Clock, ChevronRight } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

interface StatItem {
  label: string;
  value: string;
  unit?: string;
  icon: React.ElementType;
  color: string;
  iconBg: string;
  href?: string;
}

interface StatsCardProps {
  totalReports: number;
  activeConditions: number | string;
  lastUpload: string;
}

export function StatsCard({ totalReports, activeConditions, lastUpload }: StatsCardProps) {
  const stats: StatItem[] = [
    {
      label: "Reports",
      value: String(totalReports),
      unit: "docs",
      icon: FileText,
      color: "#0A84FF",
      iconBg: "rgba(10,132,255,0.14)",
      href: "/history",
    },
    {
      label: "Conditions",
      value: String(activeConditions),
      icon: Activity,
      color: "#FF9F0A",
      iconBg: "rgba(255,159,10,0.14)",
      href: "/profile",
    },
    {
      label: "Last Upload",
      value: lastUpload,
      icon: Clock,
      color: "#8E8E93",
      iconBg: "rgba(255,255,255,0.07)",
      href: "/history",
    },
  ];

  return (
    <div className="flex flex-col h-full">
      <p className="metric-label mb-3">Quick Stats</p>
      <div className="flex flex-col gap-1 flex-1">
        {stats.map((s) => {
          const Icon = s.icon;
          const inner = (
            <div
              className={cn(
                "flex items-center gap-2.5 px-2 py-2 rounded-xl transition-all duration-160",
                s.href ? "hover:bg-white/[0.04] cursor-pointer" : ""
              )}
            >
              <div
                className="w-7 h-7 rounded-[8px] flex items-center justify-center shrink-0"
                style={{ background: s.iconBg }}
              >
                <Icon className="w-3.5 h-3.5" style={{ color: s.color }} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[9.5px] font-mono font-semibold uppercase tracking-widest leading-none"
                   style={{ color: "#636366" }}>
                  {s.label}
                </p>
                <p className="text-[13px] font-mono font-bold mt-0.5 leading-none"
                   style={{ color: s.color }}>
                  {s.value}
                  {s.unit && (
                    <span className="text-[10px] font-normal ml-1" style={{ color: "#636366" }}>
                      {s.unit}
                    </span>
                  )}
                </p>
              </div>
              {s.href && (
                <ChevronRight className="w-3 h-3 shrink-0" style={{ color: "#48484A" }} />
              )}
            </div>
          );

          return s.href ? (
            <Link key={s.label} href={s.href}>{inner}</Link>
          ) : (
            <div key={s.label}>{inner}</div>
          );
        })}
      </div>
    </div>
  );
}
