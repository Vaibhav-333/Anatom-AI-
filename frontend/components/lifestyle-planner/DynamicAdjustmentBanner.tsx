"use client";
import { Info, X } from "lucide-react";
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

export default function DynamicAdjustmentBanner() {
  const [dismissed, setDismissed] = useState(false);
  return (
    <AnimatePresence>
      {!dismissed && (
        <motion.div
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -16 }}
          className="flex items-start gap-3 rounded-xl p-4"
          style={{ background: "rgba(255,184,0,0.12)", border: "1px solid rgba(255,184,0,0.35)" }}>
          <Info size={15} className="text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-amber-400">Plan auto-adjusted</p>
            <p className="text-xs text-gray-300 mt-0.5">
              Your exercise intensity was set to <strong>light</strong> based on recent worsening symptom trends.
              Update your goal or activity level if you feel better.
            </p>
          </div>
          <button onClick={() => setDismissed(true)} className="text-gray-500 hover:text-gray-300">
            <X size={14} />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
