"use client";

import { Suspense } from "react";
import dynamic from "next/dynamic";
import { Box } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";

const BodyScene = dynamic(
  () => import("@/components/3d/BodyScene").then((m) => m.BodyScene),
  { ssr: false, loading: () => <ViewerPlaceholder /> }
);

function ViewerPlaceholder() {
  return (
    <div className="flex items-center justify-center h-full bg-navy-800 rounded-xl border border-glass-border">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-cyan/30 border-t-cyan rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm text-slate-500">Loading 3D engine...</p>
      </div>
    </div>
  );
}

function ViewerContent() {
  return (
    <div className="flex flex-col h-[calc(100vh-5.5rem)] gap-4 animate-fade-in">
      <PageHeader
        title="3D Body Viewer"
        subtitle="Interactive skeleton visualization — drag to rotate, scroll to zoom"
        icon={<Box className="w-5 h-5" />}
      />

      <div className="flex-1 relative rounded-2xl overflow-hidden border border-glass-border bg-navy-800 min-h-0">
        <BodyScene />

        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-xs text-slate-600 bg-navy-800/80 px-3 py-1.5 rounded-full border border-glass-border pointer-events-none">
          Drag to rotate · Scroll to zoom · Right-drag to pan
        </div>
      </div>
    </div>
  );
}

export default function ViewerPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-[calc(100vh-5.5rem)]">
          <div className="w-8 h-8 border-2 border-cyan/30 border-t-cyan rounded-full animate-spin" />
        </div>
      }
    >
      <ViewerContent />
    </Suspense>
  );
}
