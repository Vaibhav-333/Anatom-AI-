"use client";

import Image from "next/image";
import { cn } from "@/lib/utils";

// ── Background fill variant ───────────────────────────────────────────────────
// Parent must be position:relative with an explicit height (or use h-full etc.)

interface BgImageProps {
  src: string;
  alt: string;
  opacity?: number;            // 0–100, default 8
  overlayColor?: string;       // CSS colour for the dark wash, default navy
  zoom?: boolean;              // hover scale effect
  className?: string;
  objectPosition?: string;
}

export function BgImage({
  src,
  alt,
  opacity = 8,
  overlayColor = "rgba(10,15,30,0.72)",
  zoom = false,
  className,
  objectPosition = "center",
}: BgImageProps) {
  return (
    <div className={cn("absolute inset-0 overflow-hidden rounded-[inherit]", className)}>
      <Image
        src={src}
        alt={alt}
        fill
        sizes="100%"
        loading="lazy"
        decoding="async"
        className={cn(
          "object-cover select-none pointer-events-none transition-transform duration-700",
          zoom && "group-hover:scale-105"
        )}
        style={{ opacity: opacity / 100, objectPosition }}
      />
      {/* Dark wash so text stays legible */}
      <div
        className="absolute inset-0"
        style={{ background: overlayColor, mixBlendMode: "multiply" }}
      />
    </div>
  );
}

// ── Thumbnail variant ─────────────────────────────────────────────────────────
// Inline image with rounded corners, soft shadow, and optional hover zoom.

interface ThumbImageProps {
  src: string;
  alt: string;
  width: number;
  height: number;
  opacity?: number;
  zoom?: boolean;
  rounded?: string;
  className?: string;
  objectPosition?: string;
}

export function ThumbImage({
  src,
  alt,
  width,
  height,
  opacity = 100,
  zoom = true,
  rounded = "rounded-xl",
  className,
  objectPosition = "center",
}: ThumbImageProps) {
  return (
    <div
      className={cn(
        "overflow-hidden shrink-0",
        rounded,
        className
      )}
      style={{ width, height }}
    >
      <Image
        src={src}
        alt={alt}
        width={width}
        height={height}
        loading="lazy"
        decoding="async"
        className={cn(
          "object-cover w-full h-full transition-transform duration-500",
          zoom && "group-hover:scale-110"
        )}
        style={{ opacity: opacity / 100, objectPosition }}
      />
    </div>
  );
}

// ── Fade-edge image variant ───────────────────────────────────────────────────
// Image with a left-to-right gradient fade — great for panel sidebars.

interface FadeImageProps {
  src: string;
  alt: string;
  width: number;
  height: number;
  opacity?: number;
  fadeFrom?: "left" | "right" | "bottom";
  rounded?: string;
  className?: string;
  objectPosition?: string;
}

export function FadeImage({
  src,
  alt,
  width,
  height,
  opacity = 30,
  fadeFrom = "left",
  rounded = "rounded-xl",
  className,
  objectPosition = "center",
}: FadeImageProps) {
  const gradientMap = {
    left:   "linear-gradient(to right, rgba(10,15,30,1) 0%, rgba(10,15,30,0) 50%)",
    right:  "linear-gradient(to left,  rgba(10,15,30,1) 0%, rgba(10,15,30,0) 50%)",
    bottom: "linear-gradient(to top,   rgba(10,15,30,1) 0%, rgba(10,15,30,0) 50%)",
  };

  return (
    <div
      className={cn("relative overflow-hidden shrink-0", rounded, className)}
      style={{ width, height }}
    >
      <Image
        src={src}
        alt={alt}
        width={width}
        height={height}
        loading="lazy"
        decoding="async"
        className="object-cover w-full h-full"
        style={{ opacity: opacity / 100, objectPosition }}
      />
      <div
        className="absolute inset-0"
        style={{ background: gradientMap[fadeFrom] }}
      />
    </div>
  );
}
