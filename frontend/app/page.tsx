"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, type Variants } from "framer-motion";
import {
  Upload,
  Box,
  FileText,
  ArrowRight,
  Brain,
  Stethoscope,
  Activity,
  MapPin,
} from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { AlertBox } from "@/components/ui/AlertBox";
import { HealthScoreCard } from "@/components/dashboard/HealthScoreCard";
import { RiskLevelCard } from "@/components/dashboard/RiskLevelCard";
import { RecoveryTrendCard } from "@/components/dashboard/RecoveryTrendCard";
import { StatsCard } from "@/components/dashboard/StatsCard";
import { RecentActivityCard } from "@/components/dashboard/RecentActivityCard";
import { AIInsightsPanel } from "@/components/dashboard/AIInsightsPanel";
import { EmptyReportsState } from "@/components/dashboard/EmptyReportsState";
import { getLocalUserId } from "@/lib/utils";
import { DASH_IMAGES } from "@/lib/dashboardImages";
import type { ScoreHistoryPoint } from "@/lib/types";

// ── Quick actions ─────────────────────────────────────────────────────────────

const quickActions = [
  {
    title: "Upload Report",
    description: "PDF, X-ray, blood report, MRI",
    href: "/upload",
    icon: Upload,
    accent: "#0A84FF",
    img: DASH_IMAGES.actions.upload,
  },
  {
    title: "3D Body Viewer",
    description: "Visualize affected regions",
    href: "/viewer",
    icon: Box,
    accent: "#32D74B",
    img: DASH_IMAGES.actions.viewer,
  },
  {
    title: "Health Profile",
    description: "Update your personal data",
    href: "/profile",
    icon: FileText,
    accent: "#FF9F0A",
    img: DASH_IMAGES.actions.profile,
  },
  {
    title: "CareConnect AI",
    description: "AI reports + doctor matching",
    href: "/care-connect",
    icon: Stethoscope,
    accent: "#BF5AF2",
    img: DASH_IMAGES.actions.careConnect,
  },
  {
    title: "Health Tracker",
    description: "Symptoms & medications log",
    href: "/health-tracker",
    icon: Activity,
    accent: "#0A84FF",
    img: DASH_IMAGES.actions.healthTracker,
  },
  {
    title: "Care Navigator",
    description: "Find nearby specialists",
    href: "/care-navigator",
    icon: MapPin,
    accent: "#32D74B",
    img: DASH_IMAGES.actions.careNavigator,
  },
];

// ── Framer variants ────────────────────────────────────────────────────────────

const container: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.07 } },
};

