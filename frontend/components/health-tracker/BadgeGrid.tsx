"use client";
import { motion } from "framer-motion";

const BADGE_META: Record<string, { label: string; icon: string; color: string }> = {
  streak_7:    { label: "7-Day Streak",   icon: "🔥", color: "#FFB800" },
  streak_30:   { label: "30-Day Streak",  icon: "⚡", color: "#00D4FF" },
  perfect_week:{ label: "Perfect Week",   icon: "💊", color: "#00FF88" },
  pain_free:   { label: "Pain Free",      icon: "✨", color: "#00FF88" },
  early_bird:  { label: "Great Sleep",    icon: "🌙", color: "#A78BFA" },
};

interface Props {
  badges: string[];
}

export default function BadgeGrid({ badges }: Props) {
  if (!badges?.length) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {(badges ?? []).map((key) => {
        const meta = BADGE_META[key] ?? { label: key, icon: "🏅", color: "#8899AA" };
        return (
          <motion.div
            key={key}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 300 }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium"
            style={{
              background: `${meta.color}18`,
              border: `1px solid ${meta.color}44`,
              color: meta.color,
            }}
          >
            <span>{meta.icon}</span>
            <span>{meta.label}</span>
          </motion.div>
        );
      })}
    </div>
  );
}
