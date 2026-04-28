"use client";

import { Suspense, useRef, useState, useCallback, useEffect, useMemo } from "react";
import type { Vector3 } from "three";
import { Canvas, useThree } from "@react-three/fiber";
import { Environment, ContactShadows, useGLTF } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import { ChevronDown } from "lucide-react";
import { SkeletonModel } from "./SkeletonModel";
import { CameraController } from "./CameraController";
import { OrganInfoPanel } from "../body-viewer/OrganInfoPanel";
import { resolveOrganKey, severityColor, riskColor } from "@/lib/organMap";
import { loadAnalysis, clearAnalysis, type StoredAnalysis } from "@/lib/analysisStore";
import { DISEASE_MAP, extractDisease } from "@/lib/diseaseRegistry";   // fallback only
import { ExtractedOrgan, ORGAN_MODEL_MAP } from "./ExtractedOrgan";

// ── Model registry ────────────────────────────────────────────────────────────
type ModelKey = "full" | "neurology" | "arthrology" | "myology";
type SystemKey = "all" | "cardiovascular" | "respiratory" | "digestive" | "reproductive" | "excretory";

// myology.glb is 153 MB — too large for GitHub (>100 MB hard limit) and
// Vercel static assets (>100 MB). In production set NEXT_PUBLIC_MYOLOGY_GLB_URL
// to a CDN URL (e.g. a GitHub Release asset). Locally it falls back to public/.
const MODEL_PATH_MAP: Record<ModelKey, string> = {
  full:       "/assets/anatomy/sekeleton_with_heart,stomach,liver,gallbladder,lungs,brain.glb",
  neurology:  "/assets/anatomy/neurology.glb",
  arthrology: "/assets/anatomy/arthrology.glb",
  myology:    process.env.NEXT_PUBLIC_MYOLOGY_GLB_URL ?? "/assets/anatomy/myology.glb",
};

const MODEL_LABELS: Record<ModelKey, string> = {
  full:       "Full Body",
  neurology:  "Neurology",
  arthrology: "Arthrology",
  myology:    "Myology",
};

const SYSTEM_LABELS: Record<SystemKey, string> = {
  all:            "All",
  cardiovascular: "Cardiovascular",
  respiratory:    "Respiratory",
  digestive:      "Digestive",
  reproductive:   "Reproductive",
  excretory:      "Excretory",
};

const MODEL_KEYS  = Object.keys(MODEL_LABELS)  as ModelKey[];
const SYSTEM_KEYS = Object.keys(SYSTEM_LABELS) as SystemKey[];

// Preload only the default model eagerly; defer the heavy models until the
// browser is idle so we don't block the initial paint.
useGLTF.preload(MODEL_PATH_MAP["full"]);

if (typeof window !== "undefined") {
  const cb = window.requestIdleCallback ?? ((fn: () => void) => setTimeout(fn, 500));
  cb(() => {
    useGLTF.preload(MODEL_PATH_MAP["neurology"]);
    useGLTF.preload(MODEL_PATH_MAP["arthrology"]);
    // myology is ~153 MB — only preload after others are done
    cb(() => useGLTF.preload(MODEL_PATH_MAP["myology"]));
  });
}

// ── Per-model exposure ────────────────────────────────────────────────────────
const EXPOSURE_MAP: Record<ModelKey, number> = {
  full:       0.62,
  neurology:  0.42,
  arthrology: 0.38,
  myology:    0.50,
};

const BG_MAP: Record<ModelKey, string> = {
  full:       "#0d0d12",
  neurology:  "#38383a",
  arthrology: "#38383a",
  myology:    "#38383a",
};

// ── SceneAdaptor ──────────────────────────────────────────────────────────────
function SceneAdaptor({ model }: { model: ModelKey }) {
  const { gl } = useThree();
  useEffect(() => {
    gl.toneMappingExposure = EXPOSURE_MAP[model];
  }, [model, gl]);
  return null;
}

