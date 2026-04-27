"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain,
  Loader2,
  SkipForward,
  ChevronRight,
  AlertCircle,
} from "lucide-react";
import type { InterpretResponse } from "@/lib/types";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface DiagQuestion {
  text: string;
  type: "multiple_choice" | "boolean" | "slider" | "text";
  options?: string[];
  min_label?: string;
  max_label?: string;
  question_number: number;
  total_questions: number;
}

export interface QAEntry {
  question: string;
  answer: string;
}

interface ChatMessage {
  role: "ai" | "user";
  text: string;
}

interface Props {
  initialAnalysis: InterpretResponse;
  onComplete: (qaHistory: QAEntry[]) => void;
}

// ─── Fallback questions (used when Gemini API is unavailable) ────────────────
// These fire only when the /diagnostic/question endpoint returns done=true
// or fails on the very first question, ensuring the interview always runs.

const FALLBACK_QUESTIONS: DiagQuestion[] = [
  {
    text: "How long have you been experiencing the symptoms or concerns mentioned in this report?",
    type: "multiple_choice",
    options: ["Less than 1 week", "1–4 weeks", "1–3 months", "More than 3 months"],
    question_number: 1,
    total_questions: 4,
  },
  {
    text: "On a scale of 1–10, how severe is your discomfort or the symptoms you are feeling right now?",
    type: "slider",
    min_label: "1 — Very mild",
    max_label: "10 — Very severe",
    question_number: 2,
    total_questions: 4,
  },
  {
    text: "Do you have any pre-existing medical conditions or take any regular medications?",
    type: "multiple_choice",
    options: [
      "No known conditions or medications",
      "Diabetes or thyroid-related issues",
      "Heart disease or blood pressure problems",
      "Other chronic condition",
    ],
    question_number: 3,
    total_questions: 4,
  },
  {
    text: "Are you currently experiencing any of the following warning signs?",
    type: "multiple_choice",
    options: [
      "Chest pain or tightness",
      "Shortness of breath or dizziness",
      "Persistent fatigue or weakness",
      "None of the above",
    ],
    question_number: 4,
    total_questions: 4,
  },
];

// ─── Risk helpers ─────────────────────────────────────────────────────────────

const RISK_COLOR: Record<string, string> = {
  low: "text-green-400 bg-green-400/10 border-green-400/30",
  moderate: "text-amber-400 bg-amber-400/10 border-amber-400/30",
  high: "text-red-400 bg-red-400/10 border-red-400/30",
  critical: "text-red-500 bg-red-500/10 border-red-500/30",
};

// ─── Component ────────────────────────────────────────────────────────────────

