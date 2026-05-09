"use client";

import { useEffect, useState } from "react";
import { Sparkles, Brain, TrendingUp, Lightbulb, ChevronRight, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { DASH_IMAGES } from "@/lib/dashboardImages";

interface Insight {
  id: string;
  icon: React.ElementType;
  type: "info" | "warning" | "tip";
  headline: string;
  text: string;
}

const defaultInsights: Insight[] = [
  {
    id: "1",
    icon: TrendingUp,
    type: "tip",
    headline: "Start your health journey",
    text: "Upload your first report — blood panel, MRI, X-ray, or CT — to unlock personalized AI insights, trend analysis, and 3D body visualization.",
  },
  {
    id: "2",
    icon: Brain,
    type: "info",
    headline: "Multimodal AI analysis",
    text: "Anatom-AI combines report text, imaging findings, and your health profile to generate a holistic risk assessment and care plan tailored to you.",
  },
  {
    id: "3",
    icon: Lightbulb,
    type: "tip",
    headline: "Profile boosts accuracy",
    text: "A complete Health Profile improves AI recommendation precision by up to 40%. Add your conditions, medications, and vitals to get started.",
  },
  {
    id: "4",
    icon: AlertCircle,
    type: "warning",
    headline: "Regular monitoring matters",
    text: "Uploading reports consistently over time lets NeuroMapper track longitudinal trends — catching early signals before they become serious conditions.",
  },
];

const typeStyles = {
  info: {
    iconBg: "rgba(10,132,255,0.14)",
    iconColor: "#0A84FF",
    badge: "badge-info",
    label: "Info",
    dot: "#0A84FF",
  },
  warning: {
    iconBg: "rgba(255,159,10,0.14)",
    iconColor: "#FF9F0A",
    badge: "badge-warning",
    label: "Note",
    dot: "#FF9F0A",
  },
  tip: {
    iconBg: "rgba(50,215,75,0.14)",
    iconColor: "#32D74B",
    badge: "badge-normal",
    label: "Tip",
    dot: "#32D74B",
  },
};

interface AIInsightsPanelProps {
  insights?: Insight[];
  hasReports?: boolean;
  conditionCount?: number;
}

export function AIInsightsPanel({
  insights = defaultInsights,
  hasReports = false,
  conditionCount = 0,
}: AIInsightsPanelProps) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [fading, setFading] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      setFading(true);
      setTimeout(() => { setActiveIdx((i) => (i + 1) % insights.length); setFading(false); }, 220);
    }, 7000);
    return () => clearInterval(timer);
  }, [insights.length]);

  const goTo = (i: number) => {
    if (i === activeIdx) return;
    setFading(true);
    setTimeout(() => { setActiveIdx(i); setFading(false); }, 200);
  };

  const active = insights[activeIdx];
  const ts = typeStyles[active.type];
  const ActiveIcon = active.icon;

  const smartSuggestions = hasReports
    ? [
        "Schedule a follow-up based on your latest report findings",
        conditionCount > 0
          ? `${conditionCount} active condition${conditionCount > 1 ? "s" : ""} detected — review your care plan`
          : "Your health profile looks clean — keep maintaining your routine",
      ]
    : [];

  return (
    <div
      className="relative overflow-hidden rounded-2xl"
      style={{
        background: "var(--glass-bg)",
        boxShadow: "var(--glass-shadow)",
      }}
    >
      {/* Background image */}
      <div className="absolute inset-y-0 right-0 w-[42%] overflow-hidden pointer-events-none hidden lg:block">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={DASH_IMAGES.aiPanel}
          alt=""
          loading="lazy"
          decoding="async"
          className="absolute inset-0 w-full h-full object-cover"
          style={{ opacity: 0.18 }}
        />
        <div
          className="absolute inset-0"
          style={{ background: "linear-gradient(to right, var(--glass-bg) 0%, rgba(28,28,30,0.7) 50%, rgba(28,28,30,0.2) 100%)" }}
        />
      </div>

      <div className="relative p-5">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="relative shrink-0">
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center"
                style={{ background: "rgba(10,132,255,0.14)" }}
              >
                <Sparkles style={{ width: 17, height: 17, color: "#0A84FF" }} />
              </div>
              <span
                className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 status-pulse"
                style={{ background: "#32D74B", borderColor: "var(--glass-bg)" }}
              />
            </div>
            <div>
              <h3 className="font-semibold text-[14px] tracking-tight" style={{ color: "var(--label-primary)" }}>
                AI Intelligence
              </h3>
              <p className="text-[10px] font-mono" style={{ color: "var(--label-tertiary)" }}>
                Powered by Gemini AI · Live
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full status-pulse" style={{ background: "#32D74B" }} />
            <span className="text-[10px] font-mono font-semibold" style={{ color: "#32D74B" }}>Active</span>
          </div>
        </div>

        {/* Content grid */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto] gap-4">
          {/* Insight card */}
          <div
            className={cn("rounded-xl p-4 transition-opacity duration-200", fading ? "opacity-0" : "opacity-100")}
            style={{
              background: "var(--bg-elevated)",
              border: "1px solid var(--border-default)",
            }}
          >
            <div className="flex items-start gap-3">
              <div
                className="p-2 rounded-xl shrink-0"
                style={{ background: ts.iconBg }}
              >
                <ActiveIcon className="w-4 h-4" style={{ color: ts.iconColor }} />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <span
                    className="text-[9.5px] font-semibold uppercase tracking-widest"
                    style={{ color: "var(--label-secondary)" }}
                  >
                    AI Insight
                  </span>
                  <span className={ts.badge}>{ts.label}</span>
                </div>
                <p className="text-[13px] font-semibold mb-1.5" style={{ color: "var(--label-primary)" }}>{active.headline}</p>
                <p className="text-[12.5px] leading-relaxed" style={{ color: "var(--label-secondary)" }}>
                  {active.text}
                </p>
              </div>
            </div>

            {/* Dot nav */}
            <div className="flex items-center gap-1.5 mt-4">
              {insights.map((_, i) => (
                <button
                  key={i}
                  onClick={() => goTo(i)}
                  className="transition-all duration-300 rounded-full"
                  style={{
                    width: i === activeIdx ? 22 : 6,
                    height: 6,
                    background: i === activeIdx ? "#0A84FF" : "var(--border-default)",
                  }}
                />
              ))}
              <span className="ml-auto text-[10px] font-mono" style={{ color: "var(--label-tertiary)" }}>
                {activeIdx + 1}/{insights.length}
              </span>
            </div>
          </div>

          {/* Smart suggestions */}
          <div className="lg:w-64 flex flex-col gap-2">
            <p
              className="text-[9.5px] font-semibold uppercase tracking-widest flex items-center gap-1.5"
              style={{ color: "var(--label-secondary)" }}
            >
              <Brain className="w-3 h-3" />
              Smart Suggestions
            </p>
            <div className="flex flex-col gap-2 flex-1">
              {(smartSuggestions.length > 0
                ? smartSuggestions
                : [
                    "Complete your health profile for personalized insights",
                    "Upload a report to activate trend analysis",
                    "Connect with CareConnect AI for specialist matching",
                  ]
              ).map((s, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 p-2.5 rounded-xl transition-all duration-200 cursor-default"
                  style={{
                    background: "var(--bg-hover)",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLDivElement).style.background = "var(--bg-active)";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLDivElement).style.background = "var(--bg-hover)";
                  }}
                >
                  <ChevronRight className="w-3 h-3 shrink-0 mt-0.5" style={{ color: "#0A84FF" }} />
                  <p className="text-[12px] leading-snug" style={{ color: "var(--label-secondary)" }}>{s}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
