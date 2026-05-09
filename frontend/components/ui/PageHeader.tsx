import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  actions?: React.ReactNode;
  badge?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  subtitle,
  icon,
  actions,
  badge,
  className,
}: PageHeaderProps) {
  return (
    <div className={cn("flex items-start justify-between gap-4 p-6", className)}>
      <div className="flex items-start gap-3.5">
        {icon && (
          <div
            className="p-2.5 rounded-xl shrink-0 mt-0.5"
            style={{
              background: "rgba(10,132,255,0.14)",
              color: "#0A84FF",
            }}
          >
            {icon}
          </div>
        )}
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1
              className="text-[28px] font-extrabold tracking-tight leading-tight"
              style={{ color: "var(--label-primary)", letterSpacing: "-0.025em" }}
            >
              {title}
            </h1>
            {badge}
          </div>
          {subtitle && (
            <p
              className="text-sm mt-1 leading-relaxed"
              style={{ color: "var(--label-secondary)" }}
            >
              {subtitle}
            </p>
          )}
        </div>
      </div>
      {actions && (
        <div className="flex items-center gap-2 shrink-0">{actions}</div>
      )}
    </div>
  );
}

export function SectionDivider({
  label,
  className,
}: {
  label?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-3 my-5", className)}>
      <div
        className="h-px flex-1"
        style={{ background: "var(--border-subtle)" }}
      />
      {label && (
        <span
          className="text-[10.5px] font-semibold uppercase tracking-widest px-2"
          style={{ color: "var(--label-secondary)" }}
        >
          {label}
        </span>
      )}
      <div
        className="h-px flex-1"
        style={{ background: "var(--border-subtle)" }}
      />
    </div>
  );
}
