"use client";

import { motion } from "framer-motion";

interface Props {
  questions: string[];
  onSelect: (q: string) => void;
}

export function SuggestedQuestions({ questions, onSelect }: Props) {
  if (!questions.length) return null;

  return (
    <div className="flex flex-wrap gap-2 px-4 pb-3">
      {questions.map((q, i) => (
        <motion.button
          key={q}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          onClick={() => onSelect(q)}
          className="text-[12px] px-3 py-1.5 rounded-full transition-all cursor-pointer whitespace-nowrap"
          style={{
            background: "rgba(255,255,255,0.06)",
            border: "1px solid rgba(84,84,88,0.35)",
            color: "#8E8E93",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background = "rgba(10,132,255,0.12)";
            (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(10,132,255,0.35)";
            (e.currentTarget as HTMLButtonElement).style.color = "#0A84FF";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.06)";
            (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(84,84,88,0.35)";
            (e.currentTarget as HTMLButtonElement).style.color = "#8E8E93";
          }}
        >
          {q}
        </motion.button>
      ))}
    </div>
  );
}