// ── Component ─────────────────────────────────────────────────────────────────
export function BodyScene() {
  const [selectedOrgan,   setSelectedOrgan]   = useState<string | null>(null);
  const [activeModel,     setActiveModel]     = useState<ModelKey>("full");
  const [activeSystem,    setActiveSystem]    = useState<SystemKey>("all");
  const [isTransitioning, setIsTransitioning] = useState(false);

  // ── AI analysis state ─────────────────────────────────────────────────────
  const [analysisResult, setAnalysisResult] = useState<StoredAnalysis | null>(null);
  const [scanLoading,    setScanLoading]    = useState(false);
  const [reportText,     setReportText]     = useState("");
  const [scanOpen,       setScanOpen]       = useState(false);
  const [scanError,      setScanError]      = useState<string | null>(null);

  // Organ world position captured synchronously on click — seeds ExtractedOrgan start pos
  const organStartPosRef = useRef<Vector3 | null>(null);

  // ── Derive per-organ highlight colours from analysis result ──────────────
  const highlightMeshes = useMemo<Array<{ organKey: string; color: string }>>(() => {
    if (!analysisResult || analysisResult.conditions.length === 0) return [];
    const map = new Map<string, string>();
    // Sort by severity so most severe wins if organs overlap
    const _order: Record<string, number> = { severe: 0, moderate: 1, mild: 2 };
    const sorted = [...analysisResult.conditions].sort(
      (a, b) => (_order[a.severity] ?? 3) - (_order[b.severity] ?? 3)
    );
    for (const cond of sorted) {
      for (const organ of cond.affected_organs) {
        const key = resolveOrganKey(organ);
        if (key && !map.has(key)) map.set(key, severityColor(cond.severity));
      }
    }
    return Array.from(map.entries()).map(([organKey, color]) => ({ organKey, color }));
  }, [analysisResult]);

  // ── Load from sessionStorage on mount (upload page → viewer bridge) ───────
  useEffect(() => {
    const stored = loadAnalysis();
    if (!stored) return;
    setAnalysisResult(stored);
    setScanOpen(true);
    if (stored.organ_keys.length > 0) setSelectedOrgan(stored.organ_keys[0]);
    clearAnalysis();     // consume once
  }, []);

  // ── Model switching ───────────────────────────────────────────────────────
  const switchModel = useCallback((model: ModelKey) => {
    if (model === activeModel) return;
    setIsTransitioning(true);
    setTimeout(() => {
      setActiveModel(model);
      setSelectedOrgan(null);
      setAnalysisResult(null);
      setReportText("");
      setScanError(null);
      setTimeout(() => setIsTransitioning(false), 200);
    }, 200);
  }, [activeModel]);

  // ── AI analysis handler ───────────────────────────────────────────────────
  async function handleAnalyseAI() {
    if (!reportText.trim()) return;
    setScanLoading(true);
    setScanError(null);

    try {
      const res = await fetch("/api/analyze-report", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ text: reportText }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail ?? `Server error ${res.status}`);
      }

      const data = await res.json() as StoredAnalysis & { organ_keys: string[] };

      if (!data.conditions || data.conditions.length === 0) {
        // Try keyword fallback before giving up
        const fbKey = extractDisease(reportText);
        if (fbKey) {
          const fb: StoredAnalysis = {
            conditions: [{
              name:            DISEASE_MAP[fbKey].label,
              confidence:      0.5,
              affected_organs: [DISEASE_MAP[fbKey].organ],
              severity:        "mild",
              description:     DISEASE_MAP[fbKey].description,
            }],
            summary:    DISEASE_MAP[fbKey].description,
            risk_level: "low",
            organ_keys: [DISEASE_MAP[fbKey].organ],
            source:     "fallback",
            timestamp:  Date.now(),
          };
          setAnalysisResult(fb);
          setSelectedOrgan(DISEASE_MAP[fbKey].organ);
        } else {
          setScanError("No significant conditions detected. Try pasting more of the report.");
        }
        return;
      }

      const stored: StoredAnalysis = { ...data, source: "ai", timestamp: Date.now() };
      setAnalysisResult(stored);
      if (data.organ_keys.length > 0) setSelectedOrgan(data.organ_keys[0]);

    } catch (err) {
      setScanError(
        "AI analysis failed: " + (err instanceof Error ? err.message : "unknown error")
      );
    } finally {
      setScanLoading(false);
    }
  }

  function handleClearAnalysis() {
    setAnalysisResult(null);
    setSelectedOrgan(null);
    setReportText("");
    setScanError(null);
  }

  const btnBase   = "w-full text-left px-2.5 py-1.5 rounded-lg border text-xs font-medium transition-all duration-150";
  const btnActive = "border-cyan/60 text-cyan bg-cyan/10";
  const btnIdle   = "border-white/5 text-slate-400 hover:text-slate-200 hover:border-white/15 bg-transparent";

  return (
    <div className="w-full h-full relative">
      <Canvas
        shadows
        // "demand" only re-renders when state changes — ~60 % GPU savings
        // on static scenes.  Interactions (orbit, click) still trigger redraws.
        frameloop="demand"
        // Cap DPR at 2 — retina looks great; going higher wastes GPU on 3× screens
        dpr={[1, 2]}
        camera={{ position: [0, 2, 4], fov: 60, near: 0.001, far: 1000 }}
        gl={{
          antialias: true,
          toneMapping: 4,
          toneMappingExposure: EXPOSURE_MAP["full"],
          // Power preference hint — favours discrete GPU on multi-GPU devices
          powerPreference: "high-performance",
        }}
        style={{ background: BG_MAP[activeModel] }}
      >
        <SceneAdaptor model={activeModel} />

        <ambientLight intensity={0.15} color="#e8d8c0" />
        <directionalLight
          position={[2, 6, 4]}
          intensity={0.80}
          color="#ffd090"
          castShadow
          // 1024 shadow map is visually indistinguishable for this model scale
          // but uses 4× less GPU memory than 2048.
          shadow-mapSize-width={1024}
          shadow-mapSize-height={1024}
          shadow-camera-near={0.1}
          shadow-camera-far={80}
          shadow-bias={-0.001}
        />
        <directionalLight position={[-3, 3, 1]} intensity={0.08} color="#b0c8e8" />
        <directionalLight position={[0, 4, -6]} intensity={0.12} color="#ffc870" />

        <Environment preset="apartment" />
        <ContactShadows position={[0, 0, 0]} opacity={0.55} scale={6} blur={2} far={5} color="#0a0a0a" />

        <Suspense fallback={null}>
          <SkeletonModel
            key={activeModel}
            modelPath={MODEL_PATH_MAP[activeModel]}
            modelKey={activeModel}
            activeSystem={activeSystem}
            selectedOrgan={selectedOrgan}
            onOrganClick={(key) => {
              setSelectedOrgan(key);
              setAnalysisResult(null);   // manual click replaces AI result
            }}
            onOrganReady={(_key, pos) => { organStartPosRef.current = pos; }}
            highlightMeshes={highlightMeshes}
          />
        </Suspense>

        {/* Cinematic organ extraction — only when a standalone GLB exists for this organ */}
        {selectedOrgan && ORGAN_MODEL_MAP[selectedOrgan] && (
          <Suspense fallback={null}>
            <ExtractedOrgan
              key={selectedOrgan}
              organKey={selectedOrgan}
              startPos={organStartPosRef.current ?? undefined}
            />
          </Suspense>
        )}

        <CameraController />

        {/* Bloom is very subtle — skip on low-end devices by checking devicePixelRatio */}
        {typeof window !== "undefined" && window.devicePixelRatio <= 2 && (
          <EffectComposer multisampling={0}>
            <Bloom intensity={0.05} luminanceThreshold={0.95} luminanceSmoothing={0.9} mipmapBlur />
          </EffectComposer>
        )}
      </Canvas>

      {/* Fade overlay */}
      <div
        className="absolute inset-0 z-20 pointer-events-none transition-opacity duration-200"
        style={{ background: BG_MAP[activeModel], opacity: isTransitioning ? 1 : 0 }}
      />

      {/* ── Left control panel ────────────────────────────────────────────── */}
      <div className="absolute left-4 top-4 z-10 w-48 rounded-xl border border-white/10 bg-navy-800/90 backdrop-blur-md p-3 shadow-xl flex flex-col gap-3 overflow-y-auto max-h-[calc(100vh-6rem)]">

        {/* Anatomical Mode */}
        <div>
          <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-2">
            Anatomical Mode
          </p>
          <div className="flex flex-col gap-1">
            {MODEL_KEYS.map((key) => (
              <button
                key={key}
                onClick={() => switchModel(key)}
                className={`${btnBase} ${activeModel === key ? btnActive : btnIdle}`}
              >
                {MODEL_LABELS[key]}
              </button>
            ))}
          </div>
        </div>

        <div className="h-px bg-white/5" />

        {/* Organ System */}
        <div>
          <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-2">
            Organ System
          </p>
          <div className="flex flex-col gap-1">
            {SYSTEM_KEYS.map((key) => (
              <button
                key={key}
                onClick={() => setActiveSystem(key)}
                className={`${btnBase} ${activeSystem === key ? btnActive : btnIdle}`}
              >
                {SYSTEM_LABELS[key]}
              </button>
            ))}
          </div>
        </div>

        <div className="h-px bg-white/5" />

        {/* ── AI Analysis ──────────────────────────────────────────────────── */}
        <div>
          <button
            onClick={() => setScanOpen((v) => !v)}
            className="flex items-center justify-between w-full text-[10px] font-semibold text-slate-500 uppercase tracking-widest hover:text-slate-400 transition-colors"
          >
            <span>AI Analysis</span>
            <ChevronDown
              className="w-3 h-3 transition-transform duration-150"
              style={{ transform: scanOpen ? "rotate(180deg)" : "rotate(0deg)" }}
            />
          </button>

          {scanOpen && (
            <div className="mt-2 flex flex-col gap-2">
              {analysisResult ? (

                /* ── Results view ──────────────────────────────────────── */
                <div className="flex flex-col gap-2">
                  {/* Risk + source badges */}
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span
                      className="px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wider"
                      style={{
                        background: riskColor(analysisResult.risk_level) + "22",
                        color:      riskColor(analysisResult.risk_level),
                        border:    `1px solid ${riskColor(analysisResult.risk_level)}44`,
                      }}
                    >
                      {analysisResult.risk_level} risk
                    </span>
                    {analysisResult.source === "fallback" && (
                      <span className="text-[9px] text-slate-500 italic">keyword match</span>
                    )}
                  </div>

                  {/* Condition cards */}
                  {analysisResult.conditions.map((cond, i) => {
                    const col = severityColor(cond.severity);
                    return (
                      <button
                        key={i}
                        className="rounded-lg border p-2 flex flex-col gap-0.5 text-left w-full cursor-pointer transition-opacity hover:opacity-90"
                        style={{ borderColor: col + "44", background: col + "0e" }}
                        onClick={() => {
                          const key = resolveOrganKey(cond.affected_organs[0] ?? "");
                          if (key) setSelectedOrgan(key);
                        }}
                      >
                        <div className="flex items-center justify-between gap-1">
                          <span className="text-[11px] font-semibold text-white leading-tight">
                            {cond.name}
                          </span>
                          <span className="text-[9px] font-bold shrink-0" style={{ color: col }}>
                            {Math.round(cond.confidence * 100)}%
                          </span>
                        </div>
                        <span className="text-[9px] uppercase tracking-wider font-medium" style={{ color: col }}>
                          {cond.severity}
                        </span>
                        <p className="text-[10px] text-slate-500 leading-snug mt-0.5">{cond.description}</p>
                        <p className="text-[9px] text-slate-600 italic">{cond.affected_organs.join(", ")}</p>
                      </button>
                    );
                  })}

                  <button
                    onClick={handleClearAnalysis}
                    className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors text-left mt-0.5"
                  >
                    ✕ Clear
                  </button>
                </div>

              ) : (

                /* ── Input view ────────────────────────────────────────── */
                <>
                  <textarea
                    value={reportText}
                    onChange={(e) => { setReportText(e.target.value); setScanError(null); }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleAnalyseAI();
                    }}
                    placeholder="Paste report text…"
                    rows={3}
                    className="w-full resize-none rounded-lg border border-white/10 bg-white/5 px-2 py-1.5 text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-cyan/40 transition-colors"
                  />
                  {scanError && (
                    <p className="text-[10px] text-amber-400 leading-snug">{scanError}</p>
                  )}
                  <button
                    onClick={handleAnalyseAI}
                    disabled={!reportText.trim() || scanLoading}
                    className="w-full rounded-lg border border-cyan/30 bg-cyan/10 py-1.5 text-xs font-medium text-cyan transition-all hover:bg-cyan/20 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-1.5"
                  >
                    {scanLoading ? (
                      <>
                        <span className="w-3 h-3 border border-cyan/40 border-t-cyan rounded-full animate-spin" />
                        Analysing…
                      </>
                    ) : "Analyse with AI"}
                  </button>
                </>

              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Right side: organ info panel ─────────────────────────────────── */}
      <div className="absolute right-4 top-4 z-10">
        <OrganInfoPanel
          organ={selectedOrgan}
          detectedDisease={
            analysisResult?.conditions[0]
              ? analysisResult.conditions[0].name
              : null
          }
          onClose={() => { setSelectedOrgan(null); setAnalysisResult(null); }}
        />
      </div>
    </div>
  );
}
