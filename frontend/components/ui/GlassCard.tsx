"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  glow?: "cyan" | "green" | "red" | "amber" | "none";
  animate?: boolean;
  onClick?: () => void;
}

export function GlassCard({
  children,
  className,
  hover = false,
  animate = false,
  onClick,
}: GlassCardProps) {
  return (
    <motion.div
      initial={animate ? { opacity: 0, y: 10 } : false}
      animate={animate ? { opacity: 1, y: 0 } : undefined}
      transition={animate ? { duration: 0.38, ease: [0.25, 0.1, 0.25, 1] } : undefined}
      onClick={onClick}
      className={cn(
        "glass-panel p-5",
        hover && "cursor-pointer",
        className
      )}
      style={{ willChange: hover ? "transform" : undefined }}
      onMouseOver={hover ? (e) => {
        const el = e.currentTarget as HTMLElement;
        el.style.backgroundColor = "var(--card-hover-bg)";
        el.style.transform = "translateY(-2px)";
        el.style.boxShadow = "var(--elevation-md)";
        el.style.borderColor = "var(--border-default)";
      } : undefined}
      onMouseOut={hover ? (e) => {
        const el = e.currentTarget as HTMLElement;
        el.style.backgroundColor = "";
        el.style.transform = "";
        el.style.boxShadow = "";
        el.style.borderColor = "";
      } : undefined}
    >
      {children}
    </motion.div>
  );
}
