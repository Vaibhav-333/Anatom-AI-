"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Volume2, VolumeX } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { CopilotMessage } from "@/lib/copilotStore";

const CHARS_PER_TICK = 2;
const TICK_MS = 16;

interface Props {
  message: CopilotMessage;
}

export function MessageBubble({ message }: Props) {
  const isAI = message.role === "assistant";
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [ttsSupported, setTtsSupported] = useState(false);

  const [displayed, setDisplayed] = useState(
    message.isStreaming ? "" : message.content
  );
  const [isTypingLocally, setIsTypingLocally] = useState(message.isStreaming);

  const posRef = useRef(message.isStreaming ? 0 : message.content.length);
  const contentRef = useRef(message.content);
  const isStreamingRef = useRef(message.isStreaming);
  contentRef.current = message.content;
  isStreamingRef.current = message.isStreaming;

  useEffect(() => {
    if (!isStreamingRef.current && posRef.current >= contentRef.current.length) {
      return;
    }
    const id = setInterval(() => {
      const full = contentRef.current;
      const cur = posRef.current;
      if (cur < full.length) {
        const next = Math.min(cur + CHARS_PER_TICK, full.length);
        posRef.current = next;
        setDisplayed(full.slice(0, next));
      } else if (!isStreamingRef.current) {
        clearInterval(id);
        setDisplayed(contentRef.current);
        setIsTypingLocally(false);
      }
    }, TICK_MS);
    return () => clearInterval(id);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    setTtsSupported("speechSynthesis" in window);
  }, []);

  function toggleSpeak() {
    if (!window.speechSynthesis) return;
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }
    const u = new SpeechSynthesisUtterance(message.content);
    u.rate = 0.95;
    u.pitch = 1;
    u.onend = () => setIsSpeaking(false);
    u.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(u);
    setIsSpeaking(true);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className={`flex ${isAI ? "justify-start" : "justify-end"} mb-3`}
    >
      {isAI && (
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center text-white text-[10px] font-bold mr-2 mt-1 shrink-0"
          style={{ background: "#0A84FF" }}
        >
          AI
        </div>
      )}

      <div className="max-w-[82%] group">
        <div
          className={`px-4 py-3 text-[13px] leading-relaxed ${
            isAI ? "rounded-2xl rounded-tl-sm" : "rounded-2xl rounded-tr-sm whitespace-pre-wrap"
          }`}
          style={
            isAI
              ? { background: "var(--bg-elevated)", color: "var(--label-primary)" }
              : {
                  background: "linear-gradient(135deg, #0A84FF 0%, #0066CC 100%)",
                  color: "#FFFFFF",
                }
          }
        >
          {isAI ? (
            <>
              <ReactMarkdown
                components={{
                  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                  strong: ({ children }) => (
                    <strong className="font-semibold" style={{ color: "var(--label-primary)" }}>{children}</strong>
                  ),
                  em: ({ children }) => (
                    <em style={{ color: "#64D2FF" }}>{children}</em>
                  ),
                  ul: ({ children }) => (
                    <ul className="list-disc pl-4 mb-2 space-y-0.5">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal pl-4 mb-2 space-y-0.5">{children}</ol>
                  ),
                  li: ({ children }) => (
                    <li style={{ color: "var(--label-secondary)" }}>{children}</li>
                  ),
                  code: ({ children }) => (
                    <code
                      className="px-1 py-0.5 rounded text-xs font-mono"
                      style={{ background: "var(--bg-elevated)", color: "#64D2FF" }}
                    >
                      {children}
                    </code>
                  ),
                }}
              >
                {displayed}
              </ReactMarkdown>
              {isTypingLocally && (
                <span className="streaming-cursor" aria-hidden="true" />
              )}
            </>
          ) : (
            message.content
          )}
        </div>

        {isAI && !isTypingLocally && ttsSupported && message.content && (
          <button
            onClick={toggleSpeak}
            className="mt-1 ml-1 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 text-[11px]"
            style={{ color: "var(--label-tertiary)" }}
            title={isSpeaking ? "Stop" : "Listen"}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "#0A84FF"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "var(--label-tertiary)"; }}
          >
            {isSpeaking ? <VolumeX size={12} /> : <Volume2 size={12} />}
            <span>{isSpeaking ? "Stop" : "Listen"}</span>
          </button>
        )}
      </div>
    </motion.div>
  );
}
