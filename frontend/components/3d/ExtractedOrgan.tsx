"use client";

import { useRef, useEffect, useMemo } from "react";
import { useGLTF } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

// ── Organ → standalone GLB map ────────────────────────────────────────────────
// Bladder shares stomach.glb — closest available sac-shaped model.
// Kidney, intestine, pancreas, spleen have no standalone file — graceful skip.
// v=2 query params bust the browser cache from prior deployments that served LFS pointer text
export const ORGAN_MODEL_MAP: Record<string, string> = {
  heart:            "/assets/anatomy/realistic_human_heart.glb?v=2",
  lung:             "/assets/anatomy/realistic_human_lungs.glb?v=2",
  brain:            "/assets/anatomy/Brain.glb?v=2",
  stomach:          "/assets/anatomy/stomach.glb?v=2",
  liver:            "/assets/anatomy/human_liver_and_gallbladder.glb?v=2",
  bladder:          "/assets/anatomy/stomach.glb?v=2",     // closest sac-shaped model available
  kidney:           "/assets/anatomy/Kidney.glb?v=2",
  eye:              "/assets/anatomy/eye.glb?v=2",
  vertebral_column: "/assets/anatomy/vertebral_column.glb?v=2",
  mouth:            "/assets/anatomy/mouth.glb?v=2",
};

// ── Preload all unique paths once at module load — zero cost on repeated clicks ─
const _uniquePaths = Array.from(new Set(Object.values(ORGAN_MODEL_MAP)));
_uniquePaths.forEach((p) => useGLTF.preload(p));

// ── Target world size — all organs auto-scale to this value ──────────────────
// Calibrated so the heart (confirmed correct by user) fills the inspection area.
// Every GLB is measured via bounding box on load and scaled to this world-unit
// size, so all organs appear visually identical in footprint regardless of their
// internal GLB unit scale.
const TARGET_WORLD_SIZE = 1.8; // world units — ~70% of full body height

// ── Animation constants ────────────────────────────────────────────────────────
const TARGET_X   = 0.8;  // just to the right of the body
const TARGET_Y   = 0.2;  // slight upward lift
const TARGET_Z   = 0.4;  // slight forward push toward viewer
const LERP_SPEED = 0.08;

// ── Component ─────────────────────────────────────────────────────────────────
interface ExtractedOrganProps {
  organKey: string;
  /** Organ's world position at moment of click — seeds the extraction start point. */
  startPos?: THREE.Vector3;
}

export function ExtractedOrgan({ organKey, startPos }: ExtractedOrganProps) {
  const path = ORGAN_MODEL_MAP[organKey]; // always defined — guarded in BodyScene

  const { scene }   = useGLTF(path);
  const clonedScene = useMemo(() => scene.clone(true), [scene]); // independent copy
  const groupRef    = useRef<THREE.Group>(null);

  // Computed from bounding box on load — replaces static per-organ magic numbers
  const targetScaleRef = useRef(1.0);

  // ── Measure bounding box → derive uniform scale that fills TARGET_WORLD_SIZE ──
  // Runs once per clonedScene (i.e. once per mount). Zero state updates.
  useEffect(() => {
    const box    = new THREE.Box3().setFromObject(clonedScene);
    const size   = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    if (maxDim > 0) {
      targetScaleRef.current = TARGET_WORLD_SIZE / maxDim;
    }
  }, [clonedScene]);

  // ── Initialise group at organ's world position, invisible ─────────────────────
  // startPos is captured synchronously on click before the body shifts — correct origin.
  useEffect(() => {
    const g = groupRef.current;
    if (!g) return;
    if (startPos) {
      g.position.copy(startPos);
    } else {
      g.position.set(0, 0, 0);
    }
    g.scale.setScalar(0.001);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // intentionally once — startPos is the mount-time snapshot

  // ── Per-frame cinematic animation (all lerp — zero state updates) ─────────────
  useFrame(() => {
    const g = groupRef.current;
    if (!g) return;

    // Position: smooth lerp toward target — "pulled out for close inspection"
    g.position.x += (TARGET_X - g.position.x) * LERP_SPEED;
    g.position.y += (TARGET_Y - g.position.y) * LERP_SPEED;
    g.position.z += (TARGET_Z - g.position.z) * LERP_SPEED;

    // Scale: lerp from near-zero to bounding-box-derived target
    const curScale = g.scale.x;
    g.scale.setScalar(curScale + (targetScaleRef.current - curScale) * LERP_SPEED);

    // Slow premium rotation
    g.rotation.y += 0.003;
  });

  return (
    <group ref={groupRef}>
      <primitive object={clonedScene} />
    </group>
  );
}
