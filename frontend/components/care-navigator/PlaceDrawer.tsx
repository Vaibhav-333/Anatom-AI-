"use client";

import { useEffect, useState } from "react";
import {
  X, Phone, Navigation, Star, Globe, Clock, MapPin,
  MessageSquare, Loader2, Users, Building2,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import type { NearbyPlace } from "./MapView";

// ── Types ──────────────────────────────────────────────────────────────────

interface PlaceDetails {
  place_id: string;
  formatted_address?: string | null;
  formatted_phone_number?: string | null;
  opening_hours?: {
    open_now?: boolean | null;
    weekday_text?: string[];
  } | null;
  rating?: number | null;
  user_ratings_total?: number | null;
  reviews?: Array<{
    author_name: string;
    rating: number | null;
    text: string;
    relative_time_description: string;
  }> | null;
  website?: string | null;
}

export interface PlaceDrawerProps {
  place: NearbyPlace | null;
  onClose: () => void;
  userLat: number;
  userLng: number;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function StarRow({ rating, size = "md" }: { rating: number; size?: "sm" | "md" }) {
  const cls = size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5";
  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          className={cn(
            cls,
            i < Math.floor(rating)
              ? "fill-amber-400 text-amber-400"
              : rating - Math.floor(rating) >= 0.5 && i === Math.floor(rating)
              ? "fill-amber-400/50 text-amber-400"
              : "fill-transparent text-slate-600"
          )}
        />
      ))}
    </div>
  );
}

// ── InfoRow ────────────────────────────────────────────────────────────────

function InfoRow({
  icon,
  label,
  children,
  iconColor = "text-slate-400",
  iconBg = "bg-navy-600/60",
}: {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
  iconColor?: string;
  iconBg?: string;
}) {
  return (
    <div className="flex items-start gap-3 p-3.5 rounded-xl bg-navy-700/40 border border-glass-border">
      <div
        className={cn(
          "w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border border-glass-border",
          iconBg
        )}
      >
        <span className={iconColor}>{icon}</span>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5 font-medium">
          {label}
        </p>
        {children}
      </div>
    </div>
  );
}

// ── Component ──────────────────────────────────────────────────────────────

