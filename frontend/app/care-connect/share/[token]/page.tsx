"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Brain, AlertTriangle, CheckCircle2, Stethoscope, Clock, Eye, ArrowRight } from "lucide-react";
import Link from "next/link";
import { RiskBadge } from "@/components/care-connect/RiskBadge";
import { ConditionTable } from "@/components/care-connect/ConditionTable";
import { careConnectApi, PublicReportResponse } from "@/lib/careConnectApi";

export default function SharedReportPage() {
  const { token } = useParams<{ token: string }>();
  const [report, setReport] = useState<PublicReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    careConnectApi.getSharedReport(token)
      .then(setReport)
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="fixed inset-0 bg-[#0F172A] z-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 rounded-full border-4 border-cyan/30 border-t-cyan animate-spin mx-auto mb-4" />
          <p className="text-slate-400 text-sm">Loading report...</p>
        </div>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="fixed inset-0 bg-[#0F172A] z-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full text-center">
          <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-5">
            <AlertTriangle className="w-8 h-8 text-red-400" />
          </div>
          <h1 className="text-xl font-bold text-white mb-2">Link Unavailable</h1>
          <p className="text-slate-400 text-sm mb-6">
            This report link has expired, been revoked, or does not exist.
          </p>
          <Link href="/" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-cyan/10 border border-cyan/30 text-cyan text-sm font-medium hover:bg-cyan/20 transition-colors">
            Get your own report <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    );
  }

  if (!report) return null;

  const date = new Date(report.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" });
  const expiresDate = new Date(report.expires_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" });

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-[#0F172A]">
      {/* Top bar */}
      <div className="border-b border-white/5 bg-navy-900/80 backdrop-blur-xl px-4 py-3">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-cyan/10 border border-cyan/30 flex items-center justify-center">
              <Brain className="w-3.5 h-3.5 text-cyan" />
            </div>
            <span className="font-display font-bold text-white text-sm tracking-wider">ANATOM<span className="text-cyan">-AI</span></span>
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> {report.view_count} view{report.view_count !== 1 ? "s" : ""}</span>
            <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> Expires {expiresDate}</span>
          </div>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs text-slate-500 font-mono uppercase tracking-wider mb-1">Shared Health Report</p>
              <h1 className="text-2xl font-bold text-white">AI Medical Analysis</h1>
              <p className="text-slate-500 text-sm mt-1">{date}</p>
            </div>
            <RiskBadge level={report.risk_level} size="lg" />
          </div>
        </motion.div>

        {/* Symptoms */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }}>
          <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
            <h3 className="font-semibold text-white mb-3 flex items-center gap-2 text-sm">
              <Stethoscope className="w-4 h-4 text-cyan" /> Reported Symptoms
            </h3>
            <div className="flex flex-wrap gap-2">
              {report.symptoms.map((s) => (
                <span key={s} className="text-xs px-3 py-1.5 rounded-full bg-cyan/10 border border-cyan/20 text-cyan">{s}</span>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Conditions */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }}>
          <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
            <h3 className="font-semibold text-white mb-3 text-sm">Probable Conditions</h3>
            <ConditionTable conditions={report.probable_conditions} />
          </div>
        </motion.div>

        {/* Red flags */}
        {report.red_flags.length > 0 && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
            <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-5">
              <h3 className="font-semibold text-red-400 mb-3 flex items-center gap-2 text-sm">
                <AlertTriangle className="w-4 h-4" /> Red Flag Warnings
              </h3>
              <ul className="space-y-2">
                {report.red_flags.map((f, i) => (
                  <li key={i} className="text-sm text-red-300 flex items-start gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" /> {f}
                  </li>
                ))}
              </ul>
            </div>
          </motion.div>
        )}

        {/* Next steps */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18 }}>
          <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
            <h3 className="font-semibold text-white mb-3 flex items-center gap-2 text-sm">
              <CheckCircle2 className="w-4 h-4 text-green" /> Recommended Next Steps
            </h3>
            <ol className="space-y-2">
              {report.next_steps.map((s, i) => (
                <li key={i} className="flex items-start gap-3 text-sm text-slate-300">
                  <span className="w-5 h-5 rounded-full bg-green/10 border border-green/30 text-green text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">{i + 1}</span>
                  {s}
                </li>
              ))}
            </ol>
          </div>
        </motion.div>

        {/* Specialization */}
        <div className="bg-cyan/5 border border-cyan/20 rounded-2xl p-4 text-center">
          <p className="text-xs text-slate-500 mb-1">Recommended Specialist</p>
          <p className="text-cyan font-semibold">{report.recommended_specialization}</p>
        </div>

        {/* Disclaimer */}
        <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4">
          <p className="text-xs text-amber-300/70 text-center leading-relaxed">
            ⚠ This report was generated by Anatom-AI CareConnect for informational purposes only.
            It does not constitute medical advice, diagnosis, or treatment. Always consult a qualified healthcare professional.
          </p>
        </div>

        {/* CTA */}
        <div className="text-center pb-6">
          <p className="text-xs text-slate-600 mb-3">Want your own AI health report?</p>
          <Link href="/"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-cyan text-navy-900 font-bold text-sm hover:bg-cyan/90 transition-colors">
            Try Anatom-AI Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
