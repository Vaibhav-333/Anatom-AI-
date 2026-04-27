"use client";

import { motion } from "framer-motion";

export function TypingIndicator() {
  return (
    <div
      className="flex items-center gap-1.5 px-4 py-3 rounded-2xl rounded-bl-sm w-fit"
      style={{ background: "#1C1C1E" }}
    >
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="w-2 h-2 rounded-full"
          style={{ background: "#0A84FF" }}
          animate={{ y: [0, -5, 0], opacity: [0.5, 1, 0.5] }}
          transition={{
            duration: 0.7,
            repeat: Infinity,
            delay: i * 0.16,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}
