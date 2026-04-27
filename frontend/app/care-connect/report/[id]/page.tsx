"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Download, Share2, ChevronLeft, AlertTriangle,
  CheckCircle2, Stethoscope, Activity,
} from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { GlassCard } from "@/components/ui/GlassCard";
import { RiskBadge } from "@/components/care-connect/RiskBadge";
import { ConditionTable } from "@/components/care-connect/ConditionTable";
import { TreatmentPanel } from "@/components/care-connect/TreatmentPanel";
import { DoctorCard } from "@/components/care-connect/DoctorCard";
import { ShareModal } from "@/components/care-connect/ShareModal";
import { careConnectApi, CareReport, Doctor } from "@/lib/careConnectApi";
import { useCareConnectStore } from "@/lib/useCareConnectStore";

export default function ReportDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { currentReport, currentDoctors, setCurrentReport } = useCareConnectStore();

  const [report, setReport] = useState<CareReport | null>(currentReport);
  const [doctors, setDoctors] = useState<Doctor[]>(currentDoctors);
  const [loading, setLoading] = useState(!currentReport);
  const [showShare, setShowShare] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);

  useEffect(() => {
    if (!currentReport || currentReport.id !== id) {
      careConnectApi.getReport(id)
        .then((res) => {
          setReport(res.report);
          setDoctors(res.recommended_doctors);
          setCurrentReport(res.report, res.recommended_doctors);
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [id]);

  const downloadPdf = () => {
    setPdfLoading(true);
    const url = careConnectApi.downloadPdfUrl(id);
    const a = document.createElement("a");
    a.href = url;
    a.download = `care-report-${id}.pdf`;
    a.click();
    setTimeout(() => setPdfLoading(false), 2000);
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-32 rounded-2xl bg-navy-800/40 border border-glass-border animate-pulse" />
        ))}
      </div>
    );
  }

  if (!report) {
    return (
      <GlassCard className="py-20 text-center">
        <AlertTriangle className="w-10 h-10 text-amber-400 mx-auto mb-3" />
        <p className="text-white font-medium">Report not found</p>
        <button onClick={() => router.push("/care-connect")} className="mt-4 text-sm text-cyan hover:underline">
          Back to CareConnect
        </button>
      </GlassCard>
    );
  }

  const date = new Date(report.created_at).toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button onClick={() => router.push("/care-connect")}
            className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-white mb-3 transition-colors">
            <ChevronLeft className="w-4 h-4" /> CareConnect
          </button>
          <PageHeader title="Health Report" subtitle={date} />
        </div>
        <div className="flex items-center gap-2 mt-8">
          <button onClick={() => setShowShare(true)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-glass-border text-slate-400 text-sm hover:border-slate-500 hover:text-white transition-all">
            <Share2 className="w-4 h-4" /> Share
          </button>
          <button onClick={downloadPdf} disabled={pdfLoading}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-cyan/10 border border-cyan/30 text-cyan text-sm font-medium hover:bg-cyan/20 transition-all disabled:opacity-50">
            <Download className="w-4 h-4" />
            {pdfLoading ? "Preparing..." : "PDF"}
          </button>
        </div>
      </div>

      {/* Patient summary */}
      <GlassCard className="p-5">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div><p className="text-xs text-slate-500 mb-0.5">Age</p><p className="text-white font-medium">{report.user_age ?? "—"}</p></div>
          <div><p className="text-xs text-slate-500 mb-0.5">Gender</p><p className="text-white font-medium capitalize">{report.user_gender ?? "—"}</p></div>
          <div><p className="text-xs text-slate-500 mb-0.5">Severity</p><p className="text-white font-medium capitalize">{report.severity}</p></div>
          <div><p className="text-xs text-slate-500 mb-0.5">Duration</p><p className="text-white font-medium">{report.duration_days} day{report.duration_days !== 1 ? "s" : ""}</p></div>
        </div>
      </GlassCard>

      {/* Symptoms */}
      <GlassCard className="p-5">
        <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan" /> Reported Symptoms
        </h3>
        <div className="flex flex-wrap gap-2">
          {report.symptoms.map((s) => (
            <span key={s} className="text-xs px-3 py-1.5 rounded-full bg-cyan/10 border border-cyan/20 text-cyan">{s}</span>
          ))}
        </div>
        {report.medical_history.length > 0 && (
          <div className="mt-3 pt-3 border-t border-glass-border/50">
            <p className="text-xs text-slate-500 mb-2">Medical History</p>
            <div className="flex flex-wrap gap-2">
              {report.medical_history.map((h) => (
                <span key={h} className="text-xs px-3 py-1 rounded-full bg-navy-700 border border-glass-border text-slate-400">{h}</span>
              ))}
            </div>
          </div>
        )}
      </GlassCard>

      {/* Risk level + conditions */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <GlassCard className="p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-white flex items-center gap-2">
              <Stethoscope className="w-4 h-4 text-cyan" /> AI Analysis
            </h3>
            <RiskBadge level={report.risk_level} size="md" />
          </div>
          <ConditionTable conditions={report.probable_conditions} />
          {report.affected_organs.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 mb-2">Affected Organs</p>
              <div className="flex flex-wrap gap-2">
                {report.affected_organs.map((o) => (
                  <span key={o} className="text-xs px-2.5 py-1 rounded-full border border-glass-border text-slate-400 capitalize">{o}</span>
                ))}
              </div>
            </div>
          )}
        </GlassCard>
      </motion.div>

      {/* Red flags */}
      {report.red_flags.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-5">
            <h3 className="font-semibold text-red-400 mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" /> Red Flag Warnings
            </h3>
            <ul className="space-y-2">
              {report.red_flags.map((f, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-red-300">
                  <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0 text-red-400" />
                  {f}
                </li>
              ))}
            </ul>
          </div>
        </motion.div>
      )}

      {/* Next steps */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <GlassCard className="p-5">
          <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-green" /> Recommended Next Steps
          </h3>
          <ol className="space-y-2">
            {report.next_steps.map((step, i) => (
              <li key={i} className="flex items-start gap-3 text-sm text-slate-300">
                <span className="w-6 h-6 rounded-full bg-green/10 border border-green/30 text-green text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">{i + 1}</span>
                {step}
              </li>
            ))}
          </ol>
        </GlassCard>
      </motion.div>

      {/* Treatment suggestions */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
        <TreatmentPanel suggestions={report.treatment_suggestions} />
      </motion.div>

      {/* Recommended doctors */}
      {doctors.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white">Recommended Specialists</h3>
            <span className="text-xs text-cyan border border-cyan/30 px-2 py-0.5 rounded-full">
              {report.recommended_specialization}
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {doctors.slice(0, 4).map((doc) => (
              <DoctorCard key={doc.id} doctor={doc} />
            ))}
          </div>
        </motion.div>
      )}

      {showShare && <ShareModal reportId={id} onClose={() => setShowShare(false)} />}
    </div>
  );
}
