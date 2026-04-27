"use client";

import React, { useMemo } from "react";
import { MEDICAL_TERMS, SORTED_TERMS } from "@/lib/medicalTerms";

const MAX_LINKS = 8; // Maximum clickable links rendered per text block

// ── Text segment types ──────────────────────────────────────────────────────

interface PlainSegment {
  kind: "plain";
  text: string;
}

interface LinkedSegment {
  kind: "link";
  text: string;
  slug: string;
}

type Segment = PlainSegment | LinkedSegment;

// ── Core parser ─────────────────────────────────────────────────────────────

/**
 * Parse `text` into an array of plain and linked segments.
 * Matching is case-insensitive and word-boundary aware.
 * Long-form terms are matched before single-word terms (SORTED_TERMS is
 * pre-sorted longest-first).
 */
function parseSegments(text: string): Segment[] {
  if (!text) return [];

  // We'll walk through the text, building segments greedily
  const result: Segment[] = [];
  let remaining = text;
  let offset = 0;

  while (remaining.length > 0) {
    let matched = false;

    for (const term of SORTED_TERMS) {
      // Build a word-boundary regex for this term
      // Escape special regex chars in the term
      const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const regex = new RegExp(`(?<![a-zA-Z])(${escaped})(?![a-zA-Z])`, "i");
      const match = regex.exec(remaining);

      if (match && match.index !== undefined) {
        // Everything before the match is plain text
        if (match.index > 0) {
          result.push({ kind: "plain", text: remaining.slice(0, match.index) });
        }
        result.push({
          kind: "link",
          text: match[0], // preserve original capitalisation
          slug: MEDICAL_TERMS[term],
        });
        remaining = remaining.slice(match.index + match[0].length);
        matched = true;
        break;
      }
    }

    if (!matched) {
      // No more matches — push the rest as plain text
      result.push({ kind: "plain", text: remaining });
      remaining = "";
    }
  }

  return result;
}

// ── Component ───────────────────────────────────────────────────────────────

interface LinkedMedicalTextProps {
  text: string;
  className?: string;
}

export function LinkedMedicalText({ text, className }: LinkedMedicalTextProps) {
  const segments = useMemo(() => parseSegments(text), [text]);

  // Enforce the MAX_LINKS cap — render only the first N links
  let linkCount = 0;

  return (
    <span className={className}>
      {segments.map((seg, i) => {
        if (seg.kind === "plain") {
          return <React.Fragment key={i}>{seg.text}</React.Fragment>;
        }

        // Cap links
        if (linkCount >= MAX_LINKS) {
          return <React.Fragment key={i}>{seg.text}</React.Fragment>;
        }

        linkCount++;
        const url = `https://en.wikipedia.org/wiki/${seg.slug}`;

        return (
          <a
            key={i}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-cyan/80 hover:text-cyan underline underline-offset-2 decoration-cyan/30 hover:decoration-cyan transition-colors duration-150 cursor-pointer"
            title={`Read about "${seg.text}" on Wikipedia`}
          >
            {seg.text}
          </a>
        );
      })}
    </span>
  );
}
