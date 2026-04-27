"use client";
import { useState } from "react";
import { Bell, X } from "lucide-react";
import { MedicationResponse, MedLogResponse } from "@/lib/healthTrackerStore";
import { AnimatePresence, motion } from "framer-motion";

interface Props {
  medications: MedicationResponse[];
  todayLogs: MedLogResponse[];
}

export default function ReminderNudge({ medications, todayLogs }: Props) {
  const [dismissed, setDismissed] = useState(false);
  const takenIds = new Set(todayLogs.filter((l) => l.status === "taken").map((l) => l.medication_id));
  const pending = medications.filter((m) => m.active && !takenIds.has(m.id));

  if (!pending.length || dismissed) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className="flex items-start gap-3 rounded-xl p-4 mb-4"
        style={{ background: "rgba(255,184,0,0.12)", border: "1px solid rgba(255,184,0,0.35)" }}>
        <Bell size={16} className="text-amber-400 mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          <p className="text-sm font-semibold text-amber-400">Medication Reminder</p>
          <p className="text-xs text-gray-300 mt-0.5">
            You haven't logged today's dose for:{" "}
            <span className="font-medium text-amber-300">
              {pending.map((m) => m.name).join(", ")}
            </span>
          </p>
        </div>
        <button onClick={() => setDismissed(true)} className="text-gray-500 hover:text-gray-300">
          <X size={14} />
        </button>
      </motion.div>
    </AnimatePresence>
  );
}
