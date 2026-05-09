"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useRef, useState } from "react";
import {
  LayoutDashboard,
  Upload,
  Box,
  FileText,
  User,
  History,
  Brain,
  Activity,
  ChevronRight,
  MapPin,
  Stethoscope,
  Thermometer,
  Pill,
  Download,
  Leaf,
  Apple,
  Dumbbell,
  Lightbulb,
  HeartPulse,
  Salad,
  Sun,
  Moon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useTheme } from "@/context/ThemeContext";

// ── Nav data with semantic icon colors ───────────────────────────────────────

const flatNavGroups = [
  {
    group: "Main",
    items: [
      { label: "Dashboard",      href: "/",             icon: LayoutDashboard, color: "#0A84FF" },
      { label: "Upload Report",  href: "/upload",       icon: Upload,          color: "#0A84FF" },
      { label: "3D Body Viewer", href: "/viewer",       icon: Box,             color: "#BF5AF2" },
    ],
  },
  {
    group: "Analysis",
    items: [
      { label: "Results",        href: "/results",        icon: FileText,    color: "#FF9F0A" },
      { label: "History",        href: "/history",        icon: History,     color: "var(--label-secondary)" },
      { label: "Care Navigator", href: "/care-navigator", icon: MapPin,      color: "#32D74B" },
    ],
  },
  {
    group: "CareConnect AI",
    items: [
      { label: "Find Doctors", href: "/care-connect/doctors", icon: Stethoscope, color: "#0A84FF" },
    ],
  },
];

const accountGroup = {
  group: "Account",
  items: [{ label: "Health Profile", href: "/profile", icon: User, color: "var(--label-secondary)" }],
};

const collapsibleGroups = [
  {
    key: "symptom-tracker",
    label: "Symptom Tracker",
    icon: HeartPulse,
    rootHref: "/health-tracker",
    accentColor: "#FF2D55",
    items: [
      { label: "Dashboard",   href: "/health-tracker",             icon: Activity,    color: "#FF2D55" },
      { label: "Symptoms",    href: "/health-tracker/symptoms",    icon: Thermometer, color: "#FF9F0A" },
      { label: "Medications", href: "/health-tracker/medications", icon: Pill,        color: "#32D74B" },
      { label: "AI Insights", href: "/health-tracker/insights",    icon: Brain,       color: "#BF5AF2" },
      { label: "Export",      href: "/health-tracker/export",      icon: Download,    color: "var(--label-secondary)" },
    ],
  },
  {
    key: "lifestyle-planner",
    label: "Lifestyle Planner",
    icon: Salad,
    rootHref: "/lifestyle-planner",
    accentColor: "#32D74B",
    items: [
      { label: "My Plan",         href: "/lifestyle-planner",                 icon: Leaf,      color: "#32D74B" },
      { label: "Diet",            href: "/lifestyle-planner/diet",            icon: Apple,     color: "#FF9F0A" },
      { label: "Exercise",        href: "/lifestyle-planner/exercise",        icon: Dumbbell,  color: "#FF453A" },
      { label: "Recommendations", href: "/lifestyle-planner/recommendations", icon: Lightbulb, color: "#0A84FF" },
    ],
  },
] as const;

// ── Animation variants ────────────────────────────────────────────────────────

const submenuVariants = {
  hidden:  { opacity: 0, height: 0 as number | "auto" },
  visible: { opacity: 1, height: "auto" as number | "auto" },
};
const itemVariants = {
  hidden:  { opacity: 0, x: -6 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.15 } },
};

// ── CollapsibleNavItem ────────────────────────────────────────────────────────

interface CollapsibleGroup {
  key: string;
  label: string;
  icon: React.ElementType;
  rootHref: string;
  accentColor: string;
  items: readonly { label: string; href: string; icon: React.ElementType; color: string }[];
}

