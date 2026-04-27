"use client";

import { Upload, Brain, Zap, FileText, CheckCircle2 } from "lucide-react";

export interface ActivityItem {
  id: string;
  type: "upload" | "analysis" | "recommendation" | "report";
  title: string;
  subtitle: string;
  time: string;
}

const typeConfig = {
  upload: {
    icon: Upload,
    color: "#0A84FF",
    dotBg: "rgba(10,132,255,0.12)",
  },
  analysis: {
    icon: Brain,
    color: "#BF5AF2",
    dotBg: "rgba(191,90,242,0.12)",
  },
  recommendation: {
    icon: Zap,
    color: "#FF9F0A",
    dotBg: "rgba(255,159,10,0.12)",
  },
  report: {
    icon: FileText,
    color: "#32D74B",
    dotBg: "rgba(50,215,75,0.12)",
  },
};

interface RecentActivityCardProps {
  activities: ActivityItem[];
}

export function RecentActivityCard({ activities }: RecentActivityCardProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <h3 className="section-title text-base">Recent Activity</h3>
        {activities.length > 0 && (
          <span className="badge-info text-[10px]">{activities.length} events</span>
        )}
      </div>

      {activities.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center py-6 text-center">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center mb-3"
            style={{ background: "rgba(255,255,255,0.06)" }}
          >
            <CheckCircle2 className="w-5 h-5" style={{ color: "#636366" }} />
          </div>
          <p className="text-sm" style={{ color: "#8E8E93" }}>No activity yet</p>
          <p className="text-[10px] font-mono mt-1" style={{ color: "#636366" }}>
            events appear after your first upload
          </p>
        </div>
      ) : (
        <div className="relative flex flex-col gap-0.5">
          {/* Vertical connector line */}
          <div
            className="absolute left-[13px] top-6 bottom-6 w-px"
            style={{ background: "rgba(84,84,88,0.35)" }}
          />

          {activities.map((item) => {
            const cfg = typeConfig[item.type];
            const Icon = cfg.icon;
            return (
              <div
                key={item.id}
                className="flex gap-3 items-start px-1 py-2 rounded-lg transition-colors"
                style={{ cursor: "default" }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.02)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.background = "transparent"; }}
              >
                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 z-10 mt-0.5"
                  style={{ background: cfg.dotBg }}
                >
                  <Icon className="w-3 h-3" style={{ color: cfg.color }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium leading-snug truncate" style={{ color: "#FFFFFF" }}>
                    {item.title}
                  </p>
                  <p className="text-[11px] mt-0.5 leading-snug" style={{ color: "#8E8E93" }}>{item.subtitle}</p>
                </div>
                <span className="text-[10px] font-mono shrink-0 mt-0.5" style={{ color: "#636366" }}>
                  {item.time}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
