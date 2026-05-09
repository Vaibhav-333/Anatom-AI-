"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Send, Plus, Trash2 } from "lucide-react";
import { useCopilotStore } from "@/lib/copilotStore";
import {
  streamCopilotChat,
  fetchSuggestedQuestions,
  deleteConversation,
  fetchConversations,
  checkAuth,
} from "@/lib/copilotApi";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import { SuggestedQuestions } from "./SuggestedQuestions";
import { VoiceInputButton } from "./VoiceInputButton";

export function ChatWindow() {
  const {
    isWindowOpen,
    isClosing,
    closeAll,
    messages,
    isStreaming,
    conversationId,
    currentReportId,
    currentPage,
    suggestedQuestions,
    setConversationId,
    addUserMessage,
    startStreamingMessage,
    appendStreamToken,
    finalizeStreamingMessage,
    setSuggestedQuestions,
    setConversations,
    newConversation,
  } = useCopilotStore();

  const [input, setInput] = useState("");
  const [notLoggedIn, setNotLoggedIn] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll on new content
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isStreaming]);

  // Load suggested questions when report changes
  useEffect(() => {
    if (currentReportId) {
      fetchSuggestedQuestions(currentReportId).then((qs) => {
        if (qs.length) setSuggestedQuestions(qs);
      });
    }
  }, [currentReportId]);

  const sendMessage = useCallback(
    async (text: string) => {
      const query = text.trim();
      if (!query || isStreaming) return;

      // Gate on auth before doing anything visible
      const authed = await checkAuth();
      if (!authed) {
        setNotLoggedIn(true);
        return;
      }
      setNotLoggedIn(false);

      setInput("");
      abortRef.current?.abort();
      abortRef.current = new AbortController();

      addUserMessage(query);
      const aiMsgId = startStreamingMessage();

      let convId = conversationId;

      await streamCopilotChat(
        {
          query,
          conversationId: convId,
          reportId: currentReportId,
          contextPage: currentPage,
        },
        {
          onInit: (id) => {
            convId = id;
            setConversationId(id);
          },
          onToken: (token) => appendStreamToken(aiMsgId, token),
          onSuggested: (qs) => setSuggestedQuestions(qs),
          onDone: () => {
            finalizeStreamingMessage(aiMsgId);
            fetchConversations().then(setConversations);
          },
          onError: (msg) => {
            const isAuthError =
              msg.toLowerCase().includes("authentication") ||
              msg.toLowerCase().includes("session") ||
              msg.toLowerCase().includes("unauthorized");
            if (isAuthError) {
              setNotLoggedIn(true);
              finalizeStreamingMessage(aiMsgId);
            } else {
              appendStreamToken(
                aiMsgId,
                `Sorry, something went wrong: ${msg}\n\n⚠️ This is health information, not medical advice.`
              );
              finalizeStreamingMessage(aiMsgId);
            }
          },
        },
        abortRef.current.signal
      );
    },
    [
      isStreaming,
      conversationId,
      currentReportId,
      currentPage,
      addUserMessage,
      startStreamingMessage,
      appendStreamToken,
      finalizeStreamingMessage,
      setSuggestedQuestions,
      setConversationId,
      setConversations,
    ]
  );

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  async function handleDelete() {
    if (!conversationId) return;
    await deleteConversation(conversationId);
    newConversation();
    fetchConversations().then(setConversations);
  }

  const showSuggested = messages.length === 0 || (!isStreaming && messages.length < 3);

  return (
    <AnimatePresence>
      {isWindowOpen && (
        <motion.div
          key="chat-window"
          initial={{ opacity: 0, scale: 0.92, y: 20 }}
          animate={
            isClosing
              ? { opacity: 0, scale: 0.88, y: 30 }
              : { opacity: 1, scale: 1, y: 0 }
          }
          exit={{ opacity: 0, scale: 0.88, y: 30 }}
          transition={{ duration: 0.32, ease: [0.32, 0.72, 0, 1] }}
          className="fixed bottom-24 right-6 z-50 flex flex-col"
          style={{ width: 380, height: 580 }}
        >
          <div
            className="flex flex-col h-full rounded-2xl overflow-hidden"
            style={{
              background: "var(--glass-bg)",
              backdropFilter: "blur(28px)",
              WebkitBackdropFilter: "blur(28px)",
              border: "1px solid var(--border-default)",
              boxShadow: "var(--glass-shadow-lg)",
            }}
          >
            {/* Header */}
            <div
              className="flex items-center gap-3 px-4 py-3 shrink-0"
              style={{ borderBottom: "1px solid var(--border-subtle)" }}
            >
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-white text-xs font-bold"
                style={{ background: "#0A84FF" }}
              >
                AI
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[13px] font-semibold" style={{ color: "var(--label-primary)" }}>AI Health Copilot</p>
                <p className="text-[11px] truncate" style={{ color: "var(--label-tertiary)" }}>
                  {isStreaming ? "Thinking…" : "Ask me anything about your health"}
                </p>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                {conversationId && (
                  <button
                    onClick={handleDelete}
                    title="Clear conversation"
                    className="p-1.5 rounded-lg transition-all"
                    style={{ color: "var(--nav-group-label)" }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLButtonElement).style.color = "#FF453A";
                      (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,69,58,0.10)";
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLButtonElement).style.color = "var(--nav-group-label)";
                      (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                    }}
                  >
                    <Trash2 size={14} />
                  </button>
                )}
                <button
                  onClick={newConversation}
                  title="New conversation"
                  className="p-1.5 rounded-lg transition-all"
                  style={{ color: "var(--nav-group-label)" }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.color = "#0A84FF";
                    (e.currentTarget as HTMLButtonElement).style.background = "rgba(10,132,255,0.10)";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.color = "var(--nav-group-label)";
                    (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                  }}
                >
                  <Plus size={14} />
                </button>
                <button
                  onClick={closeAll}
                  title="Close"
                  className="p-1.5 rounded-lg transition-all"
                  style={{ color: "var(--nav-group-label)" }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.color = "var(--label-primary)";
                    (e.currentTarget as HTMLButtonElement).style.background = "var(--bg-hover)";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.color = "var(--nav-group-label)";
                    (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                  }}
                >
                  <X size={14} />
                </button>
              </div>
            </div>

            {/* Messages */}
            <div
              ref={scrollRef}
              className="flex-1 overflow-y-auto px-4 py-4 space-y-1"
              style={{ scrollbarWidth: "thin", scrollbarColor: "var(--scrollbar-thumb) transparent" }}
            >
              {/* Session expired / not logged in */}
              {notLoggedIn && (
                <div className="flex flex-col items-center justify-center h-full text-center gap-4 px-4">
                  <div
                    className="w-14 h-14 rounded-full flex items-center justify-center text-2xl"
                    style={{ background: "rgba(255,69,58,0.12)" }}
                  >
                    🔒
                  </div>
                  <div>
                    <p className="text-white font-semibold text-sm mb-1">Session expired</p>
                    <p className="text-[12px] leading-relaxed" style={{ color: "#8E8E93" }}>
                      Please log in to continue chatting.
                    </p>
                  </div>
                  <a
                    href="/login"
                    className="px-5 py-2 rounded-xl text-white text-sm font-semibold transition-colors"
                    style={{ background: "#0A84FF" }}
                  >
                    Log in
                  </a>
                </div>
              )}

              {messages.length === 0 && !notLoggedIn && (
                <div className="flex flex-col items-center justify-center h-full text-center gap-4">
                  <div
                    className="w-14 h-14 rounded-full flex items-center justify-center text-2xl"
                    style={{ background: "rgba(10,132,255,0.12)" }}
                  >
                    🧠
                  </div>
                  <p className="text-[13px] leading-relaxed" style={{ color: "var(--label-secondary)" }}>
                    Hi! I&apos;m your AI health companion.
                    <br />
                    Ask me about your reports, symptoms, or lifestyle.
                  </p>
                </div>
              )}

              {messages.map((msg) =>
                msg.isStreaming && !msg.content ? (
                  <div key={msg.id} className="flex justify-start mb-3">
                    <div
                      className="w-7 h-7 rounded-full flex items-center justify-center text-white text-[10px] font-bold mr-2 mt-1 shrink-0"
                      style={{ background: "#0A84FF" }}
                    >
                      AI
                    </div>
                    <TypingIndicator />
                  </div>
                ) : (
                  <MessageBubble key={msg.id} message={msg} />
                )
              )}
            </div>

            {/* Suggested questions */}
            {showSuggested && (
              <SuggestedQuestions
                questions={suggestedQuestions}
                onSelect={(q) => sendMessage(q)}
              />
            )}

            {/* Disclaimer */}
            {!notLoggedIn && (
              <div className="px-4 py-1.5 shrink-0">
                <p className="text-[11px] text-center" style={{ color: "var(--label-tertiary)" }}>
                  ⚠️ Health information only — not medical advice
                </p>
              </div>
            )}

            {/* Input */}
            <div className="px-3 pb-3 shrink-0">
              <div
                className="flex items-end gap-2 rounded-xl px-3 py-2 transition-all"
                style={{
                  background: "var(--bg-input)",
                  border: "1px solid var(--border-default)",
                }}
                onFocusCapture={(e) => {
                  (e.currentTarget as HTMLDivElement).style.borderColor = "rgba(10,132,255,0.40)";
                  (e.currentTarget as HTMLDivElement).style.boxShadow = "0 0 0 3px rgba(10,132,255,0.08)";
                }}
                onBlurCapture={(e) => {
                  (e.currentTarget as HTMLDivElement).style.borderColor = "var(--border-default)";
                  (e.currentTarget as HTMLDivElement).style.boxShadow = "none";
                }}
              >
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask about your health…"
                  disabled={isStreaming}
                  rows={1}
                  className="flex-1 resize-none bg-transparent text-[13px] outline-none max-h-32 overflow-y-auto leading-relaxed disabled:opacity-50"
                  style={{
                    minHeight: "24px",
                    color: "var(--label-primary)",
                  }}
                />
                <VoiceInputButton
                  onTranscript={(t) =>
                    setInput((prev) => (prev ? prev + " " + t : t))
                  }
                  disabled={isStreaming}
                />
                <motion.button
                  onClick={() => sendMessage(input)}
                  disabled={!input.trim() || isStreaming}
                  whileTap={{ scale: 0.88 }}
                  className="p-2 rounded-lg text-white disabled:opacity-35 transition-colors shrink-0"
                  style={{ background: "#0A84FF" }}
                  onMouseEnter={(e) => { if (input.trim() && !isStreaming) (e.currentTarget as HTMLButtonElement).style.background = "#0A73E0"; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "#0A84FF"; }}
                >
                  <Send size={14} />
                </motion.button>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
