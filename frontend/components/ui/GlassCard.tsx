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
        hover && [
          "cursor-pointer",
          "transition-all duration-200",
          "hover:bg-[#2C2C2E]",
        ],
        className
      )}
    >
      {children}
    </motion.div>
  );
}
