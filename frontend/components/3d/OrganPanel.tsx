"use client";

import React from "react";
import { X, ExternalLink } from "lucide-react";
import { ORGAN_DISPLAY_DATA } from "@/lib/organRegistry";

// ─────────────────────────────────────────────────────────────────────────────
// LINKIFY
// Wraps recognised medical terms with Wikipedia anchor links.
// ─────────────────────────────────────────────────────────────────────────────
const LINK_TERMS = [
  "blood", "oxygen", "artery", "vein", "tissue", "bile",
  "insulin", "glucagon", "urine", "neuron", "enzyme",
];

function linkify(text: string): React.ReactNode[] {
  const pattern = new RegExp(`\\b(${LINK_TERMS.join("|")})\\b`, "gi");
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index));
    parts.push(
      <a
        key={key++}
        href={`https://en.wikipedia.org/wiki/${encodeURIComponent(match[0].toLowerCase())}`}
        target="_blank"
        rel="noopener noreferrer"
        className="text-cyan-400 hover:text-cyan-300 underline underline-offset-2 transition-colors"
      >
        {match[0]}
      </a>
    );
    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts;
}

// ─────────────────────────────────────────────────────────────────────────────

interface OrganPanelProps {
  organ: string | null;
  onClose: () => void;
}

export function OrganPanel({ organ, onClose }: OrganPanelProps) {
  if (!organ) return null;
  const info = ORGAN_DISPLAY_DATA[organ];
  if (!info) return null;

  return (
    <div className="absolute top-4 right-4 w-72 rounded-xl border border-white/10 bg-navy-800/90 backdrop-blur-md shadow-xl animate-fade-in flex flex-col overflow-hidden max-h-[80vh]">
      {/* ── Scrollable body ── */}
      <div className="overflow-y-auto p-4 flex flex-col gap-3">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span
              className="w-3 h-3 rounded-full shrink-0"
              style={{ backgroundColor: info.color }}
            />
            <span className="text-sm font-semibold text-white">{info.label}</span>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-300 transition-colors"
            aria-label="Close panel"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* System badge */}
        <p className="text-xs text-slate-400 uppercase tracking-wider">{info.system}</p>

        <div className="h-px bg-white/5" />

        {/* Description with linkified terms */}
        <div>
          <p className="text-xs text-slate-500 mb-1 font-medium">DESCRIPTION</p>
          <p className="text-sm text-slate-300 leading-relaxed">
            {linkify(info.description)}
          </p>
        </div>

        <div className="h-px bg-white/5" />

        {/* Key functions */}
        <div>
          <p className="text-xs text-slate-500 mb-2 font-medium">KEY FUNCTIONS</p>
          <ul className="flex flex-col gap-1.5">
            {info.functions.map((fn, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                <span className="mt-1.5 w-1 h-1 rounded-full shrink-0" style={{ backgroundColor: info.color }} />
                {linkify(fn)}
              </li>
            ))}
          </ul>
        </div>

        {/* Disease relevance */}
        {info.diseases && info.diseases.length > 0 && (
          <>
            <div className="h-px bg-white/5" />
            <div>
              <p className="text-xs text-slate-500 mb-2 font-medium">ASSOCIATED CONDITIONS</p>
              <div className="flex flex-wrap gap-1.5">
                {info.diseases.map((d, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 rounded-full text-xs border border-white/10 bg-white/5 text-slate-400"
                  >
                    {d}
                  </span>
                ))}
              </div>
            </div>
          </>
        )}

        <div className="h-px bg-white/5" />

        {/* Wikipedia link */}
        <a
          href={info.wiki}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 transition-colors font-medium"
        >
          <ExternalLink className="w-3 h-3" />
          Learn more on Wikipedia
        </a>
      </div>
    </div>
  );
}
