"use client";

import { OrbitControls } from "@react-three/drei";

export function CameraController() {
  return (
    <OrbitControls
      makeDefault
      enableRotate
      enableZoom
      enablePan
      screenSpacePanning   // pan parallel to screen (up/down/left/right feel natural)
      panSpeed={1.5}
      minDistance={0.01}
      maxDistance={100}    // large enough for any auto-fit distance
      enableDamping
      dampingFactor={0.07}
      // No fixed target — SkeletonModel auto-fit sets it per model
    />
  );
}
