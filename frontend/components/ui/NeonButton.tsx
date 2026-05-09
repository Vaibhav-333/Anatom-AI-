"use client";

import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface NeonButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: "cyan" | "green" | "red" | "ghost";
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  loading?: boolean;
  className?: string;
  type?: "button" | "submit" | "reset";
  icon?: React.ReactNode;
}

const variantConfig = {
  cyan: {
    base: {
      background: "rgba(10,132,255,0.18)",
      color: "#0A84FF",
      border: "1px solid rgba(10,132,255,0.28)",
    },
    hoverBg:   "rgba(10,132,255,0.26)",
    glowShadow:"0 4px 16px rgba(10,132,255,0.35), 0 1px 4px rgba(10,132,255,0.18)",
  },
  green: {
    base: {
      background: "rgba(50,215,75,0.16)",
      color: "#32D74B",
      border: "1px solid rgba(50,215,75,0.26)",
    },
    hoverBg:   "rgba(50,215,75,0.24)",
    glowShadow:"0 4px 16px rgba(50,215,75,0.32), 0 1px 4px rgba(50,215,75,0.16)",
  },
  red: {
    base: {
      background: "rgba(255,69,58,0.16)",
      color: "#FF453A",
      border: "1px solid rgba(255,69,58,0.26)",
    },
    hoverBg:   "rgba(255,69,58,0.24)",
    glowShadow:"0 4px 16px rgba(255,69,58,0.32), 0 1px 4px rgba(255,69,58,0.16)",
  },
  ghost: {
    base: {
      background: "var(--btn-secondary-bg)",
      color: "var(--label-secondary)",
      border: "1px solid var(--border-subtle)",
    },
    hoverBg:   "var(--btn-secondary-hover-bg)",
    glowShadow:"none",
  },
} as const;

const sizeStyles = {
  sm: "px-3.5 py-1.5 text-xs gap-1.5 rounded-lg",
  md: "px-5 py-2.5 text-sm gap-2 rounded-xl",
  lg: "px-7 py-3 text-[15px] gap-2.5 rounded-xl",
};

export function NeonButton({
  children,
  onClick,
  variant = "cyan",
  size = "md",
  disabled = false,
  loading = false,
  className,
  type = "button",
  icon,
}: NeonButtonProps) {
  const cfg = variantConfig[variant];
  const isDisabled = disabled || loading;

  return (
    <motion.button
      type={type}
      onClick={onClick}
      disabled={isDisabled}
      whileHover={isDisabled ? {} : { scale: 1.018, y: -1 }}
      whileTap={isDisabled ? {} : { scale: 0.982, y: 0 }}
      className={cn(
        "inline-flex items-center justify-center font-semibold tracking-tight",
        sizeStyles[size],
        isDisabled && "opacity-45 cursor-not-allowed",
        className
      )}
      style={{
        ...cfg.base,
        transition: "background 0.2s ease, box-shadow 0.2s ease, color 0.2s ease",
      }}
      onMouseEnter={isDisabled ? undefined : (e) => {
        const el = e.currentTarget as HTMLElement;
        el.style.background = cfg.hoverBg;
        if (cfg.glowShadow !== "none") el.style.boxShadow = cfg.glowShadow;
        if (variant === "ghost") el.style.color = "var(--btn-secondary-hover-color)";
      }}
      onMouseLeave={isDisabled ? undefined : (e) => {
        const el = e.currentTarget as HTMLElement;
        el.style.background = cfg.base.background;
        el.style.boxShadow = "";
        if (variant === "ghost") el.style.color = cfg.base.color;
      }}
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        icon && <span className="shrink-0">{icon}</span>
      )}
      {children}
    </motion.button>
  );
}
