"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { FileText, ArrowLeft, Box, Sparkles, HeartPulse, MapPin, User, CheckCircle2, Leaf } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { GlassCard } from "@/components/ui/GlassCard";
import { SeverityBadge, RiskBadge } from "@/components/ui/StatusBadge";
import { MetricRow } from "@/components/ui/MetricRow";
import { NeonButton } from "@/components/ui/NeonButton";
import { AlertBox } from "@/components/ui/AlertBox";
import { SectionDivider } from "@/components/ui/PageHeader";
import { GuidancePanel } from "@/components/health/GuidancePanel";
import { TriageCard } from "@/components/report/TriageCard";
import { KnowledgeGraphPanel } from "@/components/report/KnowledgeGraphPanel";
import { LinkedMedicalText } from "@/components/report/LinkedMedicalText";
import { getSeverityConfig, getLocalUserId, formatRelativeDate, getReportTypeLabel } from "@/lib/utils";
import { getSpecialist, getRecommendedSpecialists } from "@/lib/specialistMap";
import { saveSpecialistSearch } from "@/lib/careNavigatorStore";
import { useCareNavigatorStore } from "@/lib/careNavigatorZustand";
import { ConditionTable } from "@/components/care-connect/ConditionTable";
import { TreatmentPanel } from "@/components/care-connect/TreatmentPanel";
import { saveAnalysis, type StoredAnalysis } from "@/lib/analysisStore";
import { resolveOrganKey, conditionToOrgans } from "@/lib/organMap";
import { useLifestyleStore, type LifestylePlanRequest } from "@/lib/lifestyleStore";
import type { ReportDetail, InterpretResponse, AnatomicalMappingItem, PersonalizedInsight } from "@/lib/types";

// Build a deep-link URL to the 3D viewer with camera focus on the most critical region
function buildViewerUrl(interp: InterpretResponse): string {
  const regions = interp.affected_regions.join(",");
  const mapping = interp.anatomical_mapping ?? [];
  // Prefer critical → borderline → first available
  const focus =
    mapping.find((m) => m.severity === "critical") ??
    mapping.find((m) => m.severity === "borderline") ??
    mapping[0] ??
    null;
  const params = new URLSearchParams();
  if (regions) params.set("regions", regions);
  if (focus) params.set("cam", focus.camera_focus.join(","));
  return `/viewer?${params.toString()}`;
}

