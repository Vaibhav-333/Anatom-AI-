"use client";
import { useState } from "react";
import { Download, Share2, FileText } from "lucide-react";
import ShareHealthReportModal from "@/components/health-tracker/ShareHealthReportModal";
import { healthTrackerApi } from "@/lib/healthTrackerApi";
import { getLocalUserId } from "@/lib/utils";
import { useNotificationStore } from "@/lib/notificationStore";

export default function ExportPage() {
  const userId = getLocalUserId();
  const addNotification = useNotificationStore((s) => s.addNotification);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().slice(0, 10);
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [shareOpen, setShareOpen] = useState(false);

  const pdfUrl = healthTrackerApi.getPdfUrl(userId, startDate, endDate);

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Export Report</h1>
        <p className="text-sm text-gray-400 mt-1">Download or share your symptom report with your healthcare provider.</p>
      </div>

      <div className="rounded-2xl p-6 space-y-5"
        style={{ background: "rgba(13,22,39,0.85)", border: "1px solid rgba(0,212,255,0.15)" }}>
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider">Report Settings</h3>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Start Date</label>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)}
              className="input-field w-full text-sm" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">End Date</label>
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)}
              className="input-field w-full text-sm" />
          </div>
        </div>

        <div className="rounded-xl p-4 space-y-2" style={{ background: "rgba(0,212,255,0.06)", border: "1px solid rgba(0,212,255,0.15)" }}>
          <div className="flex items-center gap-2 mb-1">
            <FileText size={14} className="text-cyan-400" />
            <span className="text-xs font-semibold text-cyan-400">Report Includes</span>
          </div>
          {["Health summary & weekly score", "Daily symptom trend table", "Medication adherence stats", "AI insights & alerts", "Personalized recommendations"].map((item) => (
            <p key={item} className="text-xs text-gray-300 flex gap-2"><span className="text-green-400">✓</span>{item}</p>
          ))}
        </div>

        <div className="flex gap-3">
          <a
            href={pdfUrl}
            download
            onClick={() =>
              addNotification(
                "export_ready",
                "Report Exported",
                `Health report (${startDate} → ${endDate}) downloaded as PDF.`
              )
            }
            className="btn-primary flex-1 flex items-center justify-center gap-2 py-3 text-sm font-semibold no-underline"
          >
            <Download size={15} /> Download PDF
          </a>
          <button onClick={() => setShareOpen(true)}
            className="btn-secondary flex items-center gap-2 px-5 py-3 text-sm font-semibold">
            <Share2 size={15} /> Share
          </button>
        </div>
      </div>

      <ShareHealthReportModal userId={userId} open={shareOpen} onClose={() => setShareOpen(false)} />
    </div>
  );
}
