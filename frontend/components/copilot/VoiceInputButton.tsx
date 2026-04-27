"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Mic, Square } from "lucide-react";

interface Props {
  onTranscript: (text: string) => void;
  disabled?: boolean;
}

export function VoiceInputButton({ onTranscript, disabled }: Props) {
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [interimText, setInterimText] = useState("");

  const recogRef = useRef<any>(null);
  const finalRef = useRef<string>("");
  // Ref mirrors isListening so event handlers always see the current value (no stale closure)
  const shouldListenRef = useRef(false);

  useEffect(() => {
    const SR =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    setIsSupported(!!SR);
  }, []);

  function buildRecognition() {
    const SR =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (!SR) return null;

    const r = new SR();
    r.lang = "en-US";
    r.continuous = true;       // keep going through pauses
    r.interimResults = true;   // show live text
    r.maxAlternatives = 1;

    r.onresult = (e: any) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) {
          finalRef.current += e.results[i][0].transcript + " ";
        } else {
          interim += e.results[i][0].transcript;
        }
      }
      setInterimText(finalRef.current + interim);
    };

    r.onerror = (e: any) => {
      if (e.error === "no-speech") return; // benign — onend will restart
      // Real error — stop everything
      shouldListenRef.current = false;
      setIsListening(false);
      setInterimText("");
    };

    r.onend = () => {
      // Auto-restart only if the user hasn't clicked Stop
      if (shouldListenRef.current) {
        try {
          r.start();
        } catch {
          /* recognition already starting */
        }
      }
    };

    return r;
  }

  function startListening() {
    const r = buildRecognition();
    if (!r) return;

    finalRef.current = "";
    setInterimText("");
    shouldListenRef.current = true;
    recogRef.current = r;
    r.start();
    setIsListening(true);
  }

  function stopListening() {
    // Clear the flag FIRST so onend doesn't restart
    shouldListenRef.current = false;

    if (recogRef.current) {
      recogRef.current.onend = null; // prevent any pending onend from restarting
      try { recogRef.current.stop(); } catch { /* already stopped */ }
      recogRef.current = null;
    }

    const transcript = finalRef.current.trim();
    finalRef.current = "";
    setIsListening(false);
    setInterimText("");

    if (transcript) onTranscript(transcript);
  }

  if (!isSupported) return null;

  return (
    <div className="relative flex flex-col items-center">
      <motion.button
        onClick={isListening ? stopListening : startListening}
        disabled={disabled}
        whileTap={{ scale: 0.88 }}
        className={`relative p-2 rounded-full transition-all ${
          isListening
            ? "bg-red-500/20 border border-red-500/60 text-red-400"
            : "bg-white/5 border border-white/10 text-slate-400 hover:text-cyan-400 hover:border-cyan-500/40"
        } disabled:opacity-40`}
        title={isListening ? "Tap to stop & send" : "Tap to speak"}
      >
        {isListening ? (
          <>
            <Square size={16} />
            <motion.span
              className="absolute inset-0 rounded-full bg-red-500/20"
              animate={{ scale: [1, 1.6, 1], opacity: [0.7, 0, 0.7] }}
              transition={{ duration: 1, repeat: Infinity }}
            />
          </>
        ) : (
          <Mic size={16} />
        )}
      </motion.button>

      {/* Live transcript preview bubble */}
      {isListening && interimText && (
        <div
          className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 z-20
                     bg-[#0a0f1e]/95 border border-white/10 rounded-xl px-3 py-2
                     text-xs text-cyan-200 max-w-[220px] text-center shadow-xl
                     backdrop-blur-md whitespace-pre-wrap leading-relaxed"
          style={{ width: "max-content" }}
        >
          {interimText}
          <span className="inline-block w-0.5 h-3 bg-cyan-400 ml-0.5 animate-pulse align-middle" />
        </div>
      )}
    </div>
  );
}
