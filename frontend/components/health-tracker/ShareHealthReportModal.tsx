"use client";
import { useState } from "react";
import { X, Copy, Check, Share2 } from "lucide-react";
import { healthTrackerApi } from "@/lib/healthTrackerApi";

interface Props {
  userId: string;
  open: boolean;
  onClose: () => void;
}

export default function ShareHealthReportModal({ userId, open, onClose }: Props) {
  const [loading, setLoading] = useState(false);
  const [shareUrl, setShareUrl] = useState("");
  const [copied, setCopied] = useState(false);
  const [expiryHours, setExpiryHours] = useState(72);

  if (!open) return null;

  const generate = async () => {
    setLoading(true);
    try {
      const res = await healthTrackerApi.shareReport({ user_id: userId, expiry_hours: expiryHours });
      setShareUrl(`${window.location.origin}${res.data.share_url}`);
    } finally {
      setLoading(false);
    }
  };

  const copy = async () => {
    await navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 w-full max-w-md rounded-2xl p-6"
        style={{ background: "#0D1627", border: "1px solid rgba(0,212,255,0.2)" }}>
        <div className="flex justify-between items-center mb-5">
          <div className="flex items-center gap-2">
            <Share2 size={16} className="text-cyan-400" />
            <h3 className="text-sm font-semibold text-white">Share Health Report</h3>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300"><X size={16} /></button>
        </div>

        <p className="text-xs text-gray-400 mb-4">
          Generate a secure read-only link to share your symptom report with your doctor or care team.
        </p>

        <div className="mb-4">
          <label className="text-xs text-gray-400 mb-2 block">Link expires after</label>
          <div className="flex gap-2">
            {[24, 48, 72, 168].map((h) => (
              <button key={h} onClick={() => setExpiryHours(h)}
                className="flex-1 py-2 rounded-lg text-xs font-medium transition-all"
                style={{
                  background: expiryHours === h ? "rgba(0,212,255,0.2)" : "rgba(255,255,255,0.04)",
                  color: expiryHours === h ? "#00D4FF" : "#8899AA",
                  border: `1px solid ${expiryHours === h ? "#00D4FF" : "transparent"}`,
                }}>
                {h < 48 ? `${h}h` : h === 168 ? "7d" : `${h/24}d`}
              </button>
            ))}
          </div>
        </div>

        {!shareUrl ? (
          <button onClick={generate} disabled={loading}
            className="btn-primary w-full py-2.5 text-sm font-semibold">
            {loading ? "Generating…" : "Generate Share Link"}
          </button>
        ) : (
          <div className="space-y-3">
            <div className="flex gap-2">
              <input readOnly value={shareUrl}
                className="input-field flex-1 text-xs" />
              <button onClick={copy}
                className="px-3 rounded-lg flex items-center gap-1 text-xs font-medium"
                style={{ background: "rgba(0,212,255,0.15)", color: "#00D4FF" }}>
                {copied ? <Check size={13} /> : <Copy size={13} />}
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
            <p className="text-xs text-gray-500 text-center">Link expires in {expiryHours} hours</p>
          </div>
        )}
      </div>
    </div>
  );
}
