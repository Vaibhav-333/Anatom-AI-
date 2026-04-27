"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  CheckCircle2,
  AlertTriangle,
  ChevronRight,
  Box,
  Stethoscope,
  FileText,
  Share2,
  Star,
  BadgeCheck,
  Building2,
  Download,
  RotateCcw,
  Brain,
  Sparkles,
  HeartPulse,
} from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { MetricRow } from "@/components/ui/MetricRow";
import { SeverityBadge } from "@/components/ui/StatusBadge";
import { RiskBadge } from "@/components/care-connect/RiskBadge";
import { ConditionTable } from "@/components/care-connect/ConditionTable";
import { TreatmentPanel } from "@/components/care-connect/TreatmentPanel";
import { ShareModal } from "@/components/care-connect/ShareModal";
import { TriageCard } from "@/components/report/TriageCard";
import { KnowledgeGraphPanel } from "@/components/report/KnowledgeGraphPanel";
import { LinkedMedicalText } from "@/components/report/LinkedMedicalText";
import { saveAnalysis, type StoredAnalysis } from "@/lib/analysisStore";
import { resolveOrganKey, conditionToOrgans } from "@/lib/organMap";
import { getLocalUserId, getSeverityConfig } from "@/lib/utils";
import { useLifestyleStore, type LifestylePlanRequest } from "@/lib/lifestyleStore";
import type {
  InterpretResponse,
  TriageResult,
  KnowledgeGraphData,
  PersonalizedInsight,
} from "@/lib/types";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ProbableCondition {
  name: string;
  confidence_pct: number;
  description: string;
}

export interface FinalDiagReport {
  probable_conditions: ProbableCondition[];
  affected_organs: string[];
  risk_level: string;
  red_flags: string[];
  next_steps: string[];
  treatment_suggestions: string[];
  recommended_specialization: string;
  personalized_insights?: PersonalizedInsight[];
  personalized_ai_summary?: string;
  disclaimer: string;
}

export interface RecommendedDoctor {
  id: string;
  name: string;
  specialization: string;
  rating: number;
  review_count: number;
  consultation_fee: number;
  mode: string;
  hospital: string;
  city: string;
  verified: boolean;
  experience_years: number;
}

interface Props {
  report: FinalDiagReport;
  reportId: string;
  initialAnalysis: InterpretResponse;
  recommendedDoctors: RecommendedDoctor[];
  triage?: TriageResult | null;
  knowledgeGraph?: KnowledgeGraphData | null;
  personalizedInsights?: PersonalizedInsight[];
  onReset: () => void;
}

// ─── Mode badge ───────────────────────────────────────────────────────────────

const MODE_LABEL: Record<string, string> = {
  online: "Online",
  offline: "In-Clinic",
  both: "Online + Clinic",
};

// ─── Personalization helpers ──────────────────────────────────────────────────

/**
 * Generate client-side fallback insights when the backend returns an empty array.
 * Always produces at least one insight from the available report data.
 */
function _generateFallbackInsights(report: FinalDiagReport): PersonalizedInsight[] {
  const insights: PersonalizedInsight[] = [];
  const risk = report.risk_level?.toLowerCase() ?? "low";

  // Risk-level insight
  if (risk === "high" || risk === "critical") {
    insights.push({
      factor: "elevated risk level",
      impact: `Your report shows a ${risk} risk — prompt evaluation by a specialist is recommended`,
      severity: "high",
    });
  } else if (risk === "medium" || risk === "moderate") {
    insights.push({
      factor: "moderate risk findings",
      impact: "Your analysis detected moderate risk — a medical consultation within the week is advised",
      severity: "moderate",
    });
  } else {
    insights.push({
      factor: "routine monitoring",
      impact: "No urgent findings detected — continue your regular health check-ups and lifestyle habits",
      severity: "low",
    });
  }

  // Top condition insight
  const top = report.probable_conditions[0];
  if (top) {
    insights.push({
      factor: top.name,
      impact: `${top.name} identified with ${top.confidence_pct}% confidence — discuss with a ${report.recommended_specialization ?? "specialist"}`,
      severity: top.confidence_pct >= 70 ? "high" : top.confidence_pct >= 40 ? "moderate" : "low",
    });
  }

  // Red flag insight
  if (report.red_flags.length > 0) {
    insights.push({
      factor: "red flag detected",
      impact: `${report.red_flags[0]} — make sure to mention this to your doctor`,
      severity: "high",
    });
  }

  return insights.slice(0, 3);
}