const itemAnim: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.42, ease: "easeOut" } },
};

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [userId, setUserId] = useState<string | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [healthScore, setHealthScore] = useState<number | null>(null);
  const [bodyAge, setBodyAge] = useState<number | undefined>(undefined);
  const [scoreHistory, setScoreHistory] = useState<ScoreHistoryPoint[]>([]);
  const [conditionCount, setConditionCount] = useState(0);

  useEffect(() => {
    const uid = getLocalUserId();
    setUserId(uid);

    fetch("/api/health")
      .then((r) => { if (r.ok) setBackendOnline(true); else setBackendOnline(false); })
      .catch(() => setBackendOnline(false));

    if (uid) {
      fetch(`/api/profile/${uid}`)
        .then((r) => (r.ok ? r.json() : null))
        .then((profile) => {
          if (profile) {
            setHealthScore(profile.health_score ?? null);
            setBodyAge(profile.metabolic_age);
            setConditionCount(profile.conditions?.length ?? 0);
          }
        })
        .catch(() => {});

      fetch(`/api/profile/${uid}/scores`)
        .then((r) => (r.ok ? r.json() : []))
        .then((data: ScoreHistoryPoint[]) => setScoreHistory(data))
        .catch(() => {});
    }
  }, []);

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="max-w-6xl mx-auto space-y-5"
    >
      {/* ── Hero header ──────────────────────────────────────────────────── */}
      <motion.div variants={itemAnim}>
        <div
          className="relative rounded-2xl overflow-hidden"
          style={{
            background: "#1C1C1E",
            border: "1px solid rgba(255,255,255,0.08)",
            boxShadow: "0 2px 16px rgba(0,0,0,0.45), inset 0 0.5px 0 rgba(255,255,255,0.07)",
          }}
        >
          {/* Hero background image */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={DASH_IMAGES.hero}
            alt=""
            loading="eager"
            decoding="async"
            aria-hidden
            className="absolute inset-0 w-full h-full object-cover pointer-events-none select-none"
            style={{ opacity: 0.22, objectPosition: "center 30%" }}
          />
          {/* Vignette */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background: "linear-gradient(90deg, rgba(28,28,30,0.75) 0%, rgba(28,28,30,0) 65%)",
            }}
          />
          {/* Bottom shimmer line */}
          <div
            className="absolute bottom-0 left-0 right-0 h-px pointer-events-none"
            style={{
              background: "linear-gradient(90deg, transparent, rgba(10,132,255,0.15), transparent)",
            }}
          />

          <div className="relative">
            <PageHeader
              title="Dashboard"
              subtitle="Welcome to Anatom-AI — your personal medical intelligence platform"
              icon={<Brain className="w-5 h-5" />}
              badge={
                backendOnline !== null ? (
                  <StatusBadge
                    status={backendOnline ? "online" : "offline"}
                    label={backendOnline ? "API Online" : "API Offline"}
                  />
                ) : undefined
              }
            />
          </div>
        </div>
      </motion.div>

      {/* ── Profile alert ──────────────────────────────────────────────── */}
      {!userId && (
        <motion.div variants={itemAnim}>
          <AlertBox variant="info" title="Set up your health profile">
            Create your profile to get personalized analysis and accurate health scoring.{" "}
            <Link href="/profile" className="underline-offset-2 hover:underline" style={{ color: "#0A84FF" }}>
              Get started →
            </Link>
          </AlertBox>
        </motion.div>
      )}

      {/* ── Primary metrics row ────────────────────────────────────────── */}
      <motion.div variants={itemAnim} className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <GlassCard hover glow="cyan">
          <HealthScoreCard score={healthScore} history={scoreHistory} bodyAge={bodyAge} />
        </GlassCard>

        <GlassCard hover glow="green">
          <RiskLevelCard healthScore={healthScore} />
        </GlassCard>

        <GlassCard hover glow="cyan">
          <RecoveryTrendCard history={scoreHistory} />
        </GlassCard>

        <GlassCard hover glow="amber">
          <StatsCard
            totalReports={0}
            activeConditions={conditionCount || "—"}
            lastUpload="None"
          />
        </GlassCard>
      </motion.div>

      {/* ── AI Insights Panel ──────────────────────────────────────────── */}
      <motion.div variants={itemAnim}>
        <AIInsightsPanel hasReports={false} conditionCount={conditionCount} />
      </motion.div>

      {/* ── Quick Actions ──────────────────────────────────────────────── */}
      <motion.div variants={itemAnim}>
        <div className="flex items-center gap-3 mb-4">
          <h2 className="section-title">Quick Actions</h2>
          <div
            className="flex-1 h-px"
            style={{
              background: "linear-gradient(to right, rgba(255,255,255,0.08), transparent)",
            }}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {quickActions.map((action) => {
            const Icon = action.icon;
            return (
              <Link key={action.href} href={action.href}>
                <motion.div
                  whileHover={{ scale: 1.012, y: -2 }}
                  whileTap={{ scale: 0.988 }}
                  className="relative flex items-start gap-4 overflow-hidden cursor-pointer group"
                  style={{
                    background: "#1C1C1E",
                    border: `1px solid rgba(255,255,255,0.08)`,
                    borderRadius: 16,
                    padding: "16px 18px",
                    boxShadow: "0 2px 12px rgba(0,0,0,0.35), inset 0 0.5px 0 rgba(255,255,255,0.06)",
                    transition: "border-color 0.2s, box-shadow 0.2s, background 0.2s",
                  }}
                  onMouseEnter={(e) => {
                    const el = e.currentTarget as HTMLDivElement;
                    el.style.borderColor = "rgba(84,84,88,0.35)";
                    el.style.background = "#2C2C2E";
                    el.style.boxShadow = `0 4px 20px rgba(0,0,0,0.45), inset 0 0.5px 0 rgba(255,255,255,0.07)`;
                  }}
                  onMouseLeave={(e) => {
                    const el = e.currentTarget as HTMLDivElement;
                    el.style.borderColor = "rgba(255,255,255,0.08)";
                    el.style.background = "#1C1C1E";

                    el.style.boxShadow = "0 2px 12px rgba(0,0,0,0.35), inset 0 0.5px 0 rgba(255,255,255,0.06)";
                  }}
                >
                  {/* Per-card background image */}
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={action.img}
                    alt=""
                    loading="lazy"
                    decoding="async"
                    aria-hidden
                    className="absolute right-0 top-0 bottom-0 w-28 h-full object-cover pointer-events-none select-none transition-transform duration-500 group-hover:scale-105"
                    style={{ opacity: 0.18 }}
                  />
                  {/* Fade mask */}
                  <div
                    className="absolute right-0 top-0 bottom-0 w-28 pointer-events-none"
                    style={{
                      background:
                        "linear-gradient(to right, #1C1C1E 0%, rgba(28,28,30,0.6) 55%, rgba(28,28,30,0.12) 100%)",
                    }}
                  />

                  {/* Icon */}
                  <div
                    className="relative z-10 p-2.5 rounded-xl shrink-0 transition-transform duration-200 group-hover:scale-110"
                    style={{
                      background: `${action.accent}16`,
                      border: `1px solid ${action.accent}28`,
                    }}
                  >
                    <Icon className="w-5 h-5" style={{ color: action.accent }} />
                  </div>

                  {/* Text */}
                  <div className="relative z-10 flex-1 min-w-0">
                    <p className="font-semibold text-[13px]" style={{ color: action.accent }}>
                      {action.title}
                    </p>
                    <p className="text-[11.5px] mt-0.5 leading-snug" style={{ color: "#8E8E93" }}>
                      {action.description}
                    </p>
                  </div>

                  {/* Arrow */}
                  <ArrowRight
                    className="relative z-10 w-4 h-4 shrink-0 mt-0.5 transition-all duration-200 group-hover:translate-x-0.5"
                    style={{ color: "#636366" }}
                  />
                </motion.div>
              </Link>
            );
          })}
        </div>
      </motion.div>

      {/* ── Overview ──────────────────────────────────────────────────── */}
      <motion.div variants={itemAnim}>
        <div className="flex items-center gap-3 mb-4">
          <h2 className="section-title">Overview</h2>
          <div
            className="flex-1 h-px"
            style={{
              background: "linear-gradient(to right, rgba(255,255,255,0.08), transparent)",
            }}
          />
        </div>

        {/* Overview banner */}
        <div
          className="relative rounded-2xl overflow-hidden h-28 mb-4"
          style={{
            background: "#1C1C1E",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={DASH_IMAGES.hero}
            alt=""
            loading="lazy"
            decoding="async"
            aria-hidden
            className="absolute inset-0 w-full h-full object-cover pointer-events-none select-none"
            style={{ opacity: 0.22, objectPosition: "center 30%" }}
          />
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background: "linear-gradient(to right, rgba(28,28,30,0.92) 0%, rgba(28,28,30,0.55) 55%, rgba(28,28,30,0.18) 100%)",
            }}
          />
          <div
            className="absolute bottom-0 left-0 right-0 h-px pointer-events-none"
            style={{
              background: "linear-gradient(90deg, transparent, rgba(10,132,255,0.18), transparent)",
            }}
          />
          <div className="relative h-full flex items-center px-6">
            <div>
              <p
                className="text-[10px] font-semibold uppercase tracking-widest mb-1"
                style={{ color: "#0A84FF" }}
              >
                Health Overview
              </p>
              <h3 className="text-white font-bold text-[15px] tracking-tight">
                Activity &amp; Recent Reports
              </h3>
              <p className="text-[12.5px] mt-0.5" style={{ color: "#8E8E93" }}>
                Your recent health activity and uploaded reports at a glance.
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <GlassCard>
            <RecentActivityCard activities={[]} />
          </GlassCard>

          <GlassCard>
            <div className="flex items-center justify-between mb-1">
              <h3 className="section-title text-[14px]">Recent Reports</h3>
              <Link
                href="/history"
                className="text-[12px] transition-colors"
                style={{ color: "#0A84FF" }}
                onMouseEnter={(e) => ((e.target as HTMLElement).style.textDecoration = "underline")}
                onMouseLeave={(e) => ((e.target as HTMLElement).style.textDecoration = "none")}
              >
                View all
              </Link>
            </div>
            <EmptyReportsState />
          </GlassCard>
        </div>
      </motion.div>

      {/* ── Footer disclaimer ─────────────────────────────────────────── */}
      <motion.div variants={itemAnim}>
        <div
          className="h-px w-full mb-4"
          style={{
            background: "linear-gradient(to right, transparent, rgba(255,255,255,0.07), transparent)",
          }}
        />
        <p
          className="text-[10.5px] text-center font-mono leading-relaxed"
          style={{ color: "#636366" }}
        >
          ANATOM-AI is a wellness tool, not a regulated medical device. All AI outputs are for
          informational purposes only. Always consult a qualified healthcare professional.
        </p>
      </motion.div>
    </motion.div>
  );
}