export function PlaceDrawer({ place, onClose, userLat, userLng }: PlaceDrawerProps) {
  const [details, setDetails] = useState<PlaceDetails | null>(null);
  const [fetching, setFetching] = useState(false);

  useEffect(() => {
    if (!place) {
      setDetails(null);
      return;
    }
    setFetching(true);
    setDetails(null);
    fetch(`/api/get-place-details/${encodeURIComponent(place.place_id)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d: PlaceDetails | null) => setDetails(d))
      .catch(() => setDetails(null))
      .finally(() => setFetching(false));
  }, [place?.place_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const distKm = place ? haversineKm(userLat, userLng, place.lat, place.lng) : 0;
  const distLabel =
    distKm < 1 ? `${Math.round(distKm * 1000)} m away` : `${distKm.toFixed(1)} km away`;
  const directionsUrl = place
    ? `https://www.google.com/maps/dir/?api=1&destination=${place.lat},${place.lng}`
    : "#";

  const isOpen = place?.open_now ?? details?.opening_hours?.open_now ?? null;
  const phone = details?.formatted_phone_number ?? null;
  const cleanPhone = phone?.replace(/\s+/g, "") ?? "";

  return (
    <AnimatePresence>
      {place && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 backdrop-blur-[2px] z-40"
          />

          {/* Drawer panel */}
          <motion.aside
            key="drawer"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="fixed top-0 right-0 h-full w-full max-w-[400px] z-50 flex flex-col"
            style={{
              background: "linear-gradient(180deg, #0a0e1a 0%, #06080f 100%)",
              borderLeft: "1px solid rgba(0, 212, 255, 0.12)",
              boxShadow: "-8px 0 40px rgba(0,0,0,0.6), -1px 0 0 rgba(0,212,255,0.08)",
            }}
          >
            {/* ── Header ── */}
            <div
              className="shrink-0 pt-5 pb-4 px-5"
              style={{
                background: "linear-gradient(180deg, rgba(0,212,255,0.06) 0%, transparent 100%)",
                borderBottom: "1px solid rgba(0, 212, 255, 0.1)",
              }}
            >
              {/* Close + icon row */}
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-cyan/10 border border-cyan/20 flex items-center justify-center shrink-0">
                  <Building2 className="w-5 h-5 text-cyan" />
                </div>
                <button
                  onClick={onClose}
                  className="w-8 h-8 rounded-lg bg-navy-700/60 border border-glass-border flex items-center justify-center text-slate-400 hover:text-white hover:border-slate-500 transition-all shrink-0"
                  aria-label="Close"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Name */}
              <h2 className="text-[15px] font-bold text-white leading-snug mb-1.5">
                {place.name}
              </h2>

              {/* Vicinity */}
              {place.vicinity && (
                <div className="flex items-center gap-1.5 mb-2">
                  <MapPin className="w-3 h-3 text-slate-500 shrink-0" />
                  <p className="text-xs text-slate-400 leading-relaxed">{place.vicinity}</p>
                </div>
              )}

              {/* Pills row */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-cyan/10 border border-cyan/20 text-cyan text-[11px] font-semibold font-mono">
                  {distLabel}
                </span>
                {isOpen != null && (
                  <span
                    className={cn(
                      "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold border",
                      isOpen
                        ? "bg-emerald-500/10 border-emerald-500/25 text-emerald-400"
                        : "bg-red-500/10 border-red-500/25 text-red-400"
                    )}
                  >
                    <span
                      className={cn(
                        "w-1.5 h-1.5 rounded-full",
                        isOpen ? "bg-emerald-400 animate-pulse" : "bg-red-400"
                      )}
                    />
                    {isOpen ? "Open Now" : "Closed"}
                  </span>
                )}
                {place.rating != null && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[11px] font-semibold">
                    <Star className="w-3 h-3 fill-amber-400" />
                    {place.rating.toFixed(1)}
                  </span>
                )}
              </div>
            </div>

            {/* ── Scrollable body ── */}
            <div className="flex-1 overflow-y-auto p-5 space-y-3">
              {/* Loading shimmer */}
              {fetching && (
                <div className="flex items-center gap-2.5 py-4 px-1 text-slate-500">
                  <Loader2 className="w-4 h-4 animate-spin text-cyan" />
                  <span className="text-sm text-slate-400">Loading details…</span>
                </div>
              )}

              {details && (
                <>
                  {/* Rating (from OSM — usually null, but shown if present) */}
                  {place.user_ratings_total != null && place.rating != null && (
                    <InfoRow
                      icon={<Star className="w-3.5 h-3.5" />}
                      label="Rating"
                      iconColor="text-amber-400"
                      iconBg="bg-amber-500/10"
                    >
                      <div className="flex items-center gap-2">
                        <StarRow rating={place.rating} />
                        <span className="text-sm font-bold text-amber-400">
                          {place.rating.toFixed(1)}
                        </span>
                        <span className="flex items-center gap-1 text-xs text-slate-500">
                          <Users className="w-3 h-3" />
                          {place.user_ratings_total > 999
                            ? `${(place.user_ratings_total / 1000).toFixed(1)}k`
                            : place.user_ratings_total}
                        </span>
                      </div>
                    </InfoRow>
                  )}

                  {/* Phone */}
                  {phone && (
                    <InfoRow
                      icon={<Phone className="w-3.5 h-3.5" />}
                      label="Phone"
                      iconColor="text-cyan"
                      iconBg="bg-cyan/10"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm text-slate-200 font-medium">{phone}</p>
                        <a
                          href={`tel:${cleanPhone}`}
                          className="text-xs font-semibold text-cyan hover:text-white transition-colors px-2 py-0.5 rounded-md bg-cyan/10 border border-cyan/20 hover:bg-cyan/20"
                        >
                          Call
                        </a>
                      </div>
                    </InfoRow>
                  )}

                  {/* Address */}
                  {details.formatted_address && (
                    <InfoRow
                      icon={<MapPin className="w-3.5 h-3.5" />}
                      label="Address"
                      iconColor="text-slate-400"
                      iconBg="bg-navy-600/50"
                    >
                      <p className="text-sm text-slate-300 leading-relaxed">
                        {details.formatted_address}
                      </p>
                    </InfoRow>
                  )}

                  {/* Opening hours */}
                  {(details.opening_hours?.weekday_text ?? []).length > 0 && (
                    <div className="p-3.5 rounded-xl bg-navy-700/40 border border-glass-border">
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-8 h-8 rounded-lg bg-navy-600/50 border border-glass-border flex items-center justify-center shrink-0">
                          <Clock className="w-3.5 h-3.5 text-slate-400" />
                        </div>
                        <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">
                          Opening Hours
                        </p>
                      </div>
                      <div className="space-y-2 pl-1">
                        {(details.opening_hours!.weekday_text ?? []).map((line, i) => {
                          const colonIdx = line.indexOf(": ");
                          const day = colonIdx > -1 ? line.slice(0, colonIdx) : line;
                          const hrs = colonIdx > -1 ? line.slice(colonIdx + 2) : "";
                          const isClosed = hrs.toLowerCase() === "closed";
                          return (
                            <div key={i} className="flex justify-between items-center gap-4 text-xs">
                              <span className="text-slate-400 shrink-0 font-medium">{day}</span>
                              <span
                                className={cn(
                                  "font-mono text-right",
                                  isClosed ? "text-red-400" : "text-slate-300"
                                )}
                              >
                                {hrs || line}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Website */}
                  {details.website && (
                    <a
                      href={details.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-3 p-3.5 rounded-xl bg-navy-700/40 border border-glass-border hover:border-cyan/30 transition-colors group"
                    >
                      <div className="w-8 h-8 rounded-lg bg-navy-600/50 border border-glass-border flex items-center justify-center shrink-0">
                        <Globe className="w-3.5 h-3.5 text-slate-400 group-hover:text-cyan transition-colors" />
                      </div>
                      <span className="text-sm text-slate-400 group-hover:text-cyan transition-colors truncate">
                        {details.website.replace(/^https?:\/\//, "").replace(/\/$/, "")}
                      </span>
                    </a>
                  )}

                  {/* Reviews */}
                  {(details.reviews ?? []).length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-3 px-1">
                        <MessageSquare className="w-3.5 h-3.5 text-slate-500" />
                        <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">
                          Recent Reviews
                        </p>
                      </div>
                      <div className="space-y-3">
                        {(details.reviews ?? []).map((review, i) => (
                          <div
                            key={i}
                            className="p-3.5 rounded-xl bg-navy-700/40 border border-glass-border space-y-2"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <p className="text-xs font-semibold text-slate-200 truncate">
                                {review.author_name}
                              </p>
                              <div className="flex items-center gap-2 shrink-0">
                                {review.rating != null && <StarRow rating={review.rating} size="sm" />}
                                <span className="text-[10px] text-slate-600">
                                  {review.relative_time_description}
                                </span>
                              </div>
                            </div>
                            <p className="text-xs text-slate-400 leading-relaxed line-clamp-3">
                              {review.text}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Empty state — when OSM has no extra details */}
                  {!phone && !details.formatted_address && !details.opening_hours && !details.website && !fetching && (
                    <div className="flex flex-col items-center justify-center py-8 text-center">
                      <div className="w-12 h-12 rounded-xl bg-navy-700/40 border border-glass-border flex items-center justify-center mb-3">
                        <Building2 className="w-5 h-5 text-slate-600" />
                      </div>
                      <p className="text-sm text-slate-500">No additional details available</p>
                      <p className="text-xs text-slate-600 mt-1">Use Navigate to get directions</p>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* ── Footer CTA ── */}
            <div
              className="p-4 shrink-0"
              style={{ borderTop: "1px solid rgba(0, 212, 255, 0.1)" }}
            >
              <div className={cn("grid gap-2.5", phone ? "grid-cols-2" : "grid-cols-1")}>
                {phone && (
                  <a
                    href={`tel:${cleanPhone}`}
                    className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-cyan/10 border border-cyan/25 text-cyan text-sm font-semibold hover:bg-cyan/20 active:scale-95 transition-all"
                  >
                    <Phone className="w-4 h-4" />
                    Call Now
                  </a>
                )}
                <a
                  href={directionsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-semibold active:scale-95 transition-all"
                  style={{
                    background: "linear-gradient(135deg, rgba(0,212,255,0.15) 0%, rgba(0,255,136,0.1) 100%)",
                    border: "1px solid rgba(0, 212, 255, 0.3)",
                    color: "#00D4FF",
                  }}
                >
                  <Navigation className="w-4 h-4" />
                  Navigate
                </a>
              </div>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
