"use client";

import { useState } from "react";
import { X, Copy, CheckCheck, MessageCircle, Mail, Clock } from "lucide-react";
import { careConnectApi } from "@/lib/careConnectApi";

interface Props {
  reportId: string;
  onClose: () => void;
}

const EXPIRY_OPTIONS = [
  { label: "24 hours", hours: 24 },
  { label: "48 hours", hours: 48 },
  { label: "7 days", hours: 168 },
];

export function ShareModal({ reportId, onClose }: Props) {
  const [expiry, setExpiry] = useState(48);
  const [shareUrl, setShareUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const generate = async () => {
    setLoading(true);
    try {
      const res = await careConnectApi.shareReport(reportId, expiry);
      setShareUrl(res.share_url);
    } catch {
      /* noop */
    } finally {
      setLoading(false);
    }
  };

  const copy = async () => {
    await navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const whatsapp = () => window.open(`https://wa.me/?text=View+my+health+report:+${encodeURIComponent(shareUrl)}`, "_blank");
  const email = () => window.open(`mailto:?subject=My Health Report - Anatom AI&body=View my health report here: ${shareUrl}`, "_blank");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md bg-navy-800 border border-glass-border rounded-2xl p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-semibold text-white">Share Report</h3>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-navy-600 text-slate-400 hover:text-white transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {!shareUrl ? (
          <div className="space-y-4">
            <p className="text-sm text-slate-400">Choose how long the link should remain active:</p>
            <div className="grid grid-cols-3 gap-2">
              {EXPIRY_OPTIONS.map((opt) => (
                <button key={opt.hours} onClick={() => setExpiry(opt.hours)}
                  className={`flex items-center justify-center gap-1.5 py-2.5 rounded-xl border text-sm font-medium transition-all ${expiry === opt.hours ? "border-cyan/50 bg-cyan/10 text-cyan" : "border-glass-border text-slate-400 hover:border-slate-500"}`}>
                  <Clock className="w-3.5 h-3.5" />
                  {opt.label}
                </button>
              ))}
            </div>
            <p className="text-xs text-slate-600">Anyone with the link can view your report in read-only mode.</p>
            <button onClick={generate} disabled={loading}
              className="w-full py-2.5 rounded-xl bg-cyan text-navy-900 font-semibold text-sm hover:bg-cyan/90 transition-colors disabled:opacity-50">
              {loading ? "Generating link..." : "Generate Share Link"}
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center gap-2 bg-navy-900 border border-glass-border rounded-xl px-3 py-2.5">
              <input readOnly value={shareUrl} className="flex-1 bg-transparent text-xs text-slate-300 outline-none font-mono" />
              <button onClick={copy} className="shrink-0 p-1.5 rounded-lg hover:bg-navy-600 transition-colors">
                {copied ? <CheckCheck className="w-4 h-4 text-green" /> : <Copy className="w-4 h-4 text-slate-400" />}
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button onClick={whatsapp}
                className="flex items-center justify-center gap-2 py-2.5 rounded-xl border border-green/30 bg-green/10 text-green text-sm font-medium hover:bg-green/20 transition-colors">
                <MessageCircle className="w-4 h-4" />
                WhatsApp
              </button>
              <button onClick={email}
                className="flex items-center justify-center gap-2 py-2.5 rounded-xl border border-glass-border text-slate-300 text-sm font-medium hover:border-slate-500 hover:text-white transition-colors">
                <Mail className="w-4 h-4" />
                Email
              </button>
            </div>

            <p className="text-xs text-slate-600 text-center">
              Link expires in {EXPIRY_OPTIONS.find((o) => o.hours === expiry)?.label}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
