"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ChevronLeft, Star, MapPin, Briefcase, GraduationCap,
  Languages, BadgeCheck, Calendar, Building2, Bookmark, BookmarkCheck,
  Video, Phone, MessageCircle,
} from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { careConnectApi, Doctor } from "@/lib/careConnectApi";
import { useCareConnectStore } from "@/lib/useCareConnectStore";
import { getLocalUserId } from "@/lib/utils";

const DAY_LABELS: Record<string, string> = {
  mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", fri: "Fri", sat: "Sat", sun: "Sun",
};
const MODE_ICON: Record<string, React.ElementType> = { online: Video, offline: Building2, both: Phone };

export default function DoctorProfilePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { savedDoctorIds, toggleSaveDoctor } = useCareConnectStore();
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    careConnectApi.getDoctor(id).then(setDoctor).catch(() => {}).finally(() => setLoading(false));
  }, [id]);

  const saved = savedDoctorIds.has(id);

  const handleSave = async () => {
    if (saving) return;
    setSaving(true);
    const userId = getLocalUserId();
    if (saved) {
      await careConnectApi.unsaveDoctor(userId, id).catch(() => {});
    } else {
      await careConnectApi.saveDoctor(userId, id).catch(() => {});
    }
    toggleSaveDoctor(id);
    setSaving(false);
  };

  if (loading) return (
    <div className="space-y-4 max-w-2xl mx-auto">
      {[1, 2, 3].map((i) => <div key={i} className="h-28 rounded-2xl bg-navy-800/40 border border-glass-border animate-pulse" />)}
    </div>
  );

  if (!doctor) return (
    <GlassCard className="py-20 text-center max-w-2xl mx-auto">
      <p className="text-slate-400">Doctor not found</p>
    </GlassCard>
  );

  const ModeIcon = MODE_ICON[doctor.mode] ?? Building2;

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <button onClick={() => router.push("/care-connect/doctors")}
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-white transition-colors">
        <ChevronLeft className="w-4 h-4" /> All Doctors
      </button>

      {/* Profile header */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <GlassCard className="p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              {/* Avatar */}
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan/20 to-cyan/5 border border-cyan/20 flex items-center justify-center text-2xl font-bold text-cyan shrink-0">
                {doctor.name.split(" ").slice(1, 3).map((n) => n[0]).join("")}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-bold text-white">{doctor.name}</h1>
                  {doctor.verified && <BadgeCheck className="w-5 h-5 text-cyan" />}
                </div>
                <p className="text-cyan font-medium text-sm mt-0.5">{doctor.specialization}</p>
                <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
                  <span className="flex items-center gap-1">
                    <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
                    {doctor.rating.toFixed(1)} <span className="text-slate-600">({doctor.review_count} reviews)</span>
                  </span>
                  <span>•</span>
                  <span>{doctor.experience_years} yrs exp</span>
                </div>
              </div>
            </div>
            <button onClick={handleSave}
              className="p-2.5 rounded-xl border border-glass-border hover:border-cyan/30 text-slate-400 hover:text-cyan transition-all">
              {saved ? <BookmarkCheck className="w-5 h-5 text-cyan" /> : <Bookmark className="w-5 h-5" />}
            </button>
          </div>

          {/* Fee + mode */}
          <div className="grid grid-cols-3 gap-3 mt-5 pt-5 border-t border-glass-border/50">
            <div className="text-center">
              <p className="text-xs text-slate-500 mb-1">Consultation Fee</p>
              <p className="text-lg font-bold text-white">₹{doctor.consultation_fee.toLocaleString()}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-slate-500 mb-1">Mode</p>
              <div className="flex items-center justify-center gap-1.5">
                <ModeIcon className="w-4 h-4 text-cyan" />
                <p className="text-sm font-medium text-white capitalize">{doctor.mode === "both" ? "Online & Clinic" : doctor.mode}</p>
              </div>
            </div>
            <div className="text-center">
              <p className="text-xs text-slate-500 mb-1">Location</p>
              <p className="text-sm font-medium text-white">{doctor.city}</p>
            </div>
          </div>
        </GlassCard>
      </motion.div>

      {/* Hospital */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
        <GlassCard className="p-5">
          <div className="flex items-start gap-3">
            <Building2 className="w-5 h-5 text-slate-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs text-slate-500 mb-0.5">Hospital / Clinic</p>
              <p className="text-sm font-medium text-white">{doctor.hospital}</p>
              <div className="flex items-center gap-1 mt-1 text-xs text-slate-500">
                <MapPin className="w-3 h-3" /> {doctor.city}
              </div>
            </div>
          </div>
        </GlassCard>
      </motion.div>

      {/* About */}
      {doctor.about && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <GlassCard className="p-5">
            <h3 className="font-semibold text-white mb-3 text-sm">About</h3>
            <p className="text-sm text-slate-400 leading-relaxed">{doctor.about}</p>
          </GlassCard>
        </motion.div>
      )}

      {/* Qualifications & Languages */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <GlassCard className="p-5">
            <div className="flex items-center gap-2 mb-3">
              <GraduationCap className="w-4 h-4 text-cyan" />
              <h3 className="font-semibold text-white text-sm">Qualifications</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {doctor.degrees.map((d) => (
                <span key={d} className="text-xs px-2.5 py-1 rounded-full bg-cyan/10 border border-cyan/20 text-cyan">{d}</span>
              ))}
            </div>
          </GlassCard>
          <GlassCard className="p-5">
            <div className="flex items-center gap-2 mb-3">
              <Languages className="w-4 h-4 text-green" />
              <h3 className="font-semibold text-white text-sm">Languages</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {doctor.languages.map((l) => (
                <span key={l} className="text-xs px-2.5 py-1 rounded-full bg-green/10 border border-green/20 text-green">{l}</span>
              ))}
            </div>
          </GlassCard>
        </div>
      </motion.div>

      {/* Subspecialties */}
      {doctor.subspecialties.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <GlassCard className="p-5">
            <div className="flex items-center gap-2 mb-3">
              <Briefcase className="w-4 h-4 text-amber-400" />
              <h3 className="font-semibold text-white text-sm">Areas of Expertise</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {doctor.subspecialties.map((s) => (
                <span key={s} className="text-xs px-3 py-1.5 rounded-full border border-glass-border text-slate-400">{s}</span>
              ))}
            </div>
          </GlassCard>
        </motion.div>
      )}

      {/* Availability */}
      {Object.keys(doctor.availability).length > 0 && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
          <GlassCard className="p-5">
            <div className="flex items-center gap-2 mb-4">
              <Calendar className="w-4 h-4 text-purple-400" />
              <h3 className="font-semibold text-white text-sm">Availability</h3>
            </div>
            <div className="space-y-2">
              {Object.entries(doctor.availability).map(([day, slots]) => (
                <div key={day} className="flex items-center gap-3">
                  <span className="text-xs text-slate-500 w-8 font-mono uppercase">{DAY_LABELS[day] ?? day}</span>
                  <div className="flex flex-wrap gap-1.5">
                    {(slots as string[]).map((slot) => (
                      <span key={slot} className="text-xs px-2 py-0.5 rounded border border-glass-border text-slate-400 font-mono">{slot}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </motion.div>
      )}

      {/* Book CTA */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
        <div className="flex gap-3">
          <button className="flex-1 py-3 rounded-xl bg-cyan text-navy-900 font-bold text-sm hover:bg-cyan/90 transition-colors">
            Book Consultation
          </button>
          <button onClick={handleSave}
            className={`px-4 py-3 rounded-xl border font-medium text-sm transition-all ${saved ? "border-cyan/40 bg-cyan/10 text-cyan" : "border-glass-border text-slate-400 hover:border-slate-500"}`}>
            {saved ? "Saved" : "Save"}
          </button>
        </div>
        <p className="text-xs text-slate-600 text-center mt-2">
          Booking functionality coming soon. Contact the clinic directly for appointments.
        </p>
      </motion.div>
    </div>
  );
}
