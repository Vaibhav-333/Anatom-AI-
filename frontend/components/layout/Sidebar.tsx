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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/StatusBadge";

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
      { label: "History",        href: "/history",        icon: History,     color: "#8E8E93" },
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
  items: [{ label: "Health Profile", href: "/profile", icon: User, color: "#8E8E93" }],
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
      { label: "Export",      href: "/health-tracker/export",      icon: Download,    color: "#8E8E93" },
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
        className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-[13px] font-medium transition-all duration-200 select-none hover:bg-white/[0.05]"
        style={
          isGroupActive
            ? { background: "rgba(255,255,255,0.08)", color: "#FFFFFF" }
            : { color: "#8E8E93" }
        }
      >
        <Icon className="w-4 h-4 shrink-0" style={{ color: group.accentColor }} />
        <span className="flex-1 text-left">{group.label}</span>
        <motion.span animate={{ rotate: open ? 90 : 0 }} transition={{ duration: 0.2, ease: "easeInOut" }} className="inline-flex">
          <ChevronRight className="w-3 h-3" style={{ color: "#48484A" }} />
        </motion.span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div key="submenu" variants={submenuVariants} initial="hidden" animate="visible" exit="hidden" className="overflow-hidden">
            <div
              className="mt-0.5 ml-3 pl-3 space-y-0.5 border-l"
              style={{ borderColor: "rgba(84,84,88,0.22)" }}
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
                          "flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[12px] font-medium transition-all duration-100",
                          isActive ? "" : "hover:bg-white/[0.04]"
                        )}
                        style={
                          isActive
                            ? { background: "rgba(255,255,255,0.07)", color: "#FFFFFF" }
                            : { color: "#8E8E93" }
                        }
                      >
                        <SubIcon className="w-3.5 h-3.5 shrink-0" style={{ color: item.color }} />
                        <span>{item.label}</span>
                        {isActive && <ChevronRight className="w-2.5 h-2.5 ml-auto" style={{ color: "#48484A" }} />}
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
        className={cn(
          "flex items-center gap-2.5 px-3 py-2 rounded-xl text-[13px] font-medium transition-all duration-200",
          isActive ? "" : "hover:bg-white/[0.05]"
        )}
        style={
          isActive
            ? { background: "rgba(255,255,255,0.08)", color: "#FFFFFF" }
            : { color: "#8E8E93" }
        }
      >
        <Icon className="w-4 h-4 shrink-0" style={{ color: item.color }} />
        <span className="flex-1">{item.label}</span>
        {isActive && <ChevronRight className="w-3 h-3" style={{ color: "#48484A" }} />}
      </motion.div>
    </Link>
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
          background: "#0B0B0F",
          borderRight: "1px solid rgba(84,84,88,0.28)",
        }}
      />

      <div className="relative z-10 flex flex-col h-full">
        {/* Logo */}
        <div
          className="px-5 py-5 shrink-0"
          style={{ borderBottom: "1px solid rgba(84,84,88,0.20)" }}
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
                style={{ color: "#fff", letterSpacing: "-0.01em" }}
              >
                ANATOM<span style={{ color: "#0A84FF" }}>-AI</span>
              </h1>
              <p className="text-[10px] font-mono" style={{ color: "#636366", marginTop: "-1px" }}>
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
                style={{ color: "#48484A" }}
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
            <div className="h-px w-full" style={{ background: "rgba(84,84,88,0.20)" }} />
          </div>

          {/* Health Modules */}
          <div>
            <p
              className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest"
              style={{ color: "#48484A" }}
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
              style={{ color: "#48484A" }}
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
          className="px-5 py-4 shrink-0"
          style={{ borderTop: "1px solid rgba(84,84,88,0.20)" }}
        >
          <div className="flex items-center justify-between">
            <StatusBadge status="online" label="API Connected" />
            <div className="flex items-center gap-1.5" style={{ color: "#48484A" }}>
              <Activity className="w-3 h-3" />
              <span className="font-mono text-[10px]">8000</span>
            </div>
          </div>
          <p className="mt-2 text-[10px] font-mono" style={{ color: "#48484A" }}>
            Not medical advice
          </p>
        </div>
      </div>
    </aside>
  );
}
