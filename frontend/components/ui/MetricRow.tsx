import { cn } from "@/lib/utils";

interface MetricRowProps {
  label: string;
  value: string | number;
  unit?: string;
  color?: "cyan" | "green" | "amber" | "red" | "white";
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function MetricRow({
  label,
  value,
  unit,
  color = "cyan",
  size = "md",
  className,
}: MetricRowProps) {
  const colorClass = {
    cyan: "text-cyan",
    green: "text-green",
    amber: "text-amber",
    red: "text-red",
    white: "text-white",
  }[color];

  const sizeClass = {
    sm: "text-lg",
    md: "text-2xl",
    lg: "text-3xl",
  }[size];

  return (
    <div className={cn("flex flex-col gap-0.5", className)}>
      <span className="metric-label">{label}</span>
      <div className="flex items-baseline gap-1.5">
        <span className={cn("font-mono font-semibold", colorClass, sizeClass)}>
          {value}
        </span>
        {unit && (
          <span className="text-xs text-slate-500 font-mono">{unit}</span>
        )}
      </div>
    </div>
  );
}