/**
 * Compose a one-sentence personalized narrative shown above the insights list.
 */
function _getPersonalizedNarrative(
  name: string,
  report: FinalDiagReport,
  insights: PersonalizedInsight[]
): string {
  const greeting = name ? `${name}, ` : "";
  const risk = report.risk_level?.toLowerCase() ?? "low";
  const topCondition = report.probable_conditions[0]?.name;

  // Lead with the most severe insight if available
  const topHigh = insights.find((i) => i.severity === "high");
  if (topHigh) {
    const impactSentence = topHigh.impact.charAt(0).toUpperCase() + topHigh.impact.slice(1);
    return `${greeting}${impactSentence.endsWith(".") ? impactSentence : impactSentence + "."} Your ${topHigh.factor} is a key contributing factor identified in this analysis.`;
  }

  if (topCondition) {
    const riskWord =
      risk === "high" || risk === "critical"
        ? "elevated"
        : risk === "medium" || risk === "moderate"
        ? "moderate"
        : "low";
    return `${greeting}based on your report, ${topCondition} is the most likely concern with a ${riskWord} overall risk level. Review the personalised details below.`;
  }

  return `${greeting}your medical report has been fully analysed. The insights below are derived from your findings and interview responses.`;
}

/**
 * Generate a multi-paragraph AI summary when the backend has not yet produced
 * a personalized_ai_summary (e.g., old reports or when Gemini was unavailable).
 */
function _generateFallbackSummary(
  name: string,
  report: FinalDiagReport,
  initialAnalysis: InterpretResponse
): string {
  const greeting = name ? `${name}, ` : "";
  const risk = report.risk_level?.toLowerCase() ?? "low";
  const riskWord =
    risk === "high" || risk === "critical"
      ? "elevated"
      : risk === "medium" || risk === "moderate"
      ? "moderate"
      : "low";
  const top = report.probable_conditions[0];
  const urgency =
    risk === "high" || risk === "critical"
      ? "prompt medical attention is strongly recommended"
      : risk === "medium" || risk === "moderate"
      ? "a medical consultation within the next week is advised"
      : "routine monitoring and regular check-ups are sufficient";

  const p1 = top
    ? `${greeting}based on your uploaded medical report, our AI has identified ${top.name} as the most likely finding, with a confidence of ${top.confidence_pct}%. Your overall risk level has been assessed as ${riskWord}, indicating that ${urgency}.`
    : `${greeting}your medical report has been thoroughly analysed by our AI system. ${
        initialAnalysis.findings.length > 0
          ? `${initialAnalysis.findings.length} finding${initialAnalysis.findings.length > 1 ? "s" : ""} were identified.`
          : "No significant findings were detected."
      }`;

  const criticalCount = initialAnalysis.findings.filter((f) => f.severity === "critical").length;
  const borderlineCount = initialAnalysis.findings.filter((f) => f.severity === "borderline").length;
  const p2 = report.affected_organs.length > 0
    ? `Your ${report.affected_organs.slice(0, 2).join(" and ")} ${
        report.affected_organs.length === 1 ? "has" : "have"
      } been flagged as areas requiring attention. ${
        report.red_flags.length > 0
          ? `A notable red flag was identified: ${report.red_flags[0].charAt(0).toUpperCase() + report.red_flags[0].slice(1)}.`
          : "No critical red flags were detected at this time."
      } Out of ${initialAnalysis.findings.length} total findings, ${criticalCount} ${criticalCount === 1 ? "was" : "were"} critical and ${borderlineCount} borderline.`
    : `${criticalCount > 0 ? `${criticalCount} critical finding${criticalCount > 1 ? "s" : ""} ${criticalCount === 1 ? "was" : "were"} identified.` : "No critical findings were detected."} Your ${riskWord} risk profile has been carefully assessed based on your report.`;

  const p3 = report.probable_conditions.length > 1
    ? `In addition to ${top?.name ?? "the primary finding"}, ${report.probable_conditions
        .slice(1, 3)
        .map((c) => `${c.name} (${c.confidence_pct}% confidence)`)
        .join(" and ")} ${report.probable_conditions.slice(1, 3).length === 1 ? "was" : "were"} also considered. These differential diagnoses should be discussed with your specialist for a definitive evaluation.`
    : `Your interview responses and report findings have been combined to produce this analysis. The AI has taken into account the type of report, flagged regions, and any relevant patterns in your findings.`;

  const p4 = `We recommend consulting a ${report.recommended_specialization} for a thorough in-person evaluation. ${
    report.next_steps.length > 0 ? report.next_steps[0] : "Follow the recommended next steps outlined in this report."
  } This AI analysis is for informational purposes only and does not replace professional medical advice.`;

  return [p1, p2, p3, p4].join("\n\n");
}

