import { cn } from "@/lib/utils";
import type { RiskLevel, Severity } from "@/lib/types";

// ── Risk Level Badge ──────────────────────────
interface RiskBadgeProps { level: RiskLevel; className?: string; }

export function RiskBadge({ level, className }: RiskBadgeProps) {
  const config = {
    low:      { label: "Low Risk",   cls: "badge-normal"   },
    moderate: { label: "Moderate",   cls: "badge-warning"  },
    high:     { label: "High Risk",  cls: "badge-critical" },
    critical: { label: "Critical",   cls: "badge-critical" },
  }[level];
  return (
    <span className={cn(config.cls, className)}>
      <span className="w-1.5 h-1.5 rounded-full bg-current inline-block" />
      {config.label}
    </span>
  );
}

// ── Severity Badge ────────────────────────────
interface SeverityBadgeProps { severity: Severity; className?: string; }

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  const config = {
    normal:     { label: "Normal",     cls: "badge-normal"   },
    borderline: { label: "Borderline", cls: "badge-warning"  },
    critical:   { label: "Critical",   cls: "badge-critical" },
  }[severity];
  return (
    <span className={cn(config.cls, className)}>
      <span className="w-1.5 h-1.5 rounded-full bg-current inline-block" />
      {config.label}
    </span>
  );
}

// ── RANO Badge ────────────────────────────────
interface RANOBadgeProps { category: "CR" | "PR" | "SD" | "PD"; className?: string; }

export function RANOBadge({ category, className }: RANOBadgeProps) {
  const config = {
    CR: { label: "CR — Complete Response",   cls: "badge-normal"   },
    PR: { label: "PR — Partial Response",    cls: "badge-info"     },
    SD: { label: "SD — Stable Disease",      cls: "badge-warning"  },
    PD: { label: "PD — Progressive Disease", cls: "badge-critical" },
  }[category];
  return <span className={cn(config.cls, className)}>{config.label}</span>;
}

// ── Status Badge ──────────────────────────────
interface StatusBadgeProps {
  status: "online" | "offline" | "processing" | "error" | "warning";
  label?: string;
  className?: string;
}

const STATUS_COLORS = {
  online:     { dot: "#32D74B", pulse: true,  text: "#32D74B", defaultLabel: "Online"     },
  offline:    { dot: "#636366", pulse: false, text: "#636366", defaultLabel: "Offline"    },
  processing: { dot: "#0A84FF", pulse: true,  text: "#0A84FF", defaultLabel: "Processing" },
  error:      { dot: "#FF453A", pulse: false, text: "#FF453A", defaultLabel: "Error"      },
  warning:    { dot: "#FF9F0A", pulse: true,  text: "#FF9F0A", defaultLabel: "Warning"    },
};

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const cfg = STATUS_COLORS[status];
  return (
    <span
      className={cn("inline-flex items-center gap-1.5 text-[11px] font-semibold", className)}
      style={{ color: cfg.text }}
    >
      <span
        className={cn("w-2 h-2 rounded-full shrink-0", cfg.pulse && "status-pulse")}
        style={{ background: cfg.dot }}
      />
      {label ?? cfg.defaultLabel}
    </span>
  );
}
