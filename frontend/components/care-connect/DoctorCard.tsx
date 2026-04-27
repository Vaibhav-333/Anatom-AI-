"use client";

import { useState } from "react";
import Link from "next/link";
import { Star, MapPin, Clock, DollarSign, Bookmark, BookmarkCheck, BadgeCheck, Wifi, Building2 } from "lucide-react";
import { Doctor } from "@/lib/careConnectApi";
import { careConnectApi } from "@/lib/careConnectApi";
import { useCareConnectStore } from "@/lib/useCareConnectStore";
import { getLocalUserId } from "@/lib/utils";

const MODE_LABELS: Record<string, string> = { online: "Online", offline: "In-Clinic", both: "Online & Clinic" };
const MODE_COLORS: Record<string, string> = {
  online: "text-cyan border-cyan/30 bg-cyan/10",
  offline: "text-green border-green/30 bg-green/10",
  both: "text-amber-400 border-amber-400/30 bg-amber-400/10",
};

export function DoctorCard({ doctor }: { doctor: Doctor }) {
  const { savedDoctorIds, toggleSaveDoctor } = useCareConnectStore();
  const saved = savedDoctorIds.has(doctor.id);
  const [saving, setSaving] = useState(false);

  const handleSave = async (e: React.MouseEvent) => {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    const userId = getLocalUserId();
    if (saved) {
      await careConnectApi.unsaveDoctor(userId, doctor.id).catch(() => {});
    } else {
      await careConnectApi.saveDoctor(userId, doctor.id).catch(() => {});
    }
    toggleSaveDoctor(doctor.id);
    setSaving(false);
  };

  return (
    <Link href={`/care-connect/doctors/${doctor.id}`}>
      <div className="relative group bg-navy-800/60 border border-glass-border rounded-2xl p-5 hover:border-cyan/30 hover:bg-navy-700/60 transition-all duration-200 cursor-pointer">
        {/* Save button */}
        <button
          onClick={handleSave}
          className="absolute top-4 right-4 p-1.5 rounded-lg hover:bg-navy-600 transition-colors"
        >
          {saved
            ? <BookmarkCheck className="w-4 h-4 text-cyan" />
            : <Bookmark className="w-4 h-4 text-slate-500 group-hover:text-slate-300" />}
        </button>

        {/* Header */}
        <div className="pr-8">
          <div className="flex items-center gap-2 mb-0.5">
            <h3 className="font-semibold text-white text-sm">{doctor.name}</h3>
            {doctor.verified && <BadgeCheck className="w-4 h-4 text-cyan shrink-0" />}
          </div>
          <p className="text-xs text-cyan font-medium">{doctor.specialization}</p>
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-3 mt-3 text-xs text-slate-400">
          <span className="flex items-center gap-1">
            <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
            {doctor.rating.toFixed(1)}
            <span className="text-slate-600">({doctor.review_count})</span>
          </span>
          <span className="text-slate-600">•</span>
          <span>{doctor.experience_years} yrs exp</span>
        </div>

        {/* Hospital */}
        <div className="flex items-start gap-1.5 mt-2 text-xs text-slate-500">
          <Building2 className="w-3 h-3 mt-0.5 shrink-0" />
          <span className="line-clamp-1">{doctor.hospital}</span>
        </div>
        <div className="flex items-center gap-1.5 mt-1 text-xs text-slate-500">
          <MapPin className="w-3 h-3 shrink-0" />
          <span>{doctor.city}</span>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between mt-4 pt-3 border-t border-glass-border/50">
          <span className="text-sm font-bold text-white">₹{doctor.consultation_fee.toLocaleString()}</span>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${MODE_COLORS[doctor.mode] || MODE_COLORS.both}`}>
            {MODE_LABELS[doctor.mode] || doctor.mode}
          </span>
        </div>
      </div>
    </Link>
  );
}
