"use client";

export function AnimatedGrid() {
  return (
    <>
      {/* Top-left corner accent */}
      <div
        className="fixed top-0 left-0 w-96 h-96 pointer-events-none z-0"
        style={{
          opacity: "var(--animated-grid-opacity)",
          background:
            "radial-gradient(ellipse at top left, rgba(10,132,255,0.12) 0%, transparent 65%)",
        }}
        aria-hidden="true"
      />
      {/* Bottom-right corner accent */}
      <div
        className="fixed bottom-0 right-0 w-96 h-96 pointer-events-none z-0"
        style={{
          opacity: "var(--animated-grid-opacity)",
          background:
            "radial-gradient(ellipse at bottom right, rgba(50,215,75,0.09) 0%, transparent 65%)",
        }}
        aria-hidden="true"
      />
    </>
  );
}
