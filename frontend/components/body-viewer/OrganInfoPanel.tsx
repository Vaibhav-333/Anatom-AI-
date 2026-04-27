"use client";

import { useMemo } from "react";
import { X, ExternalLink } from "lucide-react";
import { ORGAN_DISPLAY_DATA } from "@/lib/organRegistry";
import { DISEASE_MAP } from "@/lib/diseaseRegistry";

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Returns the first meaningful sentence of a description.
 * Falls back to the whole string if no sentence break is found.
 */
function firstSentence(text: string): string {
  const idx = text.indexOf(". ");
  if (idx === -1 || idx < 40) return text;           // too short → show all
  return text.slice(0, idx + 1);
}

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

interface OrganInfoPanelProps {
  organ:            string | null;
  detectedDisease?: string | null;   // set by disease scan; drives the alert card
  onClose:          () => void;
}

export function OrganInfoPanel({ organ, detectedDisease, onClose }: OrganInfoPanelProps) {
  const info = useMemo(
    () => (organ ? (ORGAN_DISPLAY_DATA[organ] ?? null) : null),
    [organ],
  );

  // Try registry lookup first (exact key match); fall back to case-insensitive search.
  // AI returns free-form names like "Arrhythmia" — try to match against registry keys.
  // MUST be declared before any early return to satisfy Rules of Hooks.
  const diseaseInfo = useMemo(() => {
    if (!detectedDisease) return null;
    // Direct key match (keyword-based fallback)
    if (DISEASE_MAP[detectedDisease]) return DISEASE_MAP[detectedDisease];
    // Case-insensitive key match
    const lower = detectedDisease.toLowerCase();
    const matchKey = Object.keys(DISEASE_MAP).find(
      (k) => k.replace(/_/g, " ") === lower || k === lower
    );
    return matchKey ? DISEASE_MAP[matchKey] : null;
  }, [detectedDisease]);

  // No organ selected, or organ has no entry (e.g. bone in arthrology model)
  if (!info) return null;

  const shortDesc = firstSentence(info.description);

  return (
    // animate-fade-in is defined globally (same class used by OrganPanel)
    <div className="w-64 rounded-xl border border-white/10 bg-navy-800/90 backdrop-blur-md shadow-xl animate-fade-in overflow-hidden">
      <div className="p-3 flex flex-col gap-2.5 overflow-y-auto max-h-[80vh]">

        {/* ── Disease alert card ── */}
        {/* Shows registry data when available; otherwise shows AI name as plain label */}
        {detectedDisease && (diseaseInfo ? (
          <>
            <div
              className="rounded-lg border p-2.5 flex flex-col gap-1.5"
              style={{
                borderColor: diseaseInfo.color + "55",
                background:  diseaseInfo.color + "14",
              }}
            >
              {/* Disease header */}
              <div className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ background: diseaseInfo.color }}
                />
                <span className="text-xs font-semibold text-white leading-tight">
                  {diseaseInfo.label}
                </span>
              </div>

              {/* System badge */}
              <p className="text-[9px] font-medium text-slate-500 uppercase tracking-widest">
                {diseaseInfo.system}
              </p>

              {/* Clinical description */}
              <p className="text-[11px] text-slate-400 leading-relaxed">
                {diseaseInfo.description}
              </p>

              {/* Wikipedia link */}
              <a
                href={diseaseInfo.wiki}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-[10px] text-cyan-400 hover:text-cyan-300 transition-colors font-medium"
              >
                <ExternalLink className="w-2.5 h-2.5 shrink-0" />
                Learn more on Wikipedia
              </a>
            </div>

            <div className="h-px bg-white/5" />
          </>
        ) : (
          /* AI free-form disease name — no registry entry found */
          <>
            <div className="rounded-lg border border-amber/20 bg-amber/8 p-2.5 flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full shrink-0 bg-amber" />
                <span className="text-xs font-semibold text-white leading-tight">
                  {detectedDisease}
                </span>
              </div>
              <p className="text-[10px] text-slate-500 leading-snug">
                Detected condition — see full report for details.
              </p>
            </div>
            <div className="h-px bg-white/5" />
          </>
        ))}

        {/* ── Header: color dot + name + close ── */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span
              className="w-2.5 h-2.5 rounded-full shrink-0"
              style={{ backgroundColor: info.color }}
            />
            <span className="text-sm font-semibold text-white truncate leading-tight">
              {info.label}
            </span>
          </div>
          <button
            onClick={onClose}
            className="shrink-0 text-slate-500 hover:text-slate-300 transition-colors"
            aria-label="Close panel"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* ── System badge ── */}
        <p className="text-[10px] font-medium text-slate-500 uppercase tracking-widest leading-none">
          {info.system}
        </p>

        <div className="h-px bg-white/6" />

        {/* ── Short description ── */}
        <p className="text-xs text-slate-300 leading-relaxed">
          {shortDesc}
        </p>

        {/* ── Key functions (first 2 only — keep panel compact) ── */}
        {info.functions.length > 0 && (
          <>
            <div className="h-px bg-white/6" />
            <ul className="flex flex-col gap-1.5">
              {info.functions.slice(0, 2).map((fn, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span
                    className="mt-[5px] w-1 h-1 rounded-full shrink-0"
                    style={{ backgroundColor: info.color }}
                  />
                  <span className="text-xs text-slate-400 leading-snug">{fn}</span>
                </li>
              ))}
            </ul>
          </>
        )}

        {/* ── Associated conditions (tags) ── */}
        {info.diseases && info.diseases.length > 0 && (
          <>
            <div className="h-px bg-white/6" />
            <div className="flex flex-wrap gap-1">
              {info.diseases.slice(0, 3).map((d, i) => (
                <span
                  key={i}
                  className="px-1.5 py-0.5 rounded text-[9px] border border-white/8 bg-white/4 text-slate-500 leading-none"
                >
                  {d}
                </span>
              ))}
            </div>
          </>
        )}

        {/* ── Wikipedia link ── */}
        <a
          href={info.wiki}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-[10px] text-cyan-500 hover:text-cyan-400 transition-colors font-medium mt-0.5"
        >
          <ExternalLink className="w-2.5 h-2.5 shrink-0" />
          Read more
        </a>

      </div>
    </div>
  );
}
