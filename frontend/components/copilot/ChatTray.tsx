"use client";

import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, MessageSquarePlus, Clock } from "lucide-react";
import { useCopilotStore } from "@/lib/copilotStore";
import { fetchConversations, fetchHistory } from "@/lib/copilotApi";

export function ChatTray() {
  const {
    isOpen,
    isClosing,
    isWindowOpen,
    closeAll,
    openWindow,
    conversations,
    setConversations,
    setConversationId,
    loadHistory,
    newConversation,
  } = useCopilotStore();

  useEffect(() => {
    if (isOpen) {
      fetchConversations().then(setConversations);
    }
  }, [isOpen]);

  async function openConversation(id: string) {
    setConversationId(id);
    const msgs = await fetchHistory(id);
    loadHistory(msgs);
    openWindow();
  }

  function startNew() {
    newConversation();
    openWindow();
  }

  const visible = isOpen && !isWindowOpen;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="chat-tray"
          initial={{ x: 420, opacity: 0 }}
          animate={isClosing ? { x: 420, opacity: 0 } : { x: 0, opacity: 1 }}
          exit={{ x: 420, opacity: 0 }}
          transition={{ duration: 0.35, ease: [0.32, 0.72, 0, 1] }}
          className="fixed bottom-24 right-6 z-50 flex flex-col rounded-2xl overflow-hidden border border-white/10"
          style={{
            width: 340,
            maxHeight: 480,
            background: "rgba(10, 15, 30, 0.88)",
            backdropFilter: "blur(24px)",
            WebkitBackdropFilter: "blur(24px)",
            boxShadow: "0 0 30px rgba(0, 212, 255, 0.06), 0 20px 40px rgba(0,0,0,0.5)",
          }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/8">
            <div className="flex items-center gap-2">
              <span className="text-lg">🧠</span>
              <div>
                <p className="text-sm font-semibold text-white">AI Health Copilot</p>
                <p className="text-xs text-slate-500">Your personal health assistant</p>
              </div>
            </div>
            <button
              onClick={closeAll}
              className="p-1.5 rounded-lg text-slate-500 hover:text-white hover:bg-white/10 transition-all"
            >
              <X size={14} />
            </button>
          </div>

          {/* New chat button */}
          <div className="px-4 pt-3 pb-2">
            <button
              onClick={startNew}
              className="w-full flex items-center gap-2 px-4 py-2.5 rounded-xl
                         bg-cyan-500/15 border border-cyan-500/30 text-cyan-300
                         hover:bg-cyan-500/25 hover:border-cyan-400 transition-all text-sm font-medium"
            >
              <MessageSquarePlus size={16} />
              New conversation
            </button>
          </div>

          {/* Recent conversations */}
          {conversations.length > 0 && (
            <div className="flex-1 overflow-y-auto px-4 pb-4">
              <p className="text-xs text-slate-500 mb-2 flex items-center gap-1">
                <Clock size={10} /> Recent
              </p>
              <div className="space-y-1">
                {conversations.map((conv) => (
                  <button
                    key={conv.id}
                    onClick={() => openConversation(conv.id)}
                    className="w-full text-left px-3 py-2.5 rounded-xl bg-white/4 hover:bg-white/8
                               border border-white/5 hover:border-white/15 transition-all group"
                  >
                    <p className="text-sm text-slate-200 group-hover:text-white truncate">
                      {conv.title || "Untitled"}
                    </p>
                    <p className="text-xs text-slate-600 mt-0.5">
                      {new Date(conv.updatedAt).toLocaleDateString()}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {conversations.length === 0 && (
            <div className="px-4 pb-6 text-center">
              <p className="text-xs text-slate-600 mt-2">No conversations yet. Start a new one!</p>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
