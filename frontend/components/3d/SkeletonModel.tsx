"use client";

import { useRef, useEffect, useMemo } from "react";
import { useGLTF } from "@react-three/drei";
import { useThree, useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { ThreeEvent } from "@react-three/fiber";
import { ORGAN_MODEL_MAP } from "./ExtractedOrgan";

// ─────────────────────────────────────────────────────────────────────────────
// ORGAN REGISTRY
// base = 0 → GLB texture fully unobscured at rest
// hover = moderate → clear interaction feedback
// ─────────────────────────────────────────────────────────────────────────────
interface OrganConfig {
  key: string;
  keywords: string[];
  emissive: string;
  base: number;
  hover: number;
}

const ORGAN_REGISTRY: OrganConfig[] = [
  { key: "heart",      keywords: ["heart"],                               emissive: "#ff2200", base: 0.00, hover: 0.55 },
  { key: "lung",       keywords: ["lung", "lunge"],                       emissive: "#cc3300", base: 0.00, hover: 0.45 },
  { key: "stomach",    keywords: ["stomach", "magen"],                    emissive: "#446600", base: 0.00, hover: 0.40 },
  { key: "liver",      keywords: ["liver", "leber"],                      emissive: "#882200", base: 0.00, hover: 0.45 },
  { key: "kidney",     keywords: ["kidney", "niere"],                     emissive: "#663300", base: 0.00, hover: 0.45 },
  { key: "intestine",  keywords: ["intestine", "colon", "bowel", "darm"], emissive: "#774400", base: 0.00, hover: 0.40 },
  { key: "brain",      keywords: ["brain", "gehirn", "cerebr", "encephal", "cortex", "neural_tissue", "cranial_organ"], emissive: "#884488", base: 0.00, hover: 0.40 },
  { key: "bladder",    keywords: ["bladder", "blase"],                    emissive: "#336644", base: 0.00, hover: 0.35 },
  { key: "pancreas",   keywords: ["pancreas", "pankreas"],                emissive: "#554400", base: 0.00, hover: 0.35 },
  { key: "spleen",     keywords: ["spleen", "milz"],                      emissive: "#771144", base: 0.00, hover: 0.35 },
  { key: "gallbladder",     keywords: ["gallbladder", "gall", "gallenblase"],                                                         emissive: "#448800", base: 0.00, hover: 0.40 },
  { key: "eye",             keywords: ["eye", "eyeball", "orbit", "ocular", "sclera", "retina", "cornea"],                                emissive: "#2255ff", base: 0.00, hover: 0.50 },
  { key: "vertebral_column",keywords: ["vertebr", "spine", "spinal", "column", "cord", "lumbar", "thoracic", "cervical", "sacr", "disc"], emissive: "#aa9977", base: 0.00, hover: 0.40 },
  { key: "mouth",           keywords: ["mouth", "jaw", "mandible", "oral", "teeth", "tooth", "dental", "maxilla", "gum", "tongue"],       emissive: "#dd5533", base: 0.00, hover: 0.45 },
];

// ─────────────────────────────────────────────────────────────────────────────
// SYSTEM REGISTRY
// ─────────────────────────────────────────────────────────────────────────────
const SYSTEMS: Record<string, string[]> = {
  cardiovascular: ["heart", "artery", "vein", "aorta", "cardiac"],
  respiratory:    ["lung", "lunge", "trachea", "bronch", "airway"],
  digestive:      ["stomach", "liver", "intestine", "colon", "bowel", "gallbladder", "gall", "magen", "leber", "darm", "pancreas", "pankreas"],
  reproductive:   ["uterus", "ovary", "testis", "uteri", "ovar", "testi", "prostate", "vagina"],
  excretory:      ["kidney", "bladder", "niere", "blase", "ureter", "urethra"],
};

// ─────────────────────────────────────────────────────────────────────────────
// DISEASE HIGHLIGHT — pulsing additive glow sphere around a selected organ
// ─────────────────────────────────────────────────────────────────────────────
function OrganHighlight({ mesh, color }: { mesh: THREE.Mesh; color: string }) {
  const ref = useRef<THREE.Mesh>(null);

  const { position, radius } = useMemo(() => {
    const pos = new THREE.Vector3();
    mesh.getWorldPosition(pos);
    const box = new THREE.Box3().setFromObject(mesh);
    const r = Math.max(box.getSize(new THREE.Vector3()).length() * 0.6, 0.04);
    return { position: pos, radius: r };
  }, [mesh]);

  useFrame(({ clock }) => {
    if (!ref.current) return;
    ref.current.scale.setScalar(1 + Math.sin(clock.elapsedTime * 2) * 0.05);
  });

  return (
    <mesh ref={ref} position={position} raycast={() => null}>
      <sphereGeometry args={[radius, 32, 32]} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={0.12}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
        side={THREE.FrontSide}
      />
    </mesh>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Material fix for models with pure-white GLB exports
// ─────────────────────────────────────────────────────────────────────────────
const BRIGHT_MODELS = new Set(["neurology", "arthrology", "myology"]);
const BONE_CREAM    = new THREE.Color("#c4b98c");

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function getOrganConfig(meshName: string): OrganConfig | null {
  const lower = meshName.toLowerCase();
  return ORGAN_REGISTRY.find((o) => o.keywords.some((kw) => lower.includes(kw))) ?? null;
}

/**
 * Three-pass organ identification for a mesh node:
 *
 * Pass 1 — node name + full parent chain:
 *   Handles generic mesh names (e.g. "Object_034") inside named groups ("Brain").
 *
 * Pass 2 — material names on the mesh itself:
 *   GLTF exporters often store meaningful names in materials even when node
 *   names are auto-generated.  Catches "Brain_Material", "cerebral_mat", etc.
 *
 * Pass 3 — geometry name:
 *   Some exporters embed the organ name only in BufferGeometry.name.
 */
function getOrganConfigFromHierarchy(node: THREE.Object3D): OrganConfig | null {
  // Pass 1 — node + ancestors
  let current: THREE.Object3D | null = node;
  while (current) {
    const config = getOrganConfig(current.name);
    if (config) return config;
    current = current.parent;
  }

  // Pass 2 — material names (mesh only)
  if (node instanceof THREE.Mesh) {
    const mats = Array.isArray(node.material) ? node.material : [node.material];
    for (const mat of mats) {
      if (mat && mat.name) {
        const config = getOrganConfig(mat.name);
        if (config) return config;
      }
    }
    // Pass 3 — geometry name
    const geo = (node as THREE.Mesh).geometry;
    if (geo && geo.name) {
      const config = getOrganConfig(geo.name);
      if (config) return config;
    }
  }

  return null;
}

/**
 * Lookup by the key stored in mesh.userData.organKey during Effect 1.
 * Used in pointer handlers so they don't re-run keyword matching every event.
 */
function getOrganConfigByKey(key: string | undefined): OrganConfig | null {
  if (!key) return null;
  return ORGAN_REGISTRY.find((o) => o.key === key) ?? null;
}

function getMaterials(mesh: THREE.Mesh): THREE.MeshStandardMaterial[] {
  const raw = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  return raw.filter((m): m is THREE.MeshStandardMaterial => m instanceof THREE.MeshStandardMaterial);
}

function meshBelongsToSystem(meshName: string, system: string): boolean {
  const lower = meshName.toLowerCase();
  return (SYSTEMS[system] ?? []).some((kw) => lower.includes(kw));
}

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

interface SkeletonModelProps {
  modelPath:       string;
  modelKey:        string;
  activeSystem:    string;
  selectedOrgan:   string | null;   // drives transparency engine + cinematic focus
  onOrganClick:    (organKey: string) => void;
  /** AI-driven multi-organ highlights. Each entry gets its own glow sphere. */
  highlightMeshes?: Array<{ organKey: string; color: string }>;
  /** Fires on click with the organ's world position — used to seed ExtractedOrgan start pos. */
  onOrganReady?:    (organKey: string, worldPos: THREE.Vector3) => void;
}

type OrbCtrl = { target: THREE.Vector3; update: () => void };

export function SkeletonModel({
  modelPath,
  modelKey,
  activeSystem,
  selectedOrgan,
  onOrganClick,
  highlightMeshes = [],
  onOrganReady,
}: SkeletonModelProps) {
  const { scene }              = useGLTF(modelPath);
  const groupRef               = useRef<THREE.Group>(null);
  const { camera, controls }   = useThree();
  const needsRecolour          = BRIGHT_MODELS.has(modelKey);

  // ── Focus / transparency refs (all mutable — never trigger re-renders) ────
  const organMeshMapRef  = useRef<Map<string, THREE.Mesh>>(new Map());  // key → first mesh
  const focusedMeshRef   = useRef<THREE.Mesh | null>(null);

  // ── Derive highlight entries ──────────────────────────────────────────────────
  // Glow spheres are shown ONLY for AI multi-organ analysis results.
  // Manual single-organ clicks rely solely on the emissive highlight — no sphere.
  // This keeps the scene clean and avoids the old background-glow effect returning.
  const highlightEntries = useMemo<Array<{ mesh: THREE.Mesh; color: string }>>(() => {
    return highlightMeshes
      .map(({ organKey, color }) => {
        const mesh = organMeshMapRef.current.get(organKey);
        return mesh ? { mesh, color } : null;
      })
      .filter((x): x is { mesh: THREE.Mesh; color: string } => x !== null);
  }, [highlightMeshes]);

  const defaultCamPos    = useRef<THREE.Vector3 | null>(null);
  const defaultLookAt    = useRef<THREE.Vector3 | null>(null);
  const camTargetPos     = useRef(new THREE.Vector3());
  const camLookTarget    = useRef(new THREE.Vector3());
  const isAnimating      = useRef(false);
  const animFrames       = useRef(0);         // hard-stop fallback counter
  const defaultCamDistRef  = useRef<number>(5); // populated in Effect 2, read by AnnotationEngine
  const bodyShiftActiveRef = useRef(false);     // true when organ selected → shift body left

  // ── 1. Material setup — once per scene load ───────────────────────────────
  useEffect(() => {
    organMeshMapRef.current.clear();

    scene.traverse((node) => {
      if (!(node instanceof THREE.Mesh)) return;

      node.castShadow    = true;
      node.receiveShadow = true;

      const organ = getOrganConfigFromHierarchy(node); // walks parent chain for nested meshes
      const mats  = getMaterials(node);

      if (organ) {
        mats.forEach((mat) => {
          mat.emissive.set(organ.emissive);
          mat.emissiveIntensity              = organ.base;
          mat.userData.organKey              = organ.key;
          mat.userData.baseEmissiveIntensity = organ.base;
        });
        node.userData.organKey = organ.key;
        // Register first mesh per organ key for focus positioning
        if (!organMeshMapRef.current.has(organ.key)) {
          organMeshMapRef.current.set(organ.key, node);
        }
      } else {
        mats.forEach((mat) => {
          mat.userData.baseEmissiveIntensity = mat.emissiveIntensity;

          if (needsRecolour) {
            const { r, g, b } = mat.color;
            const lum          = 0.299 * r + 0.587 * g + 0.114 * b;
            if (lum > 0.55) {
              mat.color.copy(BONE_CREAM);
              mat.roughness = 0.72;
              mat.metalness = 0.00;
            }
          }
        });
        // Non-organ meshes (bones, skull, connective tissue) must not intercept
        // raycasts — this lets clicks pass through the skull to reach the brain,
        // through ribs to reach the heart, etc.
        node.raycast = () => {};
      }
    });

    // ── Safety net: if brain still unregistered, find the highest non-organ mesh ─
    // Some GLB files encode the brain under an unpredictable name. As a last resort,
    // collect all non-organ meshes in the upper 20% of the scene's bounding box
    // (where the skull/brain lives) and register the topmost one as brain.
    if (!organMeshMapRef.current.has("brain")) {
      const sceneBox   = new THREE.Box3().setFromObject(scene);
      const sceneMaxY  = sceneBox.max.y;
      const sceneMinY  = sceneBox.min.y;
      const headThresh = sceneMinY + (sceneMaxY - sceneMinY) * 0.80; // top 20%

      let bestMesh: THREE.Mesh | null = null;
      let bestY = -Infinity;

      scene.traverse((node) => {
        if (!(node instanceof THREE.Mesh)) return;
        if (node.userData.organKey) return; // already registered
        const worldPos = new THREE.Vector3();
        node.getWorldPosition(worldPos);
        if (worldPos.y > headThresh && worldPos.y > bestY) {
          bestY    = worldPos.y;
          bestMesh = node;
        }
      });

      if (bestMesh) {
        const brainConfig = ORGAN_REGISTRY.find((o) => o.key === "brain")!;
        const mats        = getMaterials(bestMesh);
        mats.forEach((mat) => {
          mat.emissive.set(brainConfig.emissive);
          mat.emissiveIntensity              = brainConfig.base;
          mat.userData.organKey              = brainConfig.key;
          mat.userData.baseEmissiveIntensity = brainConfig.base;
        });
        (bestMesh as THREE.Mesh).userData.organKey = brainConfig.key;
        // Restore raycast (was disabled in the else-branch above)
        (bestMesh as THREE.Mesh).raycast = THREE.Mesh.prototype.raycast;
        organMeshMapRef.current.set("brain", bestMesh as THREE.Mesh);
      }
    }
  }, [scene, needsRecolour]);

  // ── 2. Auto-fit camera + capture default position ─────────────────────────
  useEffect(() => {
    const box = new THREE.Box3().setFromObject(scene);
    if (box.isEmpty()) return;

    const sphere = new THREE.Sphere();
    box.getBoundingSphere(sphere);
    const { center, radius } = sphere;

    const cam    = camera as THREE.PerspectiveCamera;
    const fovRad = (cam.fov * Math.PI) / 180;
    const dist   = (radius / Math.sin(fovRad / 2)) * 1.25;
    defaultCamDistRef.current = dist;          // annotation zoom thresholds are relative to this

    camera.position.set(center.x, center.y, center.z + dist);
    camera.near = 0.001; // tiny near plane — lets camera go deep inside the body
    camera.far  = dist * 200;
    camera.updateProjectionMatrix();

    const ctrl = controls as unknown as OrbCtrl | null;
    if (ctrl) {
      ctrl.target.copy(center);
      ctrl.update();
    }

    // Capture after auto-fit — used as the return-to position on deselect
    defaultCamPos.current = camera.position.clone();
    defaultLookAt.current = ctrl ? ctrl.target.clone() : center.clone();
  }, [scene, camera, controls]);

  // ── 3. System filter ──────────────────────────────────────────────────────
  useEffect(() => {
    scene.traverse((node) => {
      if (!(node instanceof THREE.Mesh)) return;
      const mats = getMaterials(node);

      if (activeSystem === "all") {
        node.visible = true;
        mats.forEach((mat) => { mat.transparent = false; mat.opacity = 1; });
        return;
      }

      const inSystem = meshBelongsToSystem(node.name, activeSystem);
      node.visible = true;
      mats.forEach((mat) => {
        mat.transparent = !inSystem;
        mat.opacity     = inSystem ? 1 : 0.08;
      });
    });
  }, [scene, activeSystem]);

  // ── 4. TRANSPARENCY ENGINE + CINEMATIC FOCUS ──────────────────────────────
  // Runs only when selectedOrgan changes — NOT every frame.
  // All DOM/material work is imperative via refs.
  useEffect(() => {
    const ctrl = controls as unknown as OrbCtrl | null;

    if (selectedOrgan) {
      bodyShiftActiveRef.current = true;

      // ── Apply transparency to all meshes ──────────────────────────────────
      scene.traverse((node) => {
        if (!(node instanceof THREE.Mesh)) return;
        const mats     = getMaterials(node);
        const isTarget = node.userData.organKey === selectedOrgan;

        mats.forEach((mat) => {
          // Snapshot current state once — safe to re-snapshot if organ changes
          mat.userData.focusOrigOpacity     = mat.opacity;
          mat.userData.focusOrigTransparent = mat.transparent;

          if (isTarget) {
            mat.transparent = false;
            mat.opacity     = 1;
          } else {
            mat.transparent = true;
            mat.opacity     = 0.15;
          }
        });

        // Highlight: lift emissive on selected organ, keep scale interaction clean
        if (isTarget) {
          const organ = getOrganConfig(node.name);
          if (organ) {
            mats.forEach((mat) => {
              // 60% of hover value — visible glow without full hover brightness
              mat.emissiveIntensity = organ.hover * 0.6;
            });
          }
          focusedMeshRef.current = node;
        }
      });

      // ── Set camera lerp targets ───────────────────────────────────────────
      if (ORGAN_MODEL_MAP[selectedOrgan]) {
        // Standalone model available → focus camera on the extracted organ (right side)
        camLookTarget.current.set(0.8, 0.2, 0.4);
        camTargetPos.current.set(2.2, 0.9, 3.0);
        animFrames.current = 0;
        isAnimating.current = true;
      } else {
        // No standalone model → zoom to organ inside body (existing behaviour)
        const focusMesh = organMeshMapRef.current.get(selectedOrgan);
        if (focusMesh) {
          const worldPos = new THREE.Vector3();
          focusMesh.getWorldPosition(worldPos);

          const organBox  = new THREE.Box3().setFromObject(focusMesh);
          const organSize = organBox.getSize(new THREE.Vector3()).length();
          const focusDist = Math.max(organSize * 2.2, 0.35);

          const currentLook = ctrl ? ctrl.target.clone() : new THREE.Vector3();
          const viewDir     = camera.position.clone().sub(currentLook).normalize();

          camLookTarget.current.copy(worldPos);
          camTargetPos.current.copy(worldPos).addScaledVector(viewDir, focusDist);
          animFrames.current = 0;
          isAnimating.current = true;
        }
      }

    } else {
      bodyShiftActiveRef.current = false;

      // ── DESELECT: restore all material snapshots ──────────────────────────
      scene.traverse((node) => {
        if (!(node instanceof THREE.Mesh)) return;
        const mats = getMaterials(node);

        mats.forEach((mat) => {
          if (mat.userData.focusOrigOpacity !== undefined) {
            mat.opacity     = mat.userData.focusOrigOpacity as number;
            mat.transparent = mat.userData.focusOrigTransparent as boolean;
            delete mat.userData.focusOrigOpacity;
            delete mat.userData.focusOrigTransparent;
          }
          // Restore emissive to base
          mat.emissiveIntensity = mat.userData.baseEmissiveIntensity ?? 0;
        });
      });

      focusedMeshRef.current = null;

      // ── Return camera to auto-fit position ────────────────────────────────
      if (defaultCamPos.current && defaultLookAt.current) {
        camTargetPos.current.copy(defaultCamPos.current);
        camLookTarget.current.copy(defaultLookAt.current);
        animFrames.current = 0;
        isAnimating.current = true;
      }
    }
  }, [selectedOrgan, scene, camera, controls]);

  // ── 5. CAMERA LERP — runs every frame but only moves when isAnimating ─────
  // No state reads, no allocations: entirely ref-based.
  //
  // Convergence uses lookClose only (ctrl.target is not overridden by
  // OrbitControls.update, so it reliably converges). posClose was removed
  // because ctrl.update() rewrites camera.position each frame, preventing
  // posClose from ever becoming true and freezing the controls.
  // animFrames hard-stop (150 frames ≈ 2.5 s) guarantees controls always
  // unlock even in degenerate cases.
  useFrame(() => {
    // ── Body shift for cinematic organ extraction ─────────────────────────────
    // Runs every frame regardless of camera animation state.
    if (groupRef.current) {
      const targetX = bodyShiftActiveRef.current ? -0.6 : 0;
      groupRef.current.position.x += (targetX - groupRef.current.position.x) * 0.06;
    }

    if (!isAnimating.current) return;

    const ctrl = controls as unknown as OrbCtrl | null;
    const SPEED = 0.07;

    animFrames.current += 1;

    camera.position.lerp(camTargetPos.current, SPEED);
    if (ctrl) {
      ctrl.target.lerp(camLookTarget.current, SPEED);
      ctrl.update();
    }

    const lookClose = (ctrl?.target ?? camLookTarget.current).distanceTo(camLookTarget.current) < 0.005;
    const timedOut  = animFrames.current > 150;

    if (lookClose || timedOut) {
      if (ctrl) {
        ctrl.target.copy(camLookTarget.current);
        ctrl.update();
      } else {
        camera.position.copy(camTargetPos.current);
      }
      animFrames.current  = 0;
      isAnimating.current = false;
    }
  });

  // ── Pointer handlers — imperative, zero re-renders ────────────────────────

  const handlePointerOver = (e: ThreeEvent<PointerEvent>) => {
    const mesh  = e.object as THREE.Mesh;
    const organ = getOrganConfigByKey(mesh.userData.organKey as string | undefined);
    if (!organ) return;
    e.stopPropagation();
    getMaterials(mesh).forEach((mat) => { mat.emissiveIntensity = organ.hover; });
    // Only scale up if this mesh is NOT the currently focused organ
    if (mesh !== focusedMeshRef.current) mesh.scale.setScalar(1.04);
    document.body.style.cursor = "pointer";
  };

  const handlePointerOut = (e: ThreeEvent<PointerEvent>) => {
    const mesh  = e.object as THREE.Mesh;
    const organ = getOrganConfigByKey(mesh.userData.organKey as string | undefined);
    if (!organ) return;
    getMaterials(mesh).forEach((mat) => {
      // If focused: keep the focus emissive glow, otherwise restore base
      mat.emissiveIntensity =
        mesh === focusedMeshRef.current
          ? organ.hover * 0.6
          : (mat.userData.baseEmissiveIntensity ?? 0);
    });
    if (mesh !== focusedMeshRef.current) mesh.scale.setScalar(1.0);
    document.body.style.cursor = "default";
  };

  const handleClick = (e: ThreeEvent<MouseEvent>) => {
    const mesh  = e.object as THREE.Mesh;
    const organ = getOrganConfigByKey(mesh.userData.organKey as string | undefined);
    if (!organ) return;
    e.stopPropagation();
    onOrganClick(organ.key);
    // Fire organ position callback synchronously so BodyScene can seed ExtractedOrgan start pos
    if (onOrganReady) {
      const startPos = new THREE.Vector3();
      const regMesh  = organMeshMapRef.current.get(organ.key) ?? mesh;
      regMesh.getWorldPosition(startPos);
      onOrganReady(organ.key, startPos);
    }
  };

  return (
    <group ref={groupRef}>
      <primitive
        object={scene}
        scale={0.22}
        position={[0, 0, 0]}
        onPointerOver={handlePointerOver}
        onPointerOut={handlePointerOut}
        onClick={handleClick}
      />
      {highlightEntries.map(({ mesh, color }, i) => (
        <OrganHighlight key={i} mesh={mesh} color={color} />
      ))}
    </group>
  );
}
