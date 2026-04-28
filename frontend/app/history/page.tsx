"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { History, FileText, Trash2, ArrowRight, TrendingUp, ShieldAlert } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageHero } from "@/components/ui/PageHero";
import { PAGE_IMAGES } from "@/lib/pageImages";
import { GlassCard } from "@/components/ui/GlassCard";
import { RiskBadge } from "@/components/ui/StatusBadge";
import { NeonButton } from "@/components/ui/NeonButton";
import { AlertBox } from "@/components/ui/AlertBox";
import { getLocalUserId, formatRelativeDate, getReportTypeLabel } from "@/lib/utils";
import type { ReportSummary, TriageLevel } from "@/lib/types";

const TRIAGE_BADGE: Record<TriageLevel, { label: string; className: string }> = {
  low:       { label: "🟢 Low",       className: "text-emerald-400 bg-emerald-500/10 border border-emerald-500/20" },
  moderate:  { label: "🟡 Moderate",  className: "text-amber-400 bg-amber-500/10 border border-amber-500/20" },
  high:      { label: "🔴 High",      className: "text-red-400 bg-red-500/10 border border-red-500/20" },
  emergency: { label: "🚨 Emergency", className: "text-red-300 bg-red-500/15 border border-red-400/30" },
};

export default function HistoryPage() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const userId = getLocalUserId() ?? "anonymous";

    fetch(`/api/history/${userId}`)
      .then(async (r) => {
        if (!r.ok) throw new Error("Backend not connected — start your local server to view history.");
        const ct = r.headers.get("content-type") ?? "";
        if (!ct.includes("application/json")) throw new Error("Backend not connected — start your local server to view history.");
        return r.json();
      })
      .then((data) => setReports(Array.isArray(data) ? data : []))
      .catch((e) => {
        const msg: string = e?.message ?? "";
        setError(
          msg.includes("Unexpected token") || msg.includes("<!DOCTYPE")
            ? "Backend not connected — start your local server to view history."
            : msg
        );
      })
      .finally(() => setLoading(false));
  }, []);

  const handleDelete = async (reportId: string) => {
    const userId = getLocalUserId();
    if (!userId) return;
    await fetch(`/api/history/${userId}/${reportId}`, { method: "DELETE" });
    setReports((prev) => prev.filter((r) => r.id !== reportId));
  };

  const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } };
  const item = { hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0 } };

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-slide-up">
      <PageHero src={PAGE_IMAGES.history} opacity={36} objectPosition="center 35%">
        <PageHeader
          title="Report History"
          subtitle="All your uploaded medical documents and analyses"
          icon={<History className="w-5 h-5" />}
          badge={
            <span className="badge-info font-mono">{reports.length} reports</span>
          }
        />
      </PageHero>

      {error && <AlertBox variant="error">{error}</AlertBox>}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="flex items-center gap-3 text-slate-500">
            <div className="w-5 h-5 border-2 border-cyan/30 border-t-cyan rounded-full animate-spin" />
            <span className="text-sm">Loading history...</span>
          </div>
        </div>
      ) : reports.length === 0 ? (
        <GlassCard className="py-16 flex flex-col items-center justify-center text-center">
          <FileText className="w-12 h-12 text-slate-700 mb-4" />
          <h3 className="font-semibold text-slate-400 mb-2">No reports yet</h3>
          <p className="text-sm text-slate-600 mb-6">Upload your first medical document to get started.</p>
          <Link href="/upload">
            <NeonButton>Upload a report</NeonButton>
          </Link>
        </GlassCard>
      ) : (
        <motion.div variants={container} initial="hidden" animate="show" className="space-y-3">
          {reports.map((report) => (
            <motion.div key={report.id} variants={item}>
              <GlassCard hover glow="cyan" className="flex items-center gap-4">
                <div className="p-2.5 rounded-xl bg-navy-700 border border-glass-border shrink-0">
                  <FileText className="w-5 h-5 text-slate-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-medium text-slate-200 truncate">{report.file_name}</p>
                    <RiskBadge level={report.risk_level} />
                    {report.triage_level && TRIAGE_BADGE[report.triage_level] && (
                      <span
                        className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${TRIAGE_BADGE[report.triage_level].className}`}
                      >
                        <ShieldAlert className="w-3 h-3" />
                        {TRIAGE_BADGE[report.triage_level].label}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5 font-mono">
                    {getReportTypeLabel(report.report_type)} · {formatRelativeDate(report.upload_date)}
                  </p>
                  {report.summary_snippet && (
                    <p className="text-xs text-slate-600 mt-1.5 line-clamp-1">{report.summary_snippet}</p>
                  )}
                  {report.affected_regions.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {report.affected_regions.slice(0, 4).map((r) => (
                        <span key={r} className="text-xs px-1.5 py-0.5 rounded bg-cyan/5 border border-cyan/10 text-cyan/70 capitalize">
                          {r}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Link href={`/results/${report.id}`}>
                    <NeonButton size="sm" variant="ghost" icon={<ArrowRight className="w-3.5 h-3.5" />}>
                      View
                    </NeonButton>
                  </Link>
                  <button
                    onClick={() => handleDelete(report.id)}
                    className="p-2 rounded-lg text-slate-600 hover:text-red transition-colors hover:bg-red/10"
                    aria-label="Delete report"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}