export function DiagnosticChat({ initialAnalysis, onComplete }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState<DiagQuestion | null>(null);
  const [qaHistory, setQaHistory] = useState<QAEntry[]>([]);
  const [sliderVal, setSliderVal] = useState(5);
  const [textInput, setTextInput] = useState("");
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Fallback mode — activated when Gemini question API is unavailable
  const [fallbackMode, setFallbackMode] = useState(false);
  const [fallbackIdx, setFallbackIdx] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, currentQuestion]);

  // Fetch first question on mount
  useEffect(() => {
    fetchQuestion([]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function fetchQuestion(history: QAEntry[]) {
    // ── Fallback mode: serve the next pre-built question without hitting the API ──
    if (fallbackMode) {
      const idx = fallbackIdx;
      if (idx < FALLBACK_QUESTIONS.length) {
        const q = FALLBACK_QUESTIONS[idx];
        setFallbackIdx(idx + 1);
        setCurrentQuestion(q);
        setMessages((prev) => [...prev, { role: "ai", text: q.text }]);
      } else {
        onComplete(history);
      }
      return;
    }

    setFetching(true);
    setError(null);
    let activateFallback = false;

    try {
      const res = await fetch("/api/diagnostic/question", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          report_type: initialAnalysis.report_type,
          summary: initialAnalysis.summary,
          findings: initialAnalysis.findings,
          regions: initialAnalysis.affected_regions,
          risk_level: initialAnalysis.risk_level,
          qa_history: history,
        }),
      });
      if (!res.ok) throw new Error("Failed to fetch question");
      const data = await res.json();

      if (data.done || !data.question) {
        if (history.length === 0) {
          // API returned done before any questions — switch to fallback so
          // the interview always runs at least 4 questions
          activateFallback = true;
        } else {
          onComplete(history);
        }
      } else {
        setCurrentQuestion(data.question);
        setMessages((prev) => [...prev, { role: "ai", text: data.question.text }]);
      }
    } catch {
      if (history.length === 0) {
        // First question failed — switch to fallback silently
        activateFallback = true;
      } else {
        setError("Could not load next question. You can skip to the report.");
      }
    } finally {
      setFetching(false);
    }

    // Activate fallback after state updates settle (outside try/catch)
    if (activateFallback) {
      setFallbackMode(true);
      setFallbackIdx(1);
      const q = FALLBACK_QUESTIONS[0];
      setCurrentQuestion(q);
      setMessages((prev) => [...prev, { role: "ai", text: q.text }]);
    }
  }

  function submitAnswer(answer: string) {
    if (!currentQuestion || !answer.trim()) return;
    const newEntry: QAEntry = { question: currentQuestion.text, answer };
    const newHistory = [...qaHistory, newEntry];
    setQaHistory(newHistory);
    setMessages((prev) => [...prev, { role: "user", text: answer }]);
    setCurrentQuestion(null);
    setSliderVal(5);
    setTextInput("");
    fetchQuestion(newHistory);
  }

  function handleSkip() {
    onComplete(qaHistory);
  }

  const progress = qaHistory.length > 0
    ? Math.round((qaHistory.length / (currentQuestion?.total_questions ?? 5)) * 100)
    : 0;

  const riskStyle = RISK_COLOR[initialAnalysis.risk_level] ?? RISK_COLOR.low;

  return (
    <div className="flex flex-col h-full max-w-2xl mx-auto">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="mb-4 space-y-3">
        {/* Compact initial-analysis banner */}
        <div className={`flex items-center justify-between px-4 py-3 rounded-xl border ${riskStyle}`}>
          <div className="flex items-center gap-2.5">
            <Brain className="w-4 h-4 shrink-0" />
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider">Initial Analysis</p>
              <p className="text-xs opacity-80 mt-0.5 line-clamp-1">{initialAnalysis.summary}</p>
            </div>
          </div>
          <span className="text-xs font-mono capitalize px-2 py-0.5 rounded border opacity-60 border-current shrink-0">
            {initialAnalysis.risk_level} risk
          </span>
        </div>

        {/* Progress bar */}
        {qaHistory.length > 0 && (
          <div>
            <div className="flex justify-between text-xs text-slate-500 mb-1">
              <span>Diagnostic Interview</span>
              <span>{qaHistory.length}/{currentQuestion?.total_questions ?? 5} questions</span>
            </div>
            <div className="h-1.5 bg-navy-700 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-cyan rounded-full"
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.4 }}
              />
            </div>
          </div>
        )}
      </div>

      {/* ── Chat messages ───────────────────────────────────────────── */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-3 pr-1 pb-4 min-h-[200px] max-h-[40vh]"
      >
        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-2.5 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
            >
              {msg.role === "ai" && (
                <div className="w-8 h-8 rounded-xl bg-cyan/10 border border-cyan/30 flex items-center justify-center shrink-0 mt-0.5">
                  <Brain className="w-4 h-4 text-cyan" />
                </div>
              )}
              <div
                className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                  msg.role === "ai"
                    ? "bg-navy-700 border border-glass-border text-slate-200 rounded-tl-sm"
                    : "bg-cyan/10 border border-cyan/20 text-cyan rounded-tr-sm"
                }`}
              >
                {msg.text}
              </div>
            </motion.div>
          ))}

          {/* AI typing indicator */}
          {fetching && (
            <motion.div
              key="typing"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex gap-2.5"
            >
              <div className="w-8 h-8 rounded-xl bg-cyan/10 border border-cyan/30 flex items-center justify-center shrink-0">
                <Brain className="w-4 h-4 text-cyan" />
              </div>
              <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-navy-700 border border-glass-border">
                <div className="flex gap-1.5 items-center">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan/60 animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan/60 animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan/60 animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Answer input area ───────────────────────────────────────── */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex items-center gap-2 text-sm text-amber-400 bg-amber-400/10 border border-amber-400/20 rounded-xl px-4 py-2.5 mb-3"
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error}
          </motion.div>
        )}

        {currentQuestion && !fetching && (
          <motion.div
            key={currentQuestion.question_number}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="border border-glass-border rounded-2xl bg-navy-800/60 p-4 space-y-3"
          >
            {/* Multiple choice / boolean */}
            {(currentQuestion.type === "multiple_choice" || currentQuestion.type === "boolean") &&
              currentQuestion.options && (
                <div className="flex flex-wrap gap-2">
                  {currentQuestion.options.map((opt) => (
                    <button
                      key={opt}
                      onClick={() => submitAnswer(opt)}
                      className="px-4 py-2 rounded-xl border border-glass-border text-sm text-slate-300
                                 hover:border-cyan/40 hover:bg-cyan/5 hover:text-cyan transition-all"
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              )}

            {/* Slider */}
            {currentQuestion.type === "slider" && (
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500 w-20 text-right">
                    {currentQuestion.min_label ?? "1 — Mild"}
                  </span>
                  <input
                    type="range"
                    min={1}
                    max={10}
                    value={sliderVal}
                    onChange={(e) => setSliderVal(parseInt(e.target.value))}
                    className="flex-1 accent-cyan"
                  />
                  <span className="text-xs text-slate-500 w-20">
                    {currentQuestion.max_label ?? "10 — Severe"}
                  </span>
                </div>
                <div className="text-center">
                  <span className="text-2xl font-bold text-cyan">{sliderVal}</span>
                  <span className="text-slate-500 text-sm"> / 10</span>
                </div>
                <button
                  onClick={() => submitAnswer(`${sliderVal}/10`)}
                  className="w-full py-2.5 rounded-xl bg-cyan/10 border border-cyan/30 text-cyan font-medium text-sm
                             hover:bg-cyan/20 transition-colors flex items-center justify-center gap-2"
                >
                  Confirm <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* Free text */}
            {currentQuestion.type === "text" && (
              <div className="flex gap-2">
                <input
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && textInput.trim() && submitAnswer(textInput.trim())}
                  placeholder="Type your answer…"
                  className="flex-1 bg-navy-700 border border-glass-border rounded-xl px-4 py-2.5 text-sm text-white
                             placeholder:text-slate-500 focus:outline-none focus:border-cyan/40 transition-colors"
                />
                <button
                  onClick={() => textInput.trim() && submitAnswer(textInput.trim())}
                  disabled={!textInput.trim()}
                  className="px-4 py-2.5 rounded-xl bg-cyan text-navy-900 font-bold text-sm
                             hover:bg-cyan/90 transition-colors disabled:opacity-40"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Skip button ─────────────────────────────────────────────── */}
      <div className="mt-3 flex justify-end">
        <button
          onClick={handleSkip}
          disabled={fetching}
          className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors disabled:opacity-40"
        >
          <SkipForward className="w-3.5 h-3.5" />
          Skip to report
        </button>
      </div>
    </div>
  );
}
