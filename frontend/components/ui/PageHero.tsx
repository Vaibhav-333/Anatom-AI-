"use client";

interface PageHeroProps {
  src: string;
  children: React.ReactNode;
  /** 0–100 percentage opacity, default 30 */
  opacity?: number;
  objectPosition?: string;
  /** CSS colour for the bottom accent shimmer */
  accentColor?: string;
  className?: string;
}

export function PageHero({
  src,
  children,
  opacity = 30,
  objectPosition = "center",
  accentColor = "rgba(10,132,255,0.20)",
  className = "",
}: PageHeroProps) {
  return (
    <div
      className={`relative rounded-2xl overflow-hidden ${className}`}
      style={{
        background: "#1C1C1E",
        boxShadow: "0 2px 20px rgba(0,0,0,0.65), inset 0 0.5px 0 rgba(255,255,255,0.05)",
      }}
    >
      {/* Background photo */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt=""
        loading="eager"
        decoding="async"
        aria-hidden
        className="absolute inset-0 w-full h-full object-cover pointer-events-none select-none"
        style={{ opacity: opacity / 100, objectPosition }}
      />

      {/* Left-to-right vignette */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "linear-gradient(90deg, rgba(0,0,0,0.82) 0%, rgba(0,0,0,0.40) 55%, rgba(0,0,0,0.10) 100%)",
        }}
      />

      {/* Bottom dark wash */}
      <div
        className="absolute bottom-0 left-0 right-0 h-16 pointer-events-none"
        style={{
          background: "linear-gradient(to top, rgba(0,0,0,0.60) 0%, rgba(0,0,0,0) 100%)",
        }}
      />

      {/* Accent shimmer line */}
      <div
        className="absolute bottom-0 left-0 right-0 h-px pointer-events-none"
        style={{
          background: `linear-gradient(90deg, transparent 0%, ${accentColor} 40%, ${accentColor} 60%, transparent 100%)`,
        }}
      />

      <div className="relative">{children}</div>
    </div>
  );
}
