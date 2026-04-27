"use client";

import { useRef, KeyboardEvent, ClipboardEvent, ChangeEvent } from "react";

interface Props {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function OtpInput({ value, onChange, disabled }: Props) {
  const refs = useRef<(HTMLInputElement | null)[]>([]);
  const digits = value.padEnd(6, "").slice(0, 6).split("");

  function handleChange(index: number, e: ChangeEvent<HTMLInputElement>) {
    const char = e.target.value.replace(/\D/g, "").slice(-1);
    const next = digits.map((d, i) => (i === index ? char : d));
    onChange(next.join("").replace(/\s/g, ""));
    if (char && index < 5) refs.current[index + 1]?.focus();
  }

  function handleKeyDown(index: number, e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Backspace") {
      if (!digits[index] && index > 0) {
        refs.current[index - 1]?.focus();
        const next = digits.map((d, i) => (i === index - 1 ? "" : d));
        onChange(next.join("").trimEnd());
      } else {
        const next = digits.map((d, i) => (i === index ? "" : d));
        onChange(next.join("").trimEnd());
      }
    }
    if (e.key === "ArrowLeft" && index > 0) refs.current[index - 1]?.focus();
    if (e.key === "ArrowRight" && index < 5) refs.current[index + 1]?.focus();
  }

  function handlePaste(e: ClipboardEvent<HTMLInputElement>) {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    onChange(pasted);
    const focusIdx = Math.min(pasted.length, 5);
    refs.current[focusIdx]?.focus();
  }

  return (
    <div className="flex gap-3 justify-center" role="group" aria-label="OTP input">
      {Array.from({ length: 6 }).map((_, i) => (
        <input
          key={i}
          ref={(el) => { refs.current[i] = el; }}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={digits[i] ?? ""}
          onChange={(e) => handleChange(i, e)}
          onKeyDown={(e) => handleKeyDown(i, e)}
          onPaste={i === 0 ? handlePaste : undefined}
          onFocus={(e) => e.target.select()}
          disabled={disabled}
          aria-label={`OTP digit ${i + 1}`}
          className={`
            w-12 h-14 text-center text-xl font-bold rounded-xl border-2
            bg-slate-800/60 text-white caret-transparent
            outline-none transition-all duration-200
            ${digits[i]
              ? "border-cyan-400 shadow-[0_0_12px_rgba(34,211,238,0.3)]"
              : "border-slate-600 focus:border-cyan-500"
            }
            ${disabled ? "opacity-50 cursor-not-allowed" : ""}
          `}
        />
      ))}
    </div>
  );
}
