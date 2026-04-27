"use client";

import { useRef, useState, useEffect, useMemo, useCallback } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { Html, Line } from "@react-three/drei";
import * as THREE from "three";
import { ANNOTATIONS } from "@/lib/annotationConfig";
import type { AnnotationDef } from "@/lib/annotationConfig";

// ─── Module-level scratch vectors — zero per-frame allocations ───────────────
const _camDir   = new THREE.Vector3();
const _annotDir = new THREE.Vector3();

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

/** dots = far view (sphere only) | label = name card | full = name + description */
type LabelMode = "dots" | "label" | "full";

interface ResolvedAnnotation {
  markerPos: THREE.Vector3; // sphere anchor (organ bounding-box centre + offset)
  labelPos:  THREE.Vector3; // label card (outward from body centre + collision-resolved)
}

interface MarkerProps {
  annotation: AnnotationDef;
  resolved:   ResolvedAnnotation;
  labelMode:  LabelMode;
  isHovered:  boolean;
  onHover:    (id: string) => void;
  onLeave:    () => void;
  onClick:    (organ: string) => void;
}

interface AnnotationEngineProps {
  organMeshMapRef:   React.MutableRefObject<Map<string, THREE.Mesh>>;
  activeSystem:      string;
  selectedOrgan:     string | null; // reserved — markers always visible
  onAnnotationClick: (key: string) => void;
  defaultCamDistRef: React.MutableRefObject<number>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function getMarkerColor(ann: AnnotationDef): string {
  if (ann.type !== "disease") return "#7ec8f5";
  return ann.severity === "high" ? "#ff3333"
       : ann.severity === "medium" ? "#ff8822"
       : "#ffcc00";
}

/**
 * Push the label outward from the body centre (world origin) and slightly up.
 * This keeps labels from overlapping the model surface and gives natural spread.
 */
function makeLabelPos(markerPos: THREE.Vector3): THREE.Vector3 {
  const OUTWARD = 0.28;
  const outward = markerPos.clone().normalize().multiplyScalar(OUTWARD);
  return markerPos.clone().add(outward).add(new THREE.Vector3(0, 0.04, 0));
}

/**
 * Lightweight Y-axis collision avoidance.
 * Sorts by Y descending, then pushes vertically-close labels apart.
 * Only runs on laterally near labels (< 0.26 XZ distance).
 */
function avoidCollisions(
  entries: Array<{ id: string; pos: THREE.Vector3 }>,
): void {
  const MIN_Y_GAP   = 0.09;
  const LAT_THRESH  = 0.26;
  entries.sort((a, b) => b.pos.y - a.pos.y);
  for (let i = 0; i < entries.length - 1; i++) {
    const a = entries[i];
    const b = entries[i + 1];
    if (Math.hypot(a.pos.x - b.pos.x, a.pos.z - b.pos.z) > LAT_THRESH) continue;
    const gap = a.pos.y - b.pos.y;
    if (gap < MIN_Y_GAP) {
      const push = (MIN_Y_GAP - gap) * 0.5;
      a.pos.y += push;
      b.pos.y -= push;
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// AnnotationMarker
//
// One sphere + connector line + 3D-anchored Html label per annotation.
// All per-frame work is in useFrame with refs — zero state updates per frame.
// ─────────────────────────────────────────────────────────────────────────────

function AnnotationMarker({
  annotation,
  resolved,
  labelMode,
  isHovered,
  onHover,
  onLeave,
  onClick,
}: MarkerProps) {
  const { camera }     = useThree();
  const sphereRef      = useRef<THREE.Mesh>(null);
  const labelGroupRef  = useRef<THREE.Group>(null);
  const htmlDivRef     = useRef<HTMLDivElement>(null);
  const frameCount     = useRef(0);

  const { markerPos, labelPos } = resolved;
  const isDisease  = annotation.type === "disease";
  const isHighSev  = isDisease && annotation.severity === "high";
  const pulseSpeed = isDisease ? 4.0 : 1.8;
  const color      = getMarkerColor(annotation);
  const showLabel  = labelMode !== "dots";

  // Unique per-marker phase — stable across re-renders, zero allocation
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const phase = useMemo(() => Math.random() * Math.PI * 2, []);

  // Connector line endpoints — stable after first mount (positions never change)
  const linePoints = useMemo<[number, number, number][]>(
    () => [
      [markerPos.x, markerPos.y, markerPos.z],
      [labelPos.x,  labelPos.y,  labelPos.z ],
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  // ── Per-frame: pulse + float + depth opacity ──────────────────────────────
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    frameCount.current++;

    // ── Sphere pulse ──────────────────────────────────────────────────────
    if (sphereRef.current) {
      const pulse = 1 + Math.sin(t * pulseSpeed + phase) * 0.15;
      sphereRef.current.scale.setScalar(isHovered ? pulse * 1.35 : pulse);

      // High-severity disease: subtle random jitter
      if (isHighSev) {
        sphereRef.current.position.set(
          markerPos.x + (Math.random() - 0.5) * 0.0022,
          markerPos.y + (Math.random() - 0.5) * 0.0022,
          markerPos.z + (Math.random() - 0.5) * 0.0022,
        );
      }
    }

    // ── Label float (sinusoidal Y drift on the label group) ───────────────
    if (labelGroupRef.current) {
      labelGroupRef.current.position.y =
        labelPos.y + Math.sin(t * 0.75 + phase) * 0.0028;
    }

    // ── Depth-based opacity (every 8 frames — cheap) ──────────────────────
    // Dot product of (body-centre → annotation) with camera forward direction.
    // When annotation is on the far side of the body (behind from camera POV),
    // the dot is positive and we reduce opacity smoothly.
    if (frameCount.current % 8 === 0) {
      camera.getWorldDirection(_camDir);
      _annotDir.copy(markerPos).normalize(); // body centre is world origin
      const dot     = _annotDir.dot(_camDir);
      const opacity = Math.max(0.12, 1 - Math.max(0, dot) * 0.82);

      // Mutate Three.js material directly — no React state
      if (sphereRef.current) {
        (sphereRef.current.material as THREE.MeshBasicMaterial).opacity =
          0.88 * opacity;
      }
      // Mutate DOM element directly — no React state
      if (htmlDivRef.current) {
        htmlDivRef.current.style.opacity = opacity.toFixed(3);
      }
    }
  });

  // ── Inline styles (no Tailwind — Html portals to outside Tailwind scope) ──
  // backdrop-filter is intentionally omitted: <Html transform> applies a CSS3D
  // matrix on its wrapper that breaks backdrop-filter in Chromium. Instead we
  // use a near-opaque dark background that achieves the same premium feel.
  const cardStyle: React.CSSProperties = {
    background:    isHovered ? "rgba(28,46,72,0.95)" : "rgba(8,15,28,0.88)",
    border:        `1px solid ${isDisease ? color + "55" : "rgba(100,165,240,0.22)"}`,
    borderRadius:  isDisease ? "8px" : "6px",
    padding:       labelMode === "full" ? "5px 10px" : "3px 9px",
    color:         "#dceeff",
    fontSize:      "12px",
    fontFamily:    "system-ui, -apple-system, sans-serif",
    lineHeight:    "1.4",
    display:       "flex",
    flexDirection: "column" as const,
    gap:           "2px",
    boxShadow:     isDisease
                     ? `0 0 10px ${color}44, 0 2px 10px rgba(0,0,0,0.65)`
                     : "0 2px 8px rgba(0,0,0,0.55)",
    whiteSpace:    "nowrap" as const,
    transition:    "background 0.2s ease",
    pointerEvents: "none",
    userSelect:    "none",
  };

  const dotStyle: React.CSSProperties = {
    width:           "5px",
    height:          "5px",
    borderRadius:    "50%",
    backgroundColor: color,
    flexShrink:      0,
    boxShadow:       isDisease ? `0 0 4px 1px ${color}99` : "none",
  };

  return (
    <group>

      {/* ── Feature 2: Connector line — organ sphere → label card ─────────── */}
      {showLabel && (
        <Line
          points={linePoints}
          color={color}
          lineWidth={0.8}
          transparent
          opacity={0.28}
          depthWrite={false}
        />
      )}

      {/* ── Feature 1: Sphere marker at organ ────────────────────────────── */}
      <mesh
        ref={sphereRef}
        position={markerPos.toArray()}
        renderOrder={isDisease ? 3 : 2}   // Feature 7: disease always on top
        onPointerOver={(e) => { e.stopPropagation(); onHover(annotation.id); }}
        onPointerOut={(e)  => { e.stopPropagation(); onLeave(); }}
        onClick={(e)       => { e.stopPropagation(); onClick(annotation.organ); }}
      >
        <sphereGeometry args={[0.018, 14, 14]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.88}
          depthWrite={false}
        />

        {/* Feature 7: Additive glow halo for disease annotations */}
        {isDisease && (
          <mesh scale={1.65} raycast={() => null}>
            <sphereGeometry args={[0.018, 10, 10]} />
            <meshBasicMaterial
              color={color}
              transparent
              opacity={0.17}
              blending={THREE.AdditiveBlending}
              depthWrite={false}
            />
          </mesh>
        )}
      </mesh>

      {/* ── Feature 1: 3D-anchored label via Html transform ──────────────── */}
      {showLabel && (
        <group
          ref={labelGroupRef}
          position={labelPos.toArray()}  // Feature 8: float animation via useFrame
        >
          <Html
            transform                    // true 3D anchoring — moves with camera
            distanceFactor={10}          // scales naturally with perspective
            zIndexRange={isDisease ? [200, 100] : [100, 0]}  // Feature 7: disease on top
            style={{ pointerEvents: "none", userSelect: "none" }}
          >
            {/* htmlDivRef used for direct DOM opacity updates (no state) */}
            <div
              ref={htmlDivRef}
              style={{ transition: "opacity 0.4s ease" }}  // Feature 8: smooth fade
            >
              {/* Feature 6: Clean minimal glassmorphism label */}
              <div style={cardStyle}>
                <span style={{
                  display:       "flex",
                  alignItems:    "center",
                  gap:           "5px",
                  fontWeight:    600,
                  letterSpacing: "0.04em",
                }}>
                  <span style={dotStyle} />  {/* Feature 6: system-colour dot */}
                  {annotation.label}
                </span>

                {/* Feature 5: full mode shows description */}
                {labelMode === "full" && (
                  <span style={{
                    fontSize:   "10px",
                    color:      "rgba(155,195,230,0.82)",
                    lineHeight: "1.35",
                    marginTop:  "1px",
                    maxWidth:   "155px",
                    whiteSpace: "normal" as const,
                  }}>
                    {annotation.shortDesc}
                  </span>
                )}
              </div>
            </div>
          </Html>
        </group>
      )}
    </group>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// AnnotationEngine
//
// Resolves organ positions once, computes outward label positions,
// applies collision avoidance, then renders AnnotationMarkers.
// ─────────────────────────────────────────────────────────────────────────────

export function AnnotationEngine({
  organMeshMapRef,
  activeSystem,
  onAnnotationClick,
  defaultCamDistRef,
}: AnnotationEngineProps) {
  const { camera } = useThree();

  // Single resolved map: annotation id → { markerPos, labelPos }
  const [resolvedData, setResolvedData] = useState<Map<string, ResolvedAnnotation>>(
    () => new Map(),
  );

  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [labelMode, setLabelMode] = useState<LabelMode>("label");

  const lastModeRef  = useRef<LabelMode>("label");
  const frameSkipRef = useRef(0);

  // ── Feature 1-3, 9: Resolve positions + outward offset + collision avoidance
  // Runs once, 150ms after mount, after SkeletonModel Effect 1 has populated
  // organMeshMapRef.
  useEffect(() => {
    const timer = setTimeout(() => {
      // Step 1: mesh bounding-box centres per organ key
      const meshCenters = new Map<string, THREE.Vector3>();
      organMeshMapRef.current.forEach((mesh, key) => {
        const box = new THREE.Box3().setFromObject(mesh);
        const c   = new THREE.Vector3();
        box.getCenter(c);
        meshCenters.set(key, c);
      });

      // Step 2: compute marker + label positions per annotation
      const tempData = new Map<string, ResolvedAnnotation>();
      const labelEntries: Array<{ id: string; pos: THREE.Vector3 }> = [];

      for (const ann of ANNOTATIONS) {
        const centre = meshCenters.get(ann.organ);
        if (!centre) continue;

        const [ox, oy, oz] = ann.positionOffset;
        const markerPos    = centre.clone().add(new THREE.Vector3(ox, oy, oz));
        const labelPos     = makeLabelPos(markerPos); // Feature 3: outward offset

        labelEntries.push({ id: ann.id, pos: labelPos });
        tempData.set(ann.id, { markerPos, labelPos });
      }

      // Step 3: Feature 9 — lightweight collision avoidance
      avoidCollisions(labelEntries);
      // Write collision-resolved label positions back
      for (const { id, pos } of labelEntries) {
        const d = tempData.get(id);
        if (d) d.labelPos = pos;
      }

      setResolvedData(tempData);
    }, 150);

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // stable ref — intentionally empty deps

  // ── Feature 5: Zoom-based label mode (throttled every 15 frames) ─────────
  useFrame(() => {
    if (++frameSkipRef.current < 15) return;
    frameSkipRef.current = 0;

    const dist = camera.position.length(); // model at world origin
    const base = defaultCamDistRef.current;

    const newMode: LabelMode =
      dist > base * 1.5 ? "dots"  :   // far  → spheres only
      dist < base * 0.6 ? "full"  :   // close → full info card
      "label";                         // mid   → name only

    if (newMode !== lastModeRef.current) {
      lastModeRef.current = newMode;
      setLabelMode(newMode);
    }
  });

  // ── Feature 4, 7: Filter by system + prioritise disease annotations ────────
  const visible = useMemo(() => {
    const filtered = ANNOTATIONS.filter((ann) =>
      (activeSystem === "all" || ann.system === activeSystem) &&
      resolvedData.has(ann.id),
    );
    // Sort: normal first, disease last → disease renders on top in WebGL
    return filtered.sort((a, b) =>
      a.type === "disease" && b.type !== "disease" ?  1 :
      b.type === "disease" && a.type !== "disease" ? -1 : 0,
    );
  }, [activeSystem, resolvedData]);

  const handleHover = useCallback((id: string) => setHoveredId(id), []);
  const handleLeave = useCallback(() => setHoveredId(null), []);

  return (
    <>
      {visible.map((ann) => (
        <AnnotationMarker
          key={ann.id}
          annotation={ann}
          resolved={resolvedData.get(ann.id)!}
          labelMode={labelMode}
          isHovered={hoveredId === ann.id}
          onHover={handleHover}
          onLeave={handleLeave}
          onClick={onAnnotationClick}
        />
      ))}
    </>
  );
}
