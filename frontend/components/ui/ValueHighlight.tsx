import { cn } from "@/lib/utils";
import type { Severity } from "@/lib/types";

interface ValueHighlightProps {
  value: string | number;
  unit?: string;
  severity?: Severity;
  label?: string;
  referenceRange?: string;
  className?: string;
}

export function ValueHighlight({
  value,
  unit,
  severity = "normal",
  label,
  referenceRange,
  className,
}: ValueHighlightProps) {
  const colorMap: Record<Severity, string> = {
    normal: "text-green border-green/20 bg-green/5",
    borderline: "text-amber border-amber/20 bg-amber/5",
    critical: "text-red border-red/20 bg-red/5",
  };

  const dotMap: Record<Severity, string> = {
    normal: "bg-green",
    borderline: "bg-amber",
    critical: "bg-red animate-pulse",
  };

  return (
    <div
      className={cn(
        "inline-flex flex-col gap-0.5 px-3 py-2 rounded-lg border",
        colorMap[severity],
        className
      )}
    >
      {label && (
        <span className="text-xs text-slate-400 font-medium">{label}</span>
      )}
      <div className="flex items-center gap-2">
        <span className={cn("w-2 h-2 rounded-full shrink-0", dotMap[severity])} />
        <span className="font-mono font-semibold text-sm">
          {value}
          {unit && (
            <span className="font-normal text-xs ml-1 opacity-70">{unit}</span>
          )}
        </span>
      </div>
      {referenceRange && (
        <span className="text-xs text-slate-500 font-mono">
          ref: {referenceRange}
        </span>
      )}
    </div>
  );
}
