"use client";

export function AnimatedGrid() {
  return (
    <>
      {/* Top-left blue — primary ambient */}
      <div
        className="fixed top-0 left-0 pointer-events-none z-0"
        style={{
          width: "700px",
          height: "600px",
          opacity: "var(--animated-grid-opacity)",
          background:
            "radial-gradient(ellipse at top left, rgba(10,132,255,0.11) 0%, transparent 65%)",
          animation: "ambientDrift 25s ease-in-out infinite",
        }}
        aria-hidden="true"
      />
      {/* Bottom-right green — secondary ambient */}
      <div
        className="fixed bottom-0 right-0 pointer-events-none z-0"
        style={{
          width: "600px",
          height: "500px",
          opacity: "var(--animated-grid-opacity)",
          background:
            "radial-gradient(ellipse at bottom right, rgba(50,215,75,0.08) 0%, transparent 65%)",
          animation: "ambientDrift 30s ease-in-out infinite reverse",
        }}
        aria-hidden="true"
      />
      {/* Top-right purple — tertiary depth */}
      <div
        className="fixed top-0 right-0 pointer-events-none z-0"
        style={{
          width: "400px",
          height: "400px",
          opacity: "var(--animated-grid-opacity)",
          background:
            "radial-gradient(ellipse at top right, rgba(191,90,242,0.05) 0%, transparent 65%)",
          animation: "ambientDrift 35s ease-in-out infinite 5s",
        }}
        aria-hidden="true"
      />
      {/* Bottom-left amber — warm accent */}
      <div
        className="fixed bottom-0 left-0 pointer-events-none z-0"
        style={{
          width: "350px",
          height: "350px",
          opacity: "var(--animated-grid-opacity)",
          background:
            "radial-gradient(ellipse at bottom left, rgba(255,159,10,0.04) 0%, transparent 65%)",
          animation: "ambientDrift 28s ease-in-out infinite 10s",
        }}
        aria-hidden="true"
      />
      {/* Center diffuse — adds atmospheric depth */}
      <div
        className="fixed left-1/4 top-1/3 pointer-events-none z-0"
        style={{
          width: "800px",
          height: "400px",
          opacity: "var(--animated-grid-opacity)",
          background:
            "radial-gradient(ellipse at center, rgba(10,132,255,0.04) 0%, transparent 60%)",
        }}
        aria-hidden="true"
      />
    </>
  );
}
