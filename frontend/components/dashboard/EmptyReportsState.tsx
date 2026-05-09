"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Upload, ArrowRight, Sparkles } from "lucide-react";
import { NeonButton } from "@/components/ui/NeonButton";
import { DASH_IMAGES } from "@/lib/dashboardImages";

const features = ["AI Analysis", "3D Mapping", "Risk Scoring", "Doctor Match"];

export function EmptyReportsState() {
  return (
    <div className="flex flex-col items-center justify-center py-6 px-4 text-center">
      {/* Medical image card */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative w-full max-w-[260px] h-[130px] rounded-2xl overflow-hidden mb-6 group"
        style={{
          boxShadow: "var(--glass-shadow-lg)",
        }}
      >
        {/* Photo */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={DASH_IMAGES.emptyReport}
          alt="Medical records"
          loading="lazy"
          decoding="async"
          className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
          style={{ opacity: 0.80 }}
        />

        {/* Dark gradient overlay */}
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(180deg, rgba(17,17,19,0.20) 0%, rgba(17,17,19,0.62) 60%, rgba(17,17,19,0.92) 100%)",
          }}
        />

        {/* Static border */}
        <div
          className="absolute inset-0 rounded-2xl"
          style={{ border: "1px solid var(--border-default)" }}
        />

        {/* Floating badge */}
        <div
          className="absolute top-3 left-3 flex items-center gap-1.5 px-2 py-1 rounded-full backdrop-blur-sm"
          style={{
            background: "rgba(0,0,0,0.60)",
            border: "1px solid var(--border-default)",
          }}
        >
          <span
            className="w-1.5 h-1.5 rounded-full animate-pulse"
            style={{ background: "rgba(10,132,255,0.7)" }}
          />
          <span className="text-[10px] font-mono" style={{ color: "var(--label-secondary)" }}>AI-Ready</span>
        </div>

        {/* Bottom label */}
        <div className="absolute bottom-3 left-3 right-3">
          <p className="text-xs font-medium" style={{ color: "var(--label-primary)" }}>
            Upload a report to begin
          </p>
          <p className="text-[10px] font-mono mt-0.5" style={{ color: "var(--label-secondary)" }}>
            MRI · X-Ray · Blood Panel · CT
          </p>
        </div>
      </motion.div>

      {/* Text */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.15 }}
      >
        <h3 className="font-semibold text-base mb-1.5" style={{ color: "var(--label-primary)" }}>
          No reports yet
        </h3>
        <p className="text-sm max-w-[260px] leading-relaxed mb-5" style={{ color: "var(--label-secondary)" }}>
          Start by uploading your first medical report to unlock AI-powered insights,
          3D visualization, and a personalized care plan.
        </p>
      </motion.div>

      {/* CTAs */}
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.25 }}
        className="flex flex-col sm:flex-row items-center gap-3"
      >
        <Link href="/upload">
          <NeonButton variant="cyan" size="sm" icon={<Upload className="w-3.5 h-3.5" />}>
            Upload Report
          </NeonButton>
        </Link>
        <Link
          href="/profile"
          className="flex items-center gap-1 text-xs transition-colors"
          style={{ color: "var(--label-secondary)" }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLAnchorElement).style.color = "var(--label-primary)"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLAnchorElement).style.color = "var(--label-secondary)"; }}
        >
          Set up profile
          <ArrowRight className="w-3 h-3" />
        </Link>
      </motion.div>

      {/* Feature pills */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3, delay: 0.4 }}
        className="flex items-center gap-2 mt-5 flex-wrap justify-center"
      >
        {features.map((f) => (
          <div
            key={f}
            className="flex items-center gap-1 px-2.5 py-1 rounded-full"
            style={{ background: "var(--bg-elevated)" }}
          >
            <Sparkles className="w-2.5 h-2.5" style={{ color: "var(--label-tertiary)" }} />
            <span className="text-[10px] font-mono" style={{ color: "var(--label-secondary)" }}>{f}</span>
          </div>
        ))}
      </motion.div>
    </div>
  );
}
