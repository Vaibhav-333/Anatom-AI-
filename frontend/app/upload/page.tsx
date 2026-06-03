"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  FileText,
  Image as ImageIcon,
  X,
  Sparkles,
  Brain,
  Loader2,
  ChevronRight,
  AlertCircle,
} from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageHero } from "@/components/ui/PageHero";
import { PAGE_IMAGES } from "@/lib/pageImages";
import { GlassCard } from "@/components/ui/GlassCard";
import { NeonButton } from "@/components/ui/NeonButton";
import { AlertBox } from "@/components/ui/AlertBox";
import { SeverityBadge } from "@/components/ui/StatusBadge";
import { getSeverityConfig, getLocalUserId, getReportTypeLabel } from "@/lib/utils";
import { DiagnosticChat, type QAEntry } from "@/components/upload/DiagnosticChat";
import {
  DiagnosticReport,
  type FinalDiagReport,
  type RecommendedDoctor,
} from "@/components/upload/DiagnosticReport";
import type {
  InterpretResponse,
  InterpretMode,
  TriageResult,
  KnowledgeGraphData,
  PersonalizedInsight,
} from "@/lib/types";
import { useNotificationStore } from "@/lib/notificationStore";

// ─── Constants ────────────────────────────────────────────────────────────────

const ACCEPTED_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/jpg",
  "image/png",
  "image/webp",
];