export default function ResultsPage() {
  const params = useParams();
  const router = useRouter();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generatingGuidance, setGeneratingGuidance] = useState(false);
  const setAnalysisResult = useCareNavigatorStore((s) => s.setAnalysisResult);
  const { setReportPreload } = useLifestyleStore();

  useEffect(() => {
    const userId = getLocalUserId();
    if (!userId || !params.id) { setLoading(false); return; }

    fetch(`/api/history/${userId}/${params.id}`)
      .then((r) => { if (!r.ok) throw new Error("Report not found"); return r.json(); })
      .then((data: import("@/lib/types").ReportDetail) => {
        // If stored report has no triage, compute client-side from risk_level
        if (!data.triage) {
          const risk = data.risk_level ?? data.interpretation?.risk_level ?? "low";
          const r = risk.toLowerCase();
          const level: import("@/lib/types").TriageLevel =
            r === "critical" ? "emergency"
            : r === "high" ? "high"
            : r === "medium" || r === "moderate" ? "moderate"
            : "low";
          const rec: Record<string, string> = {
            emergency: "Seek emergency medical care immediately.",
            high: "See a doctor within 24 hours.",
            moderate: "Schedule a doctor's appointment within the next week.",
            low: "Monitor your symptoms and follow up at your next routine appointment.",
          };
          data.triage = {
            level,
            recommendation: rec[level],
            explanation: `Based on the ${risk} risk level detected in your report analysis.`,
            triggered_by: [`Risk level: ${risk}`],
          };
        }

        // If stored report has no personalized insights, generate client-side fallback
        if (!data.personalized_insights || data.personalized_insights.length === 0) {
          const risk = (data.risk_level ?? "low").toLowerCase();
          const regions = data.interpretation?.affected_regions ?? [];
          const fallback: import("@/lib/types").PersonalizedInsight[] = [];

          if (risk === "high" || risk === "critical") {
            fallback.push({
              factor: "elevated risk level",
              impact: `Your report shows a ${risk} risk level — prompt evaluation by a specialist is recommended`,
              severity: "high",
            });
          } else if (risk === "medium" || risk === "moderate") {
            fallback.push({
              factor: "moderate risk findings",
              impact: "Moderate risk was detected — scheduling a medical consultation within the week is advised",
              severity: "moderate",
            });
          } else {
            fallback.push({
              factor: "routine monitoring",
              impact: "No urgent findings detected — continue regular health check-ups and monitoring",
              severity: "low",
            });
          }

          if (regions.length > 0) {
            fallback.push({
              factor: regions[0],
              impact: `${regions[0]} was identified as an area of concern — discuss this finding with your doctor`,
              severity: risk === "high" || risk === "critical" ? "high" : "moderate",
            });
          }

          if (fallback.length > 0) data.personalized_insights = fallback;
        }

        return data;
      })
      .then(setReport)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [params.id]);

  // Organ-mapped 3D viewer — highlights the correct body parts from this report
  function handleView3D() {
    if (!report) return;
    const interp = report.interpretation;
    const diagData = report.diagnosis_data;

    // Resolve organ keys from affected regions
    const fromRegions = interp.affected_regions
      .map((r) => resolveOrganKey(r))
      .filter((k): k is string => k !== null);
    // Resolve organ keys from condition names
    const fromConditions = (diagData?.probable_conditions ?? []).flatMap((c) =>
      conditionToOrgans(c.name)
        .map((o) => resolveOrganKey(o))
        .filter((k): k is string => k !== null)
    );
    // Also from affected_organs field if available
    const fromOrgans = (diagData?.affected_organs ?? [])
      .map((o) => resolveOrganKey(o))
      .filter((k): k is string => k !== null);

    const organ_keys = Array.from(new Set([...fromRegions, ...fromConditions, ...fromOrgans]));
    const risk = diagData?.risk_level ?? report.risk_level ?? "low";
    const worstSeverity = interp.findings.some((f) => f.severity === "critical")
      ? "severe"
      : interp.findings.some((f) => f.severity === "borderline")
      ? "moderate"
      : "mild";

    const stored: StoredAnalysis = {
      conditions: (diagData?.probable_conditions ?? interp.affected_regions.map((r) => ({
        name: r, confidence_pct: 70, description: "",
      }))).map((c: { name: string; confidence_pct: number; description: string }) => {
        const condOrgans = conditionToOrgans(c.name);
        return {
          name: c.name,
          confidence: c.confidence_pct / 100,
          affected_organs: condOrgans.length > 0 ? condOrgans : (diagData?.affected_organs ?? interp.affected_regions).slice(0, 2),
          severity: worstSeverity,
          description: c.description ?? "",
        };
      }),
      summary: interp.summary,
      risk_level: risk,
      organ_keys: organ_keys.length > 0 ? organ_keys : ["brain"],
      source: "ai",
      timestamp: Date.now(),
    };
    saveAnalysis(stored);
    router.push("/viewer");
  }

  const handleGenerateGuidance = async () => {
    const userId = getLocalUserId();
    if (!userId || !report) return;
    setGeneratingGuidance(true);
    try {
      const res = await fetch("/api/guidance", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ report_id: report.id, user_id: userId }),
      });
      if (!res.ok) throw new Error("Failed to generate guidance");
      const guidance = await res.json();
      setReport((prev) => prev ? { ...prev, guidance } : prev);
    } catch {
      // silently fail — AlertBox shown in UI
    } finally {
      setGeneratingGuidance(false);
    }
  };

  function handleGenerateHealthGuidance() {
    if (!report) return;
    const risk = (report.diagnosis_data?.risk_level ?? report.risk_level ?? "low").toLowerCase();
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
    // Infer dietary restrictions from conditions
    const restrictions: string[] = [];
    const condNames = (report.diagnosis_data?.probable_conditions ?? []).map((c) => c.name.toLowerCase());
    if (condNames.some((c) => c.includes("diabetes"))) restrictions.push("Diabetic-friendly");
    if (condNames.some((c) => c.includes("hypertension") || c.includes("heart") || c.includes("cardiac"))) restrictions.push("Low-sodium");
    if (condNames.some((c) => c.includes("kidney") || c.includes("renal"))) restrictions.push("Low-fat");
    const userId = getLocalUserId();
    const req: LifestylePlanRequest = { user_id: userId, goal, dietary_pref: "vegetarian", restrictions, activity_level: activityLevel };
    setReportPreload(req);
    router.push("/lifestyle-planner");
  }

  if (loading) return (
    <div className="flex items-center justify-center py-20">
      <div className="flex items-center gap-3 text-slate-500">
        <div className="w-5 h-5 border-2 border-cyan/30 border-t-cyan rounded-full animate-spin" />
        <span>Loading report...</span>
      </div>
    </div>
  );

  if (error || !report) return (
    <div className="max-w-2xl mx-auto">
      <AlertBox variant="error">{error ?? "Report not found."}</AlertBox>
      <Link href="/history" className="inline-flex items-center gap-2 mt-4 text-sm text-cyan hover:underline">
        <ArrowLeft className="w-4 h-4" /> Back to History
      </Link>
    </div>
  );

  const interpretation = report.interpretation;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-4xl mx-auto space-y-6"
    >
      <PageHeader
        title={getReportTypeLabel(report.report_type)}
        subtitle={`Uploaded ${formatRelativeDate(report.upload_date)} · ${report.file_name}`}
        icon={<FileText className="w-5 h-5" />}
        badge={<RiskBadge level={report.risk_level} />}
        actions={
          <div className="flex gap-2">
            {(interpretation.affected_regions.length > 0 || report.diagnosis_data?.probable_conditions?.length) && (
              <span id="3dviewbtn">
                <NeonButton
                  variant="cyan"
                  size="sm"
                  icon={<Box className="w-3.5 h-3.5" />}
                  onClick={handleView3D}
                >
                  Visualize in 3D
                </NeonButton>
              </span>
            )}
            <Link href="/history">
              <NeonButton variant="ghost" size="sm" icon={<ArrowLeft className="w-3.5 h-3.5" />}>Back</NeonButton>
            </Link>
          </div>
        }
      />

      {/* ── AI Triage Card ─────────────────────────────────────────── */}
      <TriageCard triage={report.triage} />

      {/* Metrics row */}
      <div id="gridlayout" className="grid grid-cols-3 gap-4">
        <GlassCard hover glow="cyan">
          <MetricRow label="Confidence" value={`${Math.round(interpretation.confidence * 100)}%`} color="cyan" />
        </GlassCard>
        <GlassCard hover glow="none">
          <MetricRow label="Findings" value={interpretation.findings.length} color="white" />
        </GlassCard>
        <GlassCard hover glow="amber">
          <MetricRow label="Regions Flagged" value={interpretation.affected_regions.length} color="amber" />
        </GlassCard>
      </div>

      {/* Summary */}
      <GlassCard>
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-4 h-4 text-cyan" />
          <h3 className="section-title text-base">AI Analysis Summary</h3>
        </div>
        {report.diagnosis_data?.personalized_ai_summary ? (
          <div className="space-y-3">
            {report.diagnosis_data.personalized_ai_summary
              .split("\n\n")
              .filter(Boolean)
              .map((para, i) => (
                <p key={i} className="text-sm text-slate-300 leading-relaxed">
                  <LinkedMedicalText text={para} />
                </p>
              ))}
          </div>
        ) : (
          <p className="text-sm text-slate-300 leading-relaxed">
            <LinkedMedicalText text={interpretation.summary} />
          </p>
        )}
        {interpretation.reasoning && (
          <div className="mt-4 p-3 rounded-lg bg-navy-700 border border-glass-border">
            <p className="text-xs text-slate-500 font-medium mb-1.5">WHY THE AI FLAGGED THIS</p>
            <p className="text-xs text-slate-400 leading-relaxed">
              <LinkedMedicalText text={interpretation.reasoning} />
            </p>
          </div>
        )}
      </GlassCard>

      {/* Findings */}
      {interpretation.findings.length > 0 && (
        <GlassCard hover glow="cyan">
          <h3 className="section-title text-base mb-4">Key Findings</h3>
          <div className="space-y-3">
            {interpretation.findings.map((finding, i) => {
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
      )}

      {/* ── Probable Conditions (from finalized diagnosis) ──────── */}
      {report.diagnosis_data?.probable_conditions && report.diagnosis_data.probable_conditions.length > 0 && (
        <GlassCard hover glow="cyan">
          <h3 className="section-title text-base mb-4">Probable Conditions</h3>
          <ConditionTable
            conditions={report.diagnosis_data.probable_conditions.map((c) => ({
              name: c.name,
              confidence_pct: c.confidence_pct,
              description: c.description,
            }))}
          />
        </GlassCard>
      )}

      {/* ── Next Steps + Treatment (2-col grid) ─────────────────── */}
      {((report.diagnosis_data?.next_steps?.length ?? 0) > 0 || (report.diagnosis_data?.treatment_suggestions?.length ?? 0) > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {report.diagnosis_data?.next_steps && report.diagnosis_data.next_steps.length > 0 && (
            <GlassCard hover glow="green">
              <h3 className="section-title text-base mb-3 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-400" /> Next Steps
              </h3>
              <ol className="space-y-2">
                {report.diagnosis_data.next_steps.map((s, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-slate-300">
                    <span className="w-5 h-5 rounded-full bg-green-500/10 border border-green-500/30 text-green-400 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    <LinkedMedicalText text={s} />
                  </li>
                ))}
              </ol>
            </GlassCard>
          )}
          {report.diagnosis_data?.treatment_suggestions && report.diagnosis_data.treatment_suggestions.length > 0 && (
            <GlassCard hover glow="green">
              <TreatmentPanel suggestions={report.diagnosis_data.treatment_suggestions} />
            </GlassCard>
          )}
        </div>
      )}

      {/* ── Medical Knowledge Graph ─────────────────────────────── */}
      <KnowledgeGraphPanel
        initialData={report.knowledge_graph}
        conditions={
          report.knowledge_graph
            ? undefined
            : report.diagnosis_data?.probable_conditions?.length
            ? report.diagnosis_data.probable_conditions.map((c) => ({
                name: c.name,
                confidence_pct: c.confidence_pct,
              }))
            : interpretation.affected_regions.length > 0
            ? interpretation.affected_regions.map((r, i) => ({
                name: r,
                confidence_pct: 80 - i * 10,
              }))
            : undefined
        }
      />

      {/* ── Personalized Insights ───────────────────────────────── */}
      {report.personalized_insights && report.personalized_insights.length > 0 && (
        <GlassCard hover glow="cyan">
          <div className="flex items-center gap-2 mb-3">
            <User className="w-4 h-4 text-violet-400" />
            <h3 className="section-title text-base">Personalized Insights</h3>
          </div>
          {/* Personalized narrative derived from the top insight */}
          {(() => {
            const top =
              report.personalized_insights!.find((i) => i.severity === "high") ??
              report.personalized_insights![0];
            const risk = report.risk_level?.toLowerCase() ?? "low";
            const riskWord =
              risk === "high" || risk === "critical"
                ? "elevated"
                : risk === "medium" || risk === "moderate"
                ? "moderate"
                : "low";
            const sentence = top
              ? `Based on your report analysis, your risk is ${riskWord} — ${top.impact.charAt(0).toLowerCase() + top.impact.slice(1)}${top.impact.endsWith(".") ? "" : "."} This is driven by your ${top.factor}.`
              : `Your report has been analysed. The insights below are based on your report findings.`;
            return (
              <p className="text-sm text-slate-300 leading-relaxed mb-3 p-3 rounded-lg bg-violet-500/5 border border-violet-500/15">
                <LinkedMedicalText text={sentence} />
              </p>
            );
          })()}
          <div className="space-y-2">
            {report.personalized_insights.map((insight: PersonalizedInsight, i: number) => {
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
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full border font-medium shrink-0 ${sevColor}`}
                  >
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
      )}

      {/* Health Guidance — full panel or generate button */}
      {report.guidance ? (
        <GuidancePanel guidance={report.guidance} riskLevel={report.risk_level} reportId={report.id} />
      ) : (
        <GlassCard>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="section-title text-base">Health Guidance</h3>
              <p className="text-xs text-slate-500 mt-1">
                Generate personalized nutrition, exercise, and red-flag guidance powered by Gemini AI.
              </p>
            </div>
            <NeonButton
              variant="cyan"
              size="sm"
              icon={<HeartPulse className="w-3.5 h-3.5" />}
              onClick={handleGenerateHealthGuidance}
            >
              Generate Health Guidance
            </NeonButton>
          </div>
        </GlassCard>
      )}

      {/* Find Specialists Near Me */}
      {interpretation.affected_regions.length > 0 && (
        <GlassCard>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="section-title text-base">Find Specialist Care</h3>
              <p className="text-xs text-slate-500 mt-1">
                Locate nearby specialists relevant to your analysis results.
              </p>
            </div>
            <NeonButton
              variant="green"
              size="sm"
              icon={<MapPin className="w-3.5 h-3.5" />}
              onClick={() => {
                // Collect ALL detected conditions for multi-specialist support
                const conditions = [
                  ...interpretation.findings.map((f) => f.text),
                  ...interpretation.affected_regions,
                ].filter(Boolean);
                const primaryCondition = conditions[0] ?? "";
                const primarySpecialist = getSpecialist(primaryCondition);
                const recommendations = getRecommendedSpecialists(conditions);

                // Zustand (survives client-side navigation)
                setAnalysisResult(conditions, recommendations);
                // sessionStorage (survives hard reload)
                saveSpecialistSearch({ specialist: primarySpecialist, condition: primaryCondition });

                router.push("/care-navigator");
              }}
            >
              Find Specialists Near Me
            </NeonButton>
          </div>
        </GlassCard>
      )}

      <AlertBox variant="info">
        {interpretation.findings.length > 0
          ? "One or more findings were flagged. This is AI-generated analysis only — not a medical diagnosis."
          : "This analysis is for informational purposes only and does not constitute medical advice."}
      </AlertBox>
    </motion.div>
  );
}
