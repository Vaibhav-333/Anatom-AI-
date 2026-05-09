import { AlertTriangle, Info, CheckCircle, XCircle, X } from "lucide-react";
import { cn } from "@/lib/utils";

type AlertVariant = "info" | "success" | "warning" | "error";

interface AlertBoxProps {
  variant?: AlertVariant;
  title?: string;
  children: React.ReactNode;
  className?: string;
  dismissible?: boolean;
  onDismiss?: () => void;
}

const variantConfig: Record<
  AlertVariant,
  { bg: string; border: string; iconColor: string; titleColor: string; icon: React.ElementType }
> = {
  info: {
    bg: "rgba(10,132,255,0.08)",
    border: "rgba(10,132,255,0.2)",
    icon: Info,
    iconColor: "#0A84FF",
    titleColor: "#5AC8FA",
  },
  success: {
    bg: "rgba(50,215,75,0.08)",
    border: "rgba(50,215,75,0.2)",
    icon: CheckCircle,
    iconColor: "#32D74B",
    titleColor: "#4CD964",
  },
  warning: {
    bg: "rgba(255,159,10,0.08)",
    border: "rgba(255,159,10,0.2)",
    icon: AlertTriangle,
    iconColor: "#FF9F0A",
    titleColor: "#FFAC30",
  },
  error: {
    bg: "rgba(255,69,58,0.08)",
    border: "rgba(255,69,58,0.2)",
    icon: XCircle,
    iconColor: "#FF453A",
    titleColor: "#FF6961",
  },
};

export function AlertBox({
  variant = "info",
  title,
  children,
  className,
  dismissible = false,
  onDismiss,
}: AlertBoxProps) {
  const cfg = variantConfig[variant];
  const Icon = cfg.icon;

  return (
    <div
      className={cn("rounded-xl p-4 flex gap-3", className)}
      style={{
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
      }}
    >
      <Icon className="w-4 h-4 mt-0.5 shrink-0" style={{ color: cfg.iconColor }} />
      <div className="flex-1 min-w-0">
        {title && (
          <p className="text-[13px] font-semibold mb-1" style={{ color: cfg.titleColor }}>
            {title}
          </p>
        )}
        <div className="text-[12.5px] leading-relaxed" style={{ color: "var(--label-secondary)" }}>
          {children}
        </div>
      </div>
      {dismissible && (
        <button
          onClick={onDismiss}
          className="shrink-0 transition-colors"
          style={{ color: "var(--label-tertiary)" }}
          onMouseEnter={(e) => ((e.target as HTMLElement).style.color = "var(--label-primary)")}
          onMouseLeave={(e) => ((e.target as HTMLElement).style.color = "var(--label-tertiary)")}
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}