// ─── Component ────────────────────────────────────────────────────────────────

export function DiagnosticReport({
  report,
  reportId,
  initialAnalysis,
  recommendedDoctors,
  triage,
  knowledgeGraph,
  personalizedInsights,
  onReset,
}: Props) {
  const router = useRouter();
  const [shareOpen, setShareOpen] = useState(false);
  const [profileName, setProfileName] = useState("");
  const { setReportPreload } = useLifestyleStore();

  // Fetch user display name for personalized narrative
  useEffect(() => {
    const userId = getLocalUserId();
    if (!userId) return;
    fetch(`/api/profile/${userId}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => { if (data?.name) setProfileName(data.name); })
      .catch(() => {});
  }, []);

  function handleView3D() {
    // Resolve organ keys from affected_organs list
    const fromOrgans = report.affected_organs
      .map((o) => resolveOrganKey(o))
      .filter((k): k is string => k !== null);
    // Also derive organs from condition names for richer coverage
    const fromConditions = report.probable_conditions.flatMap((c) =>
      conditionToOrgans(c.name)
        .map((o) => resolveOrganKey(o))
        .filter((k): k is string => k !== null)
    );
    const organ_keys = Array.from(new Set([...fromOrgans, ...fromConditions]));

    const worstSeverity = initialAnalysis.findings.some((f) => f.severity === "critical")
      ? "severe"
      : initialAnalysis.findings.some((f) => f.severity === "borderline")
      ? "moderate"
      : "mild";

    // Build per-condition affected organs enriched by the condition→organ map
    const stored: StoredAnalysis = {
      conditions: report.probable_conditions.map((c) => {
        const condOrgans = conditionToOrgans(c.name);
        const mergedOrgans = condOrgans.length > 0 ? condOrgans : report.affected_organs.slice(0, 2);
        return {
          name: c.name,
          confidence: c.confidence_pct / 100,
          affected_organs: mergedOrgans,
          severity: worstSeverity,
          description: c.description,
        };
      }),
      summary: initialAnalysis.summary,
      risk_level: report.risk_level,
      organ_keys,
      source: "ai",
      timestamp: Date.now(),
    };
    saveAnalysis(stored);
    router.push("/viewer");
  }

  function handleFindDoctors() {
    const spec = encodeURIComponent(report.recommended_specialization);
    router.push(`/care-connect/doctors?spec=${spec}`);
  }

  function handleGenerateHealthGuidance() {
    const risk = report.risk_level?.toLowerCase() ?? "low";
    const goal: LifestylePlanRequest["goal"] =
      risk === "critical" || risk === "high"
        ? "recovery"
        : risk === "medium" || risk === "moderate"
        ? "chronic_management"
        : "fitness";
    const activityLevel: LifestylePlanRequest["activity_level"] =
      risk === "critical" ? "sedentary"
      : risk === "high" ? "light"
      : risk === "medium" || risk === "moderate" ? "moderate"
      : "moderate";
    // Infer dietary restrictions from probable conditions
    const restrictions: string[] = [];
    const condNames = report.probable_conditions.map((c) => c.name.toLowerCase());
    if (condNames.some((c) => c.includes("diabetes"))) restrictions.push("Diabetic-friendly");
    if (condNames.some((c) => c.includes("hypertension") || c.includes("heart") || c.includes("cardiac"))) restrictions.push("Low-sodium");
    if (condNames.some((c) => c.includes("kidney") || c.includes("renal"))) restrictions.push("Low-fat");
    const userId = getLocalUserId();
    const req: LifestylePlanRequest = { user_id: userId, goal, dietary_pref: "vegetarian", restrictions, activity_level: activityLevel };
    setReportPreload(req);
    router.push("/lifestyle-planner");
  }

  const stagger = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
  const item = { hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0 } };

  return (
    <>
      <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-4">

        {/* ── Header ─────────────────────────────────────────────── */}
        <motion.div variants={item}>
          <GlassCard className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green/10 border border-green/20">
                <CheckCircle2 className="w-5 h-5 text-green" />
              </div>
              <div>
                <p className="font-semibold text-slate-200">AI Diagnostic Report Ready</p>
                <p className="text-xs text-slate-500 font-mono">ID: {reportId.slice(0, 8)}…</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <RiskBadge level={report.risk_level} size="lg" />
              <button
                onClick={onReset}
                className="p-2 rounded-lg border border-glass-border text-slate-500 hover:text-white hover:border-slate-500 transition-all"
                title="Upload another report"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>
          </GlassCard>
        </motion.div>

        {/* ── AI Triage Card ──────────────────────────────────────── */}
        <motion.div variants={item}>
          <TriageCard triage={triage ?? null} />
        </motion.div>

        {/* ── Metrics Row ─────────────────────────────────────────── */}
        <motion.div variants={item} id="gridlayout" className="grid grid-cols-3 gap-3">
          <GlassCard hover glow="cyan">
            <MetricRow label="Confidence" value={`${Math.round(initialAnalysis.confidence * 100)}%`} color="cyan" />
          </GlassCard>
          <GlassCard hover glow="none">
            <MetricRow label="Findings" value={initialAnalysis.findings.length} color="white" />
          </GlassCard>
          <GlassCard hover glow="amber">
            <MetricRow label="Regions Flagged" value={initialAnalysis.affected_regions.length} color="amber" />
          </GlassCard>
        </motion.div>

        {/* ── AI Analysis Summary ─────────────────────────────────── */}
        <motion.div variants={item}>
          <GlassCard>
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-cyan" />
              <h3 className="section-title text-base">AI Analysis Summary</h3>
            </div>
            {(() => {
              const summaryText =
                report.personalized_ai_summary ||
                _generateFallbackSummary(profileName, report, initialAnalysis);
              const paragraphs = summaryText.split("\n\n").filter(Boolean);
              return (
                <div className="space-y-3">
                  {paragraphs.map((para, i) => (
                    <p key={i} className="text-sm text-slate-300 leading-relaxed">
                      <LinkedMedicalText text={para} />
                    </p>
                  ))}
                </div>
              );
            })()}
            {initialAnalysis.reasoning && (
              <div className="mt-4 p-3 rounded-lg bg-navy-700 border border-glass-border">
                <p className="text-xs text-slate-500 font-medium mb-1.5">WHY THE AI FLAGGED THIS</p>
                <p className="text-xs text-slate-400 leading-relaxed">
                  <LinkedMedicalText text={initialAnalysis.reasoning} />
                </p>
              </div>
            )}
          </GlassCard>
        </motion.div>

        {/* ── Key Findings ────────────────────────────────────────── */}
        {initialAnalysis.findings.length > 0 && (
          <motion.div variants={item}>
            <GlassCard hover glow="cyan">
              <h3 className="section-title text-base mb-4">Key Findings</h3>
              <div className="space-y-2.5">
                {initialAnalysis.findings.map((finding, i) => {
                  const cfg = getSeverityConfig(finding.severity);
                  return (
                    <div key={i} className={`flex items-start gap-3 p-3 rounded-lg border ${cfg.border} ${cfg.bg}`}>
                      <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${cfg.dot}`} />
                      <div className="flex-1">
                        <p className={`text-sm font-medium ${cfg.color}`}>
                          <LinkedMedicalText text={finding.text} />
                        </p>
                        {(finding.value || finding.reference_range) && (
                          <p className="text-xs text-slate-500 font-mono mt-0.5">
                            {finding.value && `${finding.value}${finding.unit ? ` ${finding.unit}` : ""}`}
                            {finding.reference_range && ` · ref: ${finding.reference_range}`}
                          </p>
                        )}
                      </div>
                      <SeverityBadge severity={finding.severity} />
                    </div>
                  );
                })}
              </div>
            </GlassCard>
          </motion.div>
        )}

        {/* ── Probable Conditions ─────────────────────────────────── */}
        <motion.div variants={item}>
          <GlassCard hover glow="cyan">
            <h3 className="section-title text-base mb-4">Probable Conditions</h3>
            <ConditionTable
              conditions={report.probable_conditions.map((c) => ({
                name: c.name,
                confidence_pct: c.confidence_pct,
                description: c.description,
              }))}
            />
          </GlassCard>
        </motion.div>

        {/* ── Affected Organs + Red Flags (2-col) ─────────────────── */}
        <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {report.affected_organs.length > 0 && (
            <GlassCard hover glow="cyan" className="p-5">
              <h3 className="font-semibold text-white text-sm mb-3">Affected Organs</h3>
              <div className="flex flex-wrap gap-2">
                {report.affected_organs.map((organ) => (
                  <span key={organ} className="badge-info capitalize">{organ}</span>
                ))}
              </div>
            </GlassCard>
          )}
          {report.red_flags.length > 0 && (
            <GlassCard hover glow="red" className="p-5 border-red-500/20 bg-red-500/5">
              <h3 className="font-semibold text-red-400 text-sm mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" /> Red Flags
              </h3>
              <ul className="space-y-1.5">
                {report.red_flags.map((f, i) => (
                  <li key={i} className="text-sm text-red-300 flex items-start gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                    <LinkedMedicalText text={f} />
                  </li>
                ))}
              </ul>
            </GlassCard>
          )}
        </motion.div>

        {/* ── Medical Knowledge Graph ─────────────────────────────── */}
        <motion.div variants={item}>
          <KnowledgeGraphPanel
            initialData={knowledgeGraph ?? null}
            conditions={
              knowledgeGraph
                ? undefined
                : report.probable_conditions.length > 0
                ? report.probable_conditions.map((c) => ({
                    name: c.name,
                    confidence_pct: c.confidence_pct,
                  }))
                : // Fallback: use affected organs so the graph is never empty
                  report.affected_organs
                    .filter(Boolean)
                    .map((organ, i) => ({
                      name: organ,
                      confidence_pct: Math.max(40, 75 - i * 8),
                    }))
            }
          />
        </motion.div>

        {/* ── Personalized Insights ───────────────────────────────── */}
        {(() => {
          // Use backend insights, or fall back to client-side computed insights
          const rawInsights = personalizedInsights ?? report.personalized_insights ?? [];
          const insights =
            rawInsights.length > 0 ? rawInsights : _generateFallbackInsights(report);
          const narrative = _getPersonalizedNarrative(profileName, report, insights);
          return (
            <motion.div variants={item}>
              <GlassCard hover glow="cyan">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-4 h-4 rounded-full bg-violet-400/20 border border-violet-400/30 flex items-center justify-center">
                    <span className="text-[8px] text-violet-400 font-bold">P</span>
                  </div>
                  <h3 className="section-title text-base">Personalized Insights</h3>
                </div>
                {/* Personalized narrative sentence */}
                <p className="text-sm text-slate-300 leading-relaxed mb-3 p-3 rounded-lg bg-violet-500/5 border border-violet-500/15">
                  <LinkedMedicalText text={narrative} />
                </p>
                <div className="space-y-2">
                  {insights.map((insight: PersonalizedInsight, i: number) => {
                    const sevColor =
                      insight.severity === "high"
                        ? "text-red-400 bg-red-500/10 border-red-500/20"
                        : insight.severity === "moderate"
                        ? "text-amber-400 bg-amber-500/10 border-amber-500/20"
                        : "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
                    return (
                      <div
                        key={i}
                        className="flex items-start gap-3 p-2.5 rounded-lg bg-navy-700/50 border border-glass-border"
                      >
                        <span className={`text-xs px-2 py-0.5 rounded-full border font-medium shrink-0 ${sevColor}`}>
                          {insight.severity}
                        </span>
                        <div className="flex-1 min-w-0">
                          <span className="text-xs font-medium text-slate-300">
                            <LinkedMedicalText text={insight.factor} />
                          </span>
                          <span className="text-xs text-slate-500"> — </span>
                          <span className="text-xs text-slate-400">
                            <LinkedMedicalText text={insight.impact} />
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </GlassCard>
            </motion.div>
          );
        })()}

        {/* ── Next Steps + Treatment (2-col grid) ─────────────────── */}
        {(report.next_steps.length > 0 || report.treatment_suggestions.length > 0) && (
          <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {report.next_steps.length > 0 && (
              <GlassCard hover glow="green">
                <h3 className="section-title text-base mb-3 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-green" /> Next Steps
                </h3>
                <ol className="space-y-2">
                  {report.next_steps.map((s, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm text-slate-300">
                      <span className="w-5 h-5 rounded-full bg-green/10 border border-green/30 text-green text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                        {i + 1}
                      </span>
                      <LinkedMedicalText text={s} />
                    </li>
                  ))}
                </ol>
              </GlassCard>
            )}
            {report.treatment_suggestions.length > 0 && (
              <GlassCard hover glow="green">
                <TreatmentPanel suggestions={report.treatment_suggestions} />
              </GlassCard>
            )}
          </motion.div>
        )}

        {/* ── Generate Health Guidance CTA ─────────────────────────── */}
        <motion.div variants={item}>
          <div className="group rounded-2xl p-5 bg-gradient-to-r from-cyan/5 via-transparent to-green/5 border border-cyan/20 hover:border-cyan/40 hover:shadow-[0_0_24px_rgba(0,212,255,0.1)] transition-all duration-300 flex items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <HeartPulse className="w-4 h-4 text-cyan" />
                <h3 className="text-sm font-semibold text-white">Generate Health Guidance</h3>
              </div>
              <p className="text-xs text-slate-500">
                Auto-create a personalised diet plan, exercise routine &amp; lifestyle recommendations from this report — no manual input needed.
              </p>
            </div>
            <button
              id="b1a2g3"
              onClick={handleGenerateHealthGuidance}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-cyan text-navy-900 font-semibold text-sm hover:bg-cyan/90 active:scale-95 transition-all shrink-0 shadow-[0_0_12px_rgba(0,212,255,0.3)]"
            >
              <HeartPulse className="w-4 h-4" />
              Get Plan
            </button>
          </div>
        </motion.div>

        {/* ── Specialist Recommendation ───────────────────────────── */}
        <motion.div variants={item}>
          <div className="group bg-cyan/5 border border-cyan/20 hover:border-cyan/35 hover:bg-cyan/8 hover:shadow-[0_0_18px_rgba(0,212,255,0.08)] transition-all duration-200 rounded-2xl p-4 text-center">
            <p className="text-xs text-slate-500 mb-1">Recommended Specialist</p>
            <p className="text-cyan font-semibold text-lg">{report.recommended_specialization}</p>
          </div>
        </motion.div>

        {/* ── Recommended Doctors ─────────────────────────────────── */}
        {recommendedDoctors.length > 0 && (
          <motion.div variants={item}>
            <GlassCard>
              <div className="flex items-center justify-between mb-4">
                <h3 className="section-title text-base">Recommended Doctors</h3>
                <button
                  onClick={handleFindDoctors}
                  className="text-xs text-cyan hover:underline flex items-center gap-1"
                >
                  See all <ChevronRight className="w-3 h-3" />
                </button>
              </div>
              <div className="space-y-3">
                {recommendedDoctors.slice(0, 4).map((doc) => (
                  <a
                    key={doc.id}
                    href={`/care-connect/doctors/${doc.id}`}
                    className="flex items-start gap-3 p-3 rounded-xl border border-glass-border hover:border-cyan/30 hover:bg-cyan/5 transition-all group"
                  >
                    <div className="w-10 h-10 rounded-xl bg-cyan/10 border border-cyan/20 flex items-center justify-center text-sm font-bold text-cyan shrink-0">
                      {doc.name.split(" ").slice(1, 3).map((n) => n[0]).join("")}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <p className="text-sm font-medium text-white truncate">{doc.name}</p>
                        {doc.verified && <BadgeCheck className="w-3.5 h-3.5 text-cyan shrink-0" />}
                      </div>
                      <p className="text-xs text-cyan mt-0.5">{doc.specialization}</p>
                      <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                        <span className="flex items-center gap-0.5">
                          <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
                          {doc.rating.toFixed(1)}
                        </span>
                        <span>·</span>
                        <span className="flex items-center gap-0.5">
                          <Building2 className="w-3 h-3" /> {doc.city}
                        </span>
                        <span>·</span>
                        <span>₹{doc.consultation_fee.toLocaleString()}</span>
                        <span>·</span>
                        <span>{MODE_LABEL[doc.mode] ?? doc.mode}</span>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-cyan transition-colors shrink-0 mt-1" />
                  </a>
                ))}
              </div>
            </GlassCard>
          </motion.div>
        )}

        {/* ── Action Buttons ──────────────────────────────────────── */}
        <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <button
            onClick={handleFindDoctors}
            className="flex flex-col items-center gap-2 p-4 rounded-2xl border border-cyan/20 bg-cyan/5
                       hover:bg-cyan/10 hover:border-cyan/40 transition-all text-cyan"
          >
            <Stethoscope className="w-5 h-5" />
            <span className="text-xs font-medium text-center">Find Doctors</span>
          </button>
          <button
            onClick={handleView3D}
            className="flex flex-col items-center gap-2 p-4 rounded-2xl border border-green/20 bg-green/5
                       hover:bg-green/10 hover:border-green/40 transition-all text-green"
          >
            <Box className="w-5 h-5" />
            <span className="text-xs font-medium text-center">View in 3D</span>
          </button>
          <a
            href={`/api/care-connect/report/${reportId}/pdf`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex flex-col items-center gap-2 p-4 rounded-2xl border border-amber/20 bg-amber/5
                       hover:bg-amber/10 hover:border-amber/40 transition-all text-amber-400"
          >
            <Download className="w-5 h-5" />
            <span className="text-xs font-medium text-center">Download PDF</span>
          </a>
          <button
            onClick={() => setShareOpen(true)}
            className="flex flex-col items-center gap-2 p-4 rounded-2xl border border-purple-400/20 bg-purple-400/5
                       hover:bg-purple-400/10 hover:border-purple-400/40 transition-all text-purple-400"
          >
            <Share2 className="w-5 h-5" />
            <span className="text-xs font-medium text-center">Share Report</span>
          </button>
        </motion.div>

        {/* ── Disclaimer ──────────────────────────────────────────── */}
        <motion.div variants={item}>
          <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4">
            <p className="text-xs text-amber-300/70 text-center leading-relaxed">
              ⚠ {report.disclaimer}
            </p>
          </div>
        </motion.div>

      </motion.div>

      {/* Share modal */}
      {shareOpen && (
        <ShareModal reportId={reportId} onClose={() => setShareOpen(false)} />
      )}
    </>
  );
}
