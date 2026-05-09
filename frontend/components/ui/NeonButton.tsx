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

const variantStyles: Record<string, string> = {
  cyan: [
    "text-[#0A84FF]",
    "bg-[rgba(10,132,255,0.18)]",
    "hover:bg-[rgba(10,132,255,0.26)]",
  ].join(" "),

  green: [
    "text-[#32D74B]",
    "bg-[rgba(50,215,75,0.16)]",
    "hover:bg-[rgba(50,215,75,0.24)]",
  ].join(" "),

  red: [
    "text-[#FF453A]",
    "bg-[rgba(255,69,58,0.16)]",
    "hover:bg-[rgba(255,69,58,0.24)]",
  ].join(" "),

  ghost: [
    "text-[color:var(--label-secondary)]",
    "bg-[color:var(--btn-secondary-bg)]",
    "hover:text-[color:var(--label-primary)]",
  ].join(" "),
};

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
  return (
    <motion.button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      whileHover={{ scale: disabled || loading ? 1 : 1.018 }}
      whileTap={{ scale: disabled || loading ? 1 : 0.982 }}
      className={cn(
        "inline-flex items-center justify-center font-semibold tracking-tight",
        "transition-all duration-200",
        variantStyles[variant],
        sizeStyles[size],
        (disabled || loading) && "opacity-45 cursor-not-allowed",
        className
      )}
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
