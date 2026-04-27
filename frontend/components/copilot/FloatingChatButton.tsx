"use client";

import { motion } from "framer-motion";
import { MessageCircle, X } from "lucide-react";
import { useCopilotStore } from "@/lib/copilotStore";

export function FloatingChatButton() {
  const { isOpen, isWindowOpen, openTray, closeAll } = useCopilotStore();

  const isAnyOpen = isOpen || isWindowOpen;

  function handleClick() {
    if (isAnyOpen) {
      closeAll();
    } else {
      openTray();
    }
  }

  return (
    <motion.button
      onClick={handleClick}
      whileHover={{ scale: 1.06 }}
      whileTap={{ scale: 0.93 }}
      className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full text-white flex items-center justify-center focus:outline-none transition-all"
      style={{
        background: "#0A84FF",
        boxShadow: isAnyOpen
          ? "0 0 0 3px rgba(10,132,255,0.30), 0 8px 32px rgba(0,0,0,0.5)"
          : "0 8px 24px rgba(0,0,0,0.45), 0 2px 8px rgba(10,132,255,0.20)",
      }}
      title={isAnyOpen ? "Close AI chat" : "Open AI Health Copilot"}
      aria-label={isAnyOpen ? "Close AI chat" : "Open AI health chat"}
    >
      {/* Subtle pulse ring — only when closed */}
      {!isAnyOpen && (
        <motion.span
          className="absolute inset-0 rounded-full"
          style={{ background: "rgba(10,132,255,0.25)" }}
          animate={{ scale: [1, 1.35, 1], opacity: [0.4, 0, 0.4] }}
          transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut" }}
        />
      )}

      {/* Toggle icon */}
      <motion.div
        animate={{ rotate: isAnyOpen ? 90 : 0 }}
        transition={{ duration: 0.2 }}
      >
        {isAnyOpen ? <X size={22} strokeWidth={2.5} /> : <MessageCircle size={22} strokeWidth={2} />}
      </motion.div>

      {/* AI badge — only when closed */}
      {!isAnyOpen && (
        <span
          className="absolute -top-1 -right-1 text-[9px] font-bold rounded-full px-1.5 py-0.5 leading-none"
          style={{ background: "#FF453A", color: "#fff" }}
        >
          AI
        </span>
      )}
    </motion.button>
  );
}