function CollapsibleNavItem({ group, pathname }: { group: CollapsibleGroup; pathname: string }) {
  const isGroupActive = pathname.startsWith(group.rootHref);
  const [open, setOpen] = useState(isGroupActive);
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const Icon = group.icon;

  const handleMouseEnter = () => { if (hoverTimer.current) clearTimeout(hoverTimer.current); setOpen(true); };
  const handleMouseLeave = () => { if (isGroupActive) return; hoverTimer.current = setTimeout(() => setOpen(false), 120); };
  const handleClick = () => setOpen((p) => !p);

  return (
    <div className="mb-0.5" onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
      <button
        onClick={handleClick}
        className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-[13px] font-medium transition-all duration-200 select-none"
        style={
          isGroupActive
            ? { background: "var(--bg-active)", color: "var(--label-primary)" }
            : { color: "var(--label-secondary)" }
        }
        onMouseOver={(e) => { if (!isGroupActive) (e.currentTarget as HTMLElement).style.background = "var(--bg-hover)"; }}
        onMouseOut={(e) => { if (!isGroupActive) (e.currentTarget as HTMLElement).style.background = ""; }}
      >
        <Icon className="w-4 h-4 shrink-0" style={{ color: group.accentColor }} />
        <span className="flex-1 text-left">{group.label}</span>
        <motion.span animate={{ rotate: open ? 90 : 0 }} transition={{ duration: 0.2, ease: "easeInOut" }} className="inline-flex">
          <ChevronRight className="w-3 h-3" style={{ color: "var(--nav-group-label)" }} />
        </motion.span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div key="submenu" variants={submenuVariants} initial="hidden" animate="visible" exit="hidden" className="overflow-hidden">
            <div
              className="mt-0.5 ml-3 pl-3 space-y-0.5 border-l"
              style={{ borderColor: "var(--nav-item-border)" }}
            >
              {group.items.map((item) => {
                const isActive = item.href === group.rootHref
                  ? pathname === group.rootHref
                  : pathname.startsWith(item.href);
                const SubIcon = item.icon;
                return (
                  <motion.div key={item.href} variants={itemVariants}>
                    <Link href={item.href}>
                      <div
                        className={cn(
                          "flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[12px] font-medium transition-all duration-100"
                        )}
                        style={
                          isActive
                            ? { background: "var(--bg-active)", color: "var(--label-primary)" }
                            : { color: "var(--label-secondary)" }
                        }
                        onMouseOver={(e) => { if (!isActive) (e.currentTarget as HTMLElement).style.background = "var(--bg-hover)"; }}
                        onMouseOut={(e) => { if (!isActive) (e.currentTarget as HTMLElement).style.background = ""; }}
                      >
                        <SubIcon className="w-3.5 h-3.5 shrink-0" style={{ color: item.color }} />
                        <span>{item.label}</span>
                        {isActive && <ChevronRight className="w-2.5 h-2.5 ml-auto" style={{ color: "var(--nav-group-label)" }} />}
                      </div>
                    </Link>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── FlatNavItem ───────────────────────────────────────────────────────────────

function FlatNavItem({
  item,
  pathname,
}: {
  item: { label: string; href: string; icon: React.ElementType; color: string };
  pathname: string;
}) {
  const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
  const Icon = item.icon;

  return (
    <Link href={item.href}>
      <motion.div
        whileHover={{ x: 1.5 }}
        className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-[13px] font-medium transition-all duration-200"
        style={
          isActive
            ? { background: "var(--bg-active)", color: "var(--label-primary)" }
            : { color: "var(--label-secondary)" }
        }
        onMouseOver={(e) => { if (!isActive) (e.currentTarget as HTMLElement).style.background = "var(--bg-hover)"; }}
        onMouseOut={(e) => { if (!isActive) (e.currentTarget as HTMLElement).style.background = ""; }}
      >
        <Icon className="w-4 h-4 shrink-0" style={{ color: item.color }} />
        <span className="flex-1">{item.label}</span>
        {isActive && <ChevronRight className="w-3 h-3" style={{ color: "var(--nav-group-label)" }} />}
      </motion.div>
    </Link>
  );
}

// ── ThemeToggle ───────────────────────────────────────────────────────────────

function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const isDark = theme !== "light";

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className="flex items-center gap-2.5 w-full px-2 py-1.5 rounded-xl transition-all duration-200"
      style={{ color: "var(--label-secondary)" }}
      onMouseOver={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--bg-hover)"; }}
      onMouseOut={(e) => { (e.currentTarget as HTMLElement).style.background = ""; }}
    >
      {/* Pill track */}
      <div
        className="relative flex-shrink-0 w-[38px] h-[22px] rounded-full"
        style={{
          background: isDark ? "rgba(10,132,255,0.20)" : "rgba(10,132,255,0.15)",
          border: "1px solid rgba(10,132,255,0.30)",
          transition: "background 0.3s ease",
        }}
      >
        <motion.div
          className="absolute top-[3px] w-4 h-4 rounded-full flex items-center justify-center"
          animate={{ left: isDark ? "3px" : "17px" }}
          transition={{ type: "spring", stiffness: 500, damping: 35 }}
          style={{ background: "#0A84FF" }}
        >
          <AnimatePresence mode="wait" initial={false}>
            {isDark ? (
              <motion.span
                key="moon"
                initial={{ opacity: 0, rotate: -30 }}
                animate={{ opacity: 1, rotate: 0 }}
                exit={{ opacity: 0, rotate: 30 }}
                transition={{ duration: 0.15 }}
                className="flex items-center justify-center"
              >
                <Moon className="w-2.5 h-2.5 text-white" />
              </motion.span>
            ) : (
              <motion.span
                key="sun"
                initial={{ opacity: 0, rotate: 30 }}
                animate={{ opacity: 1, rotate: 0 }}
                exit={{ opacity: 0, rotate: -30 }}
                transition={{ duration: 0.15 }}
                className="flex items-center justify-center"
              >
                <Sun className="w-2.5 h-2.5 text-white" />
              </motion.span>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
      <span className="text-[12px] font-medium" style={{ color: "var(--label-tertiary)" }}>
        {isDark ? "Dark Mode" : "Light Mode"}
      </span>
    </button>
  );
}

// ── Sidebar ───────────────────────────────────────────────────────────────────

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-60 z-40 flex flex-col">
      {/* Background */}
      <div
        className="absolute inset-0"
        style={{
          background: "var(--bg-sidebar)",
          borderRight: "1px solid var(--border-default)",
          transition: "background 0.3s ease, border-color 0.3s ease",
        }}
      />

      <div className="relative z-10 flex flex-col h-full">
        {/* Logo */}
        <div
          className="px-5 py-5 shrink-0"
          style={{ borderBottom: "1px solid var(--border-subtle)" }}
        >
          <div className="flex items-center gap-3">
            <div
              className="w-8 h-8 rounded-[10px] flex items-center justify-center"
              style={{ background: "rgba(10,132,255,0.18)" }}
            >
              <Brain className="w-4 h-4" style={{ color: "#0A84FF" }} />
            </div>
            <div>
              <h1
                className="text-[16px] font-bold tracking-tight"
                style={{ color: "var(--label-primary)", letterSpacing: "-0.01em" }}
              >
                ANATOM<span style={{ color: "#0A84FF" }}>-AI</span>
              </h1>
              <p className="text-[10px] font-mono" style={{ color: "var(--label-tertiary)", marginTop: "-1px" }}>
                v1.0 Medical Intelligence
              </p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 overflow-y-auto space-y-5">
          {flatNavGroups.map((group) => (
            <div key={group.group}>
              <p
                className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest"
                style={{ color: "var(--nav-group-label)" }}
              >
                {group.group}
              </p>
              <div className="space-y-0.5">
                {group.items.map((item) => (
                  <FlatNavItem key={item.href} item={item} pathname={pathname} />
                ))}
              </div>
            </div>
          ))}

          {/* Divider */}
          <div className="px-2">
            <div className="h-px w-full" style={{ background: "var(--border-subtle)" }} />
          </div>

          {/* Health Modules */}
          <div>
            <p
              className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest"
              style={{ color: "var(--nav-group-label)" }}
            >
              Health Modules
            </p>
            <div className="space-y-0.5">
              {collapsibleGroups.map((group) => (
                <CollapsibleNavItem key={group.key} group={group} pathname={pathname} />
              ))}
            </div>
          </div>

          {/* Account */}
          <div>
            <p
              className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest"
              style={{ color: "var(--nav-group-label)" }}
            >
              {accountGroup.group}
            </p>
            <div className="space-y-0.5">
              {accountGroup.items.map((item) => (
                <FlatNavItem key={item.href} item={item} pathname={pathname} />
              ))}
            </div>
          </div>
        </nav>

        {/* Footer */}
        <div
          className="px-4 py-4 shrink-0 space-y-3"
          style={{ borderTop: "1px solid var(--border-subtle)" }}
        >
          <ThemeToggle />

          <div className="flex items-center justify-between">
            <StatusBadge status="online" label="API Connected" />
            <div className="flex items-center gap-1.5" style={{ color: "var(--nav-group-label)" }}>
              <Activity className="w-3 h-3" />
              <span className="font-mono text-[10px]">8000</span>
            </div>
          </div>
          <p className="text-[10px] font-mono" style={{ color: "var(--nav-group-label)" }}>
            Not medical advice
          </p>
        </div>
      </div>
    </aside>
  );
}