type FlowStep = "idle" | "uploading" | "initial_result" | "chatting" | "generating" | "report";

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function UploadPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const addNotification = useNotificationStore((s) => s.addNotification);

  // Backend warm-up state
  // "warming" → ping in flight  |  "ready" → server responded  |  "error" → unreachable
  const [backendStatus, setBackendStatus] = useState<"warming" | "ready" | "error">("warming");

  // Silently ping /health on mount so Railway wakes up before the user clicks Analyze.
  // No retry loop — one ping is enough to start the cold-start sequence.
  useEffect(() => {
    let cancelled = false;
    async function wake() {
      try {
        const res = await fetch("/api/health", { method: "GET" });
        if (!cancelled) setBackendStatus(res.ok ? "ready" : "error");
      } catch {
        if (!cancelled) setBackendStatus("error");
      }
    }
    wake();
    return () => { cancelled = true; };
  }, []);

  // Upload state
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [mode, setMode] = useState<InterpretMode>("simple");

  // Flow state
  const [step, setStep] = useState<FlowStep>("idle");
  const [error, setError] = useState<string | null>(null);
  const [initialAnalysis, setInitialAnalysis] = useState<InterpretResponse | null>(null);
  const [finalReport, setFinalReport] = useState<FinalDiagReport | null>(null);
  const [reportId, setReportId] = useState<string | null>(null);
  const [recommendedDoctors, setRecommendedDoctors] = useState<RecommendedDoctor[]>([]);
  const [triage, setTriage] = useState<TriageResult | null>(null);
  const [knowledgeGraph, setKnowledgeGraph] = useState<KnowledgeGraphData | null>(null);
  const [personalizedInsights, setPersonalizedInsights] = useState<PersonalizedInsight[]>([]);

  // ── File handlers ──────────────────────────────────────────────────────────

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped && ACCEPTED_TYPES.includes(dropped.type)) {
      setFile(dropped);
      setError(null);
    } else {
      setError("Please upload a PDF or image (JPG, PNG, WebP).");
    }
  }, []);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) { setFile(f); setError(null); }
  }

  function resetAll() {
    setFile(null);
    setStep("idle");
    setError(null);
    setInitialAnalysis(null);
    setFinalReport(null);
    setReportId(null);
    setRecommendedDoctors([]);
    setTriage(null);
    setKnowledgeGraph(null);
    setPersonalizedInsights([]);
    if (inputRef.current) inputRef.current.value = "";
  }

  // ── STEP 1: Upload + initial analysis ─────────────────────────────────────

  async function handleAnalyze() {
    if (!file) return;
    const userId = getLocalUserId() ?? "anonymous";
    setStep("uploading");
    setError(null);

    const form = new FormData();
    form.append("file", file);
    form.append("user_id", userId);
    form.append("mode", mode);

    try {
      const res = await fetch("/api/interpret", { method: "POST", body: form });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `Server error ${res.status}`);
      }
      const data: InterpretResponse = await res.json();
      setInitialAnalysis(data);
      setStep("initial_result");
      addNotification(
        "report_analyzed",
        "Report Analyzed",
        `${data.findings?.length ?? 0} finding(s) detected. Review your initial analysis.`
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Analysis failed.");
      setStep("idle");
    }
  }

  // ── STEP 2 → STEP 3: Start chat ───────────────────────────────────────────

  function startChat() {
    setStep("chatting");
  }

  // ── Client-side triage fallback (always produces a result) ───────────────

  function _clientTriage(riskLevel: string, redFlags: string[]): TriageResult {
    const risk = riskLevel?.toLowerCase() ?? "low";
    const level: TriageResult["level"] =
      risk === "critical" ? "emergency"
      : risk === "high" ? "high"
      : risk === "medium" || risk === "moderate" ? "moderate"
      : "low";
    const rec: Record<string, string> = {
      emergency: "Seek emergency medical care immediately.",
      high: "See a doctor within 24 hours.",
      moderate: "Schedule a doctor's appointment within the next week.",
      low: "Monitor your symptoms and follow up at your next routine appointment.",
    };
    const exp: Record<string, string> = {
      emergency: "Critical risk detected in your report. Immediate evaluation is required.",
      high: "Your report indicates high-risk findings that need prompt medical attention.",
      moderate: "Moderate risk findings were detected. A timely medical review is advised.",
      low: "No urgent findings detected. Continue monitoring your health.",
    };
    return {
      level,
      recommendation: rec[level],
      explanation:
        exp[level] +
        (redFlags.length
          ? ` ${redFlags.length} red flag(s) were identified in the report.`
          : ""),
      triggered_by: [
        `Overall risk level: ${riskLevel}`,
        ...redFlags.slice(0, 2),
      ].filter(Boolean),
    };
  }

  // ── STEP 3 → STEP 4: Chat complete, finalize ──────────────────────────────

  async function handleChatComplete(qaHistory: QAEntry[]) {
    if (!initialAnalysis) return;
    setStep("generating");
    const userId = getLocalUserId() ?? "anonymous";

    try {
      const res = await fetch("/api/diagnostic/finalize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          initial_analysis: initialAnalysis,
          qa_history: qaHistory,
          // Pass the reports-table report_id so the DB row gets enriched
          report_id: initialAnalysis.report_id,
        }),
      });
      if (!res.ok) throw new Error(`Finalize error ${res.status}`);
      const data = await res.json();
      setFinalReport(data.report);
      setReportId(data.report_id);
      setRecommendedDoctors(data.recommended_doctors ?? []);
      // Use backend triage; fall back to client-side computation if absent
      setTriage(
        data.triage ??
          _clientTriage(
            data.report?.risk_level ?? initialAnalysis.risk_level ?? "low",
            data.report?.red_flags ?? []
          )
      );
      setKnowledgeGraph(data.knowledge_graph ?? null);
      setPersonalizedInsights(data.personalized_insights ?? []);
      setStep("report");
      addNotification(
        "report_generated",
        "Diagnostic Report Ready",
        "Your full AI diagnostic report with risk assessment and doctor recommendations is ready."
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Report generation failed.");
      setStep("initial_result");
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  const FileIcon = file?.type === "application/pdf" ? FileText : ImageIcon;

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-slide-up">
      <PageHero src={PAGE_IMAGES.upload} opacity={36} objectPosition="center 45%">
        <PageHeader
          title="AI Diagnostic Flow"
          subtitle="Upload a medical report — AI will analyze it, ask follow-up questions, and generate a personalized diagnosis"
          icon={<Brain className="w-5 h-5" />}
        />
      </PageHero>

      <AnimatePresence mode="wait">

        {/* ══ IDLE / UPLOAD ZONE ══════════════════════════════════════════ */}
        {(step === "idle" || step === "uploading") && (
          <motion.div
            key="upload"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="space-y-4"
          >
            {/* Mode selector */}
            <GlassCard>
              <p className="text-sm font-medium text-slate-300 mb-3">Explanation Mode</p>
              <div className="grid grid-cols-2 gap-3">
                {(["simple", "doctor"] as InterpretMode[]).map((m) => (
                  <button
                    key={m}
                    onClick={() => setMode(m)}
                    className={`px-4 py-3 rounded-xl border text-left transition-all ${
                      mode === m
                        ? "border-cyan/40 bg-cyan/10 text-cyan"
                        : "border-glass-border bg-navy-700 text-slate-400 hover:text-slate-300"
                    }`}
                  >
                    <p className="font-semibold text-sm">
                      {m === "simple" ? "Explain Like I'm 5" : "Doctor Mode"}
                    </p>
                    <p className="text-xs mt-0.5 opacity-70">
                      {m === "simple"
                        ? "Simple, empathetic, jargon-free language"
                        : "Clinical terminology + differential diagnosis"}
                    </p>
                  </button>
                ))}
              </div>
            </GlassCard>

            {/* Drop zone */}
            <GlassCard
              className={`border-2 border-dashed transition-all duration-200 ${
                dragOver
                  ? "border-cyan/60 bg-cyan/5"
                  : file
                  ? "border-green/40 bg-green/5"
                  : "border-glass-border hover:border-cyan/30"
              }`}
              onClick={() => !file && inputRef.current?.click()}
            >
              <div
                className="py-10 flex flex-col items-center justify-center cursor-pointer"
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
              >
                <input
                  ref={inputRef}
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png,.webp"
                  className="hidden"
                  onChange={handleFileChange}
                />
                {file ? (
                  <>
                    <div className="p-4 rounded-2xl bg-green/10 border border-green/20 mb-4">
                      <FileIcon className="w-8 h-8 text-green" />
                    </div>
                    <p className="font-medium text-slate-200">{file.name}</p>
                    <p className="text-sm text-slate-500 mt-1">
                      {(file.size / 1024).toFixed(1)} KB · {file.type}
                    </p>
                    <button
                      onClick={(e) => { e.stopPropagation(); resetAll(); }}
                      className="mt-3 flex items-center gap-1.5 text-xs text-slate-500 hover:text-red transition-colors"
                    >
                      <X className="w-3.5 h-3.5" /> Remove file
                    </button>
                  </>
                ) : (
                  <>
                    <div className="p-4 rounded-2xl bg-navy-700 border border-glass-border mb-4">
                      <Upload className="w-8 h-8 text-slate-500" />
                    </div>
                    <p className="font-medium text-slate-300">Drop your medical document here</p>
                    <p className="text-sm text-slate-500 mt-1">PDF, JPG, PNG, WebP — up to 20 MB</p>
                    <button
                      onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}
                      className="mt-4 btn-primary text-xs"
                    >
                      Browse files
                    </button>
                  </>
                )}
              </div>
            </GlassCard>

            {error && (
              <AlertBox variant="error" dismissible onDismiss={() => setError(null)}>
                {error}
              </AlertBox>
            )}

            {/* Backend warm-up status badge */}
            {backendStatus === "warming" && (
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-navy-700 border border-glass-border w-fit">
                <Loader2 className="w-3.5 h-3.5 text-cyan animate-spin" />
                <span className="text-xs text-slate-400">Waking up AI server… this takes ~20 s after inactivity</span>
              </div>
            )}

            {file && (
              <div className="flex items-center justify-end gap-3">
                {backendStatus === "warming" && (
                  <span className="text-xs text-slate-500">Server is starting — please wait</span>
                )}
                <NeonButton
                  onClick={handleAnalyze}
                  loading={step === "uploading"}
                  disabled={step === "uploading" || backendStatus === "warming"}
                  icon={<Sparkles className="w-4 h-4" />}
                  size="lg"
                >
                  {step === "uploading"
                    ? "Analyzing…"
                    : backendStatus === "warming"
                    ? "Waiting for server…"
                    : "Analyze with AI"}
                </NeonButton>
              </div>
            )}

            {/* Flow steps explanation */}
            {!file && (
              <div className="relative rounded-2xl overflow-hidden" style={{ border: "1px solid rgba(0,212,255,0.14)" }}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={PAGE_IMAGES.upload} alt="" loading="lazy" decoding="async" aria-hidden
                  className="absolute inset-0 w-full h-full object-cover pointer-events-none select-none"
                  style={{ opacity: 0.25, objectPosition: "center 45%" }} />
                <div className="absolute inset-0 pointer-events-none"
                  style={{ background: "linear-gradient(135deg, rgba(13,22,39,0.82) 0%, rgba(13,22,39,0.65) 100%)" }} />
                <div className="absolute bottom-0 left-0 right-0 h-px pointer-events-none"
                  style={{ background: "linear-gradient(90deg, transparent, rgba(0,212,255,0.40), transparent)" }} />
                <div className="relative p-5">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-4">How it works</p>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {[
                      { step: "1", icon: Upload, title: "Upload Report", desc: "PDF, X-ray, blood report, MRI, CT scan" },
                      { step: "2", icon: Brain, title: "AI Interview", desc: "Doctor-like follow-up questions to refine the analysis" },
                      { step: "3", icon: Sparkles, title: "Full Diagnosis", desc: "Conditions, risk level, next steps & doctor recommendations" },
                    ].map(({ step: s, icon: Icon, title, desc }) => (
                      <div key={s} className="flex items-start gap-3">
                        <div className="w-7 h-7 rounded-lg bg-cyan/10 border border-cyan/20 flex items-center justify-center text-xs font-bold text-cyan shrink-0">
                          {s}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-300">{title}</p>
                          <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* ══ INITIAL RESULT (before chat) ══════════════════════════════════ */}
        {step === "initial_result" && initialAnalysis && (
          <motion.div
            key="initial"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="space-y-4"
          >
            <GlassCard className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-cyan/10 border border-cyan/20">
                  <Brain className="w-5 h-5 text-cyan" />
                </div>
                <div>
                  <p className="font-semibold text-slate-200">
                    {getReportTypeLabel(initialAnalysis.report_type)} — Initial Analysis Complete
                  </p>
                  <p className="text-xs text-slate-500 font-mono">
                    Confidence: {Math.round(initialAnalysis.confidence * 100)}% ·{" "}
                    {initialAnalysis.findings.length} finding(s) detected
                  </p>
                </div>
              </div>
              <NeonButton variant="ghost" size="sm" onClick={resetAll} icon={<Upload className="w-3.5 h-3.5" />}>
                New upload
              </NeonButton>
            </GlassCard>

            <GlassCard>
              <h3 className="section-title text-base mb-3">Summary</h3>
              <p className="text-sm text-slate-300 leading-relaxed">{initialAnalysis.summary}</p>
            </GlassCard>

            {initialAnalysis.findings.length > 0 && (
              <GlassCard>
                <h3 className="section-title text-base mb-4">Key Findings</h3>
                <div className="space-y-3">
                  {initialAnalysis.findings.map((finding, i) => {
                    const cfg = getSeverityConfig(finding.severity);
                    return (
                      <div key={i} className={`flex items-start gap-3 p-3 rounded-lg border ${cfg.border} ${cfg.bg}`}>
                        <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${cfg.dot}`} />
                        <div className="flex-1 min-w-0">
                          <p className={`text-sm font-medium ${cfg.color}`}>{finding.text}</p>
                          {(finding.value || finding.reference_range) && (
                            <p className="text-xs text-slate-500 font-mono mt-0.5">
                              {finding.value && `Value: ${finding.value}${finding.unit ? ` ${finding.unit}` : ""}`}
                              {finding.reference_range && ` · Ref: ${finding.reference_range}`}
                            </p>
                          )}
                        </div>
                        <SeverityBadge severity={finding.severity} className="shrink-0" />
                      </div>
                    );
                  })}
                </div>
              </GlassCard>
            )}

            {/* CTA to start the diagnostic chat */}
            <GlassCard className="bg-gradient-to-br from-navy-800 to-navy-900 border-cyan/20">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-2xl bg-cyan/10 border border-cyan/30 flex items-center justify-center shrink-0">
                  <Brain className="w-6 h-6 text-cyan" />
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-white">Dr. Anatom AI wants to ask you a few questions</p>
                  <p className="text-sm text-slate-400 mt-1">
                    I&apos;ll ask 3–5 targeted follow-up questions based on your report findings to refine the diagnosis and improve accuracy.
                  </p>
                </div>
              </div>
              <div className="mt-4 flex items-center gap-3">
                <NeonButton onClick={startChat} icon={<ChevronRight className="w-4 h-4" />} size="md">
                  Start Diagnostic Interview
                </NeonButton>
                <button
                  onClick={() => handleChatComplete([])}
                  className="text-sm text-slate-500 hover:text-slate-300 transition-colors"
                >
                  Skip to report
                </button>
              </div>
            </GlassCard>

            {error && (
              <AlertBox variant="error" dismissible onDismiss={() => setError(null)}>
                {error}
              </AlertBox>
            )}
          </motion.div>
        )}

        {/* ══ CHATTING ═════════════════════════════════════════════════════ */}
        {step === "chatting" && initialAnalysis && (
          <motion.div
            key="chat"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <GlassCard className="p-6">
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-xl bg-cyan/10 border border-cyan/30 flex items-center justify-center">
                    <Brain className="w-5 h-5 text-cyan" />
                  </div>
                  <div>
                    <p className="font-semibold text-white text-sm">Dr. Anatom AI</p>
                    <p className="text-xs text-slate-500">Diagnostic Interview</p>
                  </div>
                </div>
                <NeonButton variant="ghost" size="sm" onClick={resetAll} icon={<Upload className="w-3.5 h-3.5" />}>
                  New upload
                </NeonButton>
              </div>
              <DiagnosticChat
                initialAnalysis={initialAnalysis}
                onComplete={handleChatComplete}
              />
            </GlassCard>
          </motion.div>
        )}

        {/* ══ GENERATING ═══════════════════════════════════════════════════ */}
        {step === "generating" && (
          <motion.div
            key="generating"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center py-20 gap-5"
          >
            <div className="relative">
              <div className="w-20 h-20 rounded-full border-4 border-cyan/20" />
              <div className="absolute inset-0 w-20 h-20 rounded-full border-4 border-t-cyan animate-spin" />
              <Brain className="absolute inset-0 m-auto w-8 h-8 text-cyan" />
            </div>
            <div className="text-center">
              <p className="text-lg font-semibold text-white">Generating your report…</p>
              <p className="text-sm text-slate-500 mt-1">
                AI is synthesizing your answers and report findings
              </p>
            </div>
            <div className="flex gap-2 mt-2">
              {["Analyzing responses", "Ranking conditions", "Recommending doctors"].map((label, i) => (
                <motion.span
                  key={label}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.6 }}
                  className="text-xs px-3 py-1 rounded-full bg-navy-700 border border-glass-border text-slate-500"
                >
                  {label}
                </motion.span>
              ))}
            </div>
          </motion.div>
        )}

        {/* ══ FULL REPORT ══════════════════════════════════════════════════ */}
        {step === "report" && finalReport && reportId && initialAnalysis && (
          <motion.div
            key="report"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <DiagnosticReport
              report={finalReport}
              reportId={reportId}
              initialAnalysis={initialAnalysis}
              recommendedDoctors={recommendedDoctors}
              triage={triage}
              knowledgeGraph={knowledgeGraph}
              personalizedInsights={personalizedInsights}
              onReset={resetAll}
            />
          </motion.div>
        )}

      </AnimatePresence>
    </div>
  );
}
