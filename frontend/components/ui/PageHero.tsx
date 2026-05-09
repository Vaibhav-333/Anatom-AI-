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
        background: "var(--glass-bg)",
        boxShadow: "var(--glass-shadow)",
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

      {/* Left-to-right vignette — adapts to theme via var */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "linear-gradient(90deg, var(--bg-card) 0%, rgba(0,0,0,0.30) 55%, transparent 100%)",
        }}
      />

      {/* Bottom dark wash */}
      <div
        className="absolute bottom-0 left-0 right-0 h-16 pointer-events-none"
        style={{
          background: "linear-gradient(to top, var(--bg-card) 0%, transparent 100%)",
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
