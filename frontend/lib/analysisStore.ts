// ─────────────────────────────────────────────────────────────────────────────
// analysisStore.ts — sessionStorage bridge between upload page and 3D viewer.
//
// The upload page saves an AnalysisResult after calling /interpret or
// /analyze-report. The viewer page reads it on mount, auto-highlights the
// affected organs, and then clears the store so repeated visits don't replay
// stale results.
// ─────────────────────────────────────────────────────────────────────────────

const STORE_KEY = "anatom_analysis_result"

// ─────────────────────────────────────────────────────────────────────────────
// Types (mirrors AnalyzeReportResponse from backend)
// ─────────────────────────────────────────────────────────────────────────────

export interface ConditionResult {
  name:            string
  confidence:      number      // 0.0 – 1.0
  affected_organs: string[]    // anatomical names e.g. ["Heart", "Liver"]
  severity:        string      // "mild" | "moderate" | "severe"
  description:     string
}

export interface StoredAnalysis {
  conditions:  ConditionResult[]
  summary:     string
  risk_level:  string           // "low" | "moderate" | "high" | "critical"
  organ_keys:  string[]         // resolved mesh keys, most severe first
  source:      "ai" | "fallback"
  timestamp:   number           // Date.now() at save time
}

// ─────────────────────────────────────────────────────────────────────────────
// API
// ─────────────────────────────────────────────────────────────────────────────

/** Persist an analysis result so the viewer can load it on navigation. */
export function saveAnalysis(result: StoredAnalysis): void {
  if (typeof window === "undefined") return
  try {
    sessionStorage.setItem(STORE_KEY, JSON.stringify(result))
  } catch {
    // sessionStorage may be unavailable in some private-browsing modes
  }
}

/** Read the stored analysis. Returns null if nothing is stored. */
export function loadAnalysis(): StoredAnalysis | null {
  if (typeof window === "undefined") return null
  try {
    const raw = sessionStorage.getItem(STORE_KEY)
    return raw ? (JSON.parse(raw) as StoredAnalysis) : null
  } catch {
    return null
  }
}

/** Remove the stored analysis (call after consuming it in the viewer). */
export function clearAnalysis(): void {
  if (typeof window === "undefined") return
  try {
    sessionStorage.removeItem(STORE_KEY)
  } catch { /* ignore */ }
}
