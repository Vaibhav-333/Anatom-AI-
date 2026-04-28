"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[ANATOM ERROR]", error);
  }, [error]);

  return (
    <div
      style={{
        padding: 32,
        minHeight: "60vh",
        display: "flex",
        flexDirection: "column",
        gap: 16,
        fontFamily: "monospace",
        color: "#e2e8f0",
      }}
    >
      <h1 style={{ color: "#f87171", fontSize: 20, margin: 0 }}>
        Page Error — {error.message || "Unknown error"}
      </h1>
      {error.digest && (
        <p style={{ color: "#94a3b8", margin: 0, fontSize: 12 }}>
          Digest: {error.digest}
        </p>
      )}
      <pre
        style={{
          background: "#0f172a",
          border: "1px solid #1e293b",
          borderRadius: 8,
          padding: 16,
          fontSize: 11,
          overflowX: "auto",
          whiteSpace: "pre-wrap",
          color: "#fca5a5",
          maxHeight: 400,
          overflowY: "auto",
        }}
      >
        {error.stack ?? "No stack trace available"}
      </pre>
      <button
        onClick={reset}
        style={{
          alignSelf: "flex-start",
          padding: "8px 20px",
          background: "#0a84ff",
          color: "#fff",
          border: "none",
          borderRadius: 8,
          cursor: "pointer",
          fontSize: 13,
        }}
      >
        Try again
      </button>
    </div>
  );
}
