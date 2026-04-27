"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Search, SlidersHorizontal, Users, Bookmark } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageHero } from "@/components/ui/PageHero";
import { GlassCard } from "@/components/ui/GlassCard";
import { DoctorCard } from "@/components/care-connect/DoctorCard";
import { careConnectApi, Doctor } from "@/lib/careConnectApi";
import { useCareConnectStore } from "@/lib/useCareConnectStore";
import { getLocalUserId } from "@/lib/utils";
import { PAGE_IMAGES } from "@/lib/pageImages";

const SPECIALIZATIONS = [
  "All", "General Physician", "Neurologist", "Neurosurgeon", "Cardiologist",
  "Orthopedist", "Dermatologist", "Gastroenterologist", "Psychiatrist",
  "Pulmonologist", "Endocrinologist", "Ophthalmologist", "ENT Specialist",
  "Rheumatologist", "Nephrologist", "Urologist",
];

const MODE_OPTIONS = [
  { label: "All", value: "all" },
  { label: "Online", value: "online" },
  { label: "In-Clinic", value: "offline" },
];

export default function DoctorsPage() {
  const searchParams = useSearchParams();
  const tab = searchParams.get("tab") ?? "all";

  const { savedDoctorIds, setSavedDoctorIds } = useCareConnectStore();
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [saved, setSaved] = useState<Doctor[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"all" | "saved">(tab as "all" | "saved");

  // Filters
  const [spec, setSpec] = useState("All");
  const [mode, setMode] = useState("all");
  const [maxFee, setMaxFee] = useState(5000);
  const [search, setSearch] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    const userId = getLocalUserId();
    Promise.all([
      careConnectApi.listDoctors(),
      careConnectApi.getSavedDoctors(userId),
    ]).then(([all, savedDocs]) => {
      setDoctors(all);
      setSaved(savedDocs);
      setSavedDoctorIds(savedDocs.map((d) => d.id));
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const filtered = (activeTab === "saved" ? saved : doctors).filter((d) => {
    if (spec !== "All" && d.specialization !== spec) return false;
    if (mode !== "all" && d.mode !== mode && d.mode !== "both") return false;
    if (d.consultation_fee > maxFee) return false;
    if (search && !d.name.toLowerCase().includes(search.toLowerCase()) &&
      !d.specialization.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      <PageHero src={PAGE_IMAGES.doctors} opacity={40} objectPosition="center 25%">
        <PageHeader title="Find Doctors" subtitle="Browse verified specialists and find the right doctor for your condition" />
      </PageHero>

      {/* Tabs */}
      <div
        className="flex items-center gap-1 p-1 rounded-xl w-fit"
        style={{ background: "rgba(28,28,30,0.80)", border: "1px solid rgba(84,84,88,0.35)" }}
      >
        {[{ label: "All Doctors", value: "all", icon: Users }, { label: "Saved", value: "saved", icon: Bookmark }].map((t) => {
          const Icon = t.icon;
          const isActive = activeTab === t.value;
          return (
            <button
              key={t.value}
              onClick={() => setActiveTab(t.value as "all" | "saved")}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-[13px] font-medium transition-all"
              style={
                isActive
                  ? { background: "#0A84FF", color: "#fff" }
                  : { color: "#8E8E93" }
              }
            >
              <Icon className="w-3.5 h-3.5" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Trusted Medical Network banner — pure dark card, no repeated image */}
      <div
        className="rounded-2xl px-6 py-5 flex items-center justify-between"
        style={{
          background: "#1C1C1E",
          border: "1px solid rgba(84,84,88,0.28)",
          boxShadow: "0 2px 12px rgba(0,0,0,0.40)",
        }}
      >
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1" style={{ color: "#0A84FF" }}>CareConnect AI</p>
          <h3 className="text-white font-bold text-[17px] tracking-tight">Trusted Medical Network</h3>
          <p className="text-[13px] mt-0.5" style={{ color: "#8E8E93" }}>
            Verified specialists across all major disciplines, available online &amp; in-clinic.
          </p>
        </div>
        <div className="flex gap-8 shrink-0">
          <div className="text-center">
            <p className="text-[22px] font-bold font-mono" style={{ color: "#0A84FF" }}>500+</p>
            <p className="text-[11px]" style={{ color: "#636366" }}>Doctors</p>
          </div>
          <div className="text-center">
            <p className="text-[22px] font-bold font-mono" style={{ color: "#FF9F0A" }}>4.8★</p>
            <p className="text-[11px]" style={{ color: "#636366" }}>Avg Rating</p>
          </div>
          <div className="text-center">
            <p className="text-[22px] font-bold font-mono" style={{ color: "#32D74B" }}>15+</p>
            <p className="text-[11px]" style={{ color: "#636366" }}>Specialties</p>
          </div>
        </div>
      </div>

      {/* Search + filter bar */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none" style={{ color: "#48484A" }} />
          <input value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or specialization..."
            className="auth-input pl-9"
          />
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-[13px] font-medium transition-all"
          style={
            showFilters
              ? { background: "rgba(10,132,255,0.14)", color: "#0A84FF", border: "1px solid rgba(10,132,255,0.25)" }
              : { background: "rgba(255,255,255,0.06)", color: "#8E8E93", border: "1px solid rgba(84,84,88,0.35)" }
          }
        >
          <SlidersHorizontal className="w-4 h-4" /> Filters
        </button>
      </div>

      {showFilters && (
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
          <GlassCard className="p-5 space-y-4">
            <div>
              <p className="text-xs text-slate-500 mb-2">Specialization</p>
              <div className="flex flex-wrap gap-2">
                {SPECIALIZATIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => setSpec(s)}
                    className="text-[12px] px-3 py-1.5 rounded-full transition-all"
                    style={
                      spec === s
                        ? { background: "rgba(10,132,255,0.14)", border: "1px solid rgba(10,132,255,0.30)", color: "#0A84FF" }
                        : { background: "rgba(255,255,255,0.04)", border: "1px solid rgba(84,84,88,0.35)", color: "#8E8E93" }
                    }
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-slate-500 mb-2">Consultation Mode</p>
                <div className="flex gap-2">
                  {MODE_OPTIONS.map((m) => (
                    <button
                      key={m.value}
                      onClick={() => setMode(m.value)}
                      className="flex-1 text-[12px] py-2 rounded-xl transition-all"
                      style={
                        mode === m.value
                          ? { background: "rgba(10,132,255,0.14)", border: "1px solid rgba(10,132,255,0.30)", color: "#0A84FF" }
                          : { background: "rgba(255,255,255,0.04)", border: "1px solid rgba(84,84,88,0.35)", color: "#8E8E93" }
                      }
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs text-slate-500 mb-2">Max Fee: ₹{maxFee.toLocaleString()}</p>
                <input type="range" min={200} max={5000} step={100} value={maxFee}
                  onChange={(e) => setMaxFee(parseInt(e.target.value))}
                  className="w-full" style={{ accentColor: "#0A84FF" }} />
              </div>
            </div>
          </GlassCard>
        </motion.div>
      )}

      {/* Results count */}
      <p className="text-sm text-slate-500">
        {loading ? "Loading..." : `${filtered.length} doctor${filtered.length !== 1 ? "s" : ""} found`}
      </p>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-52 rounded-2xl bg-navy-800/40 border border-glass-border animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <GlassCard className="py-16 text-center">
          <Users className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400 font-medium">{activeTab === "saved" ? "No saved doctors yet" : "No doctors match your filters"}</p>
          <p className="text-slate-600 text-sm mt-1">{activeTab === "saved" ? "Bookmark doctors from the listing to save them here" : "Try adjusting your search or filters"}</p>
        </GlassCard>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((doc, i) => (
            <motion.div key={doc.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}>
              <DoctorCard doctor={doc} />
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
