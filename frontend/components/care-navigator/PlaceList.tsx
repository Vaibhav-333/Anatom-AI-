"use client";

import { MapPin, Star, Clock, Navigation, Users, ChevronRight, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { NearbyPlace } from "./MapView";

interface PlaceListProps {
  places: NearbyPlace[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  /** Called when a card is clicked — opens the detail drawer */
  onOpenDrawer: (place: NearbyPlace) => void;
  userLat: number;
  userLng: number;
  loading: boolean;
  /** place_id of the automatically computed "best match" */
  bestMatchId: string | null;
}

function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
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

function RatingStars({ rating }: { rating: number }) {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          className={cn(
            "w-3 h-3",
            i < full
              ? "fill-amber-400 text-amber-400"
              : half && i === full
              ? "fill-amber-400/50 text-amber-400"
              : "fill-transparent text-slate-600"
          )}
        />
      ))}
    </div>
  );
}

export function PlaceList({
  places,
  selectedId,
  onSelect,
  onOpenDrawer,
  userLat,
  userLng,
  loading,
  bestMatchId,
}: PlaceListProps) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-slate-500 space-y-3">
        <div className="relative">
          <div className="w-8 h-8 border-2 border-cyan/20 rounded-full" />
          <div className="absolute inset-0 w-8 h-8 border-2 border-t-cyan rounded-full animate-spin" />
        </div>
        <div className="text-center">
          <p className="text-sm font-medium text-slate-400">Finding the best care options near you…</p>
          <p className="text-xs text-slate-600 mt-1">Searching Google Places</p>
        </div>
      </div>
    );
  }

  if (!places.length) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-slate-500 space-y-3">
        <div className="w-12 h-12 rounded-2xl bg-slate-800/60 border border-glass-border flex items-center justify-center">
          <MapPin className="w-5 h-5 text-slate-600" />
        </div>
        <div className="text-center">
          <p className="text-sm font-medium text-slate-400">No relevant specialists found nearby</p>
          <p className="text-xs text-slate-600 mt-1">Try increasing the search radius or adjusting filters</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2 overflow-y-auto max-h-[500px] pr-1 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-slate-700">
      {places.map((place, i) => {
        const isSelected = place.place_id === selectedId;
        const isBest = place.place_id === bestMatchId;
        const distKm = haversineKm(userLat, userLng, place.lat, place.lng);
        const distLabel =
          distKm < 1 ? `${Math.round(distKm * 1000)} m` : `${distKm.toFixed(1)} km`;
        const directionsUrl = `https://www.google.com/maps/dir/?api=1&destination=${place.lat},${place.lng}&destination_place_id=${place.place_id}`;

        return (
          <motion.div
            key={place.place_id}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04, duration: 0.25 }}
            onClick={() => {
              onSelect(place.place_id);
              onOpenDrawer(place);
            }}
            className={cn(
              "p-3.5 rounded-xl border cursor-pointer transition-all duration-150 group relative",
              isSelected
                ? "bg-cyan/8 border-cyan/30 shadow-[0_0_16px_rgba(0,212,255,0.12)]"
                : "bg-navy-800/50 border-glass-border hover:bg-navy-700/50 hover:border-cyan/20"
            )}
          >
            {/* Best match badge */}
            {isBest && (
              <div className="absolute -top-2.5 left-3 flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-400 text-[10px] font-bold uppercase tracking-wider">
                <Sparkles className="w-2.5 h-2.5" />
                Best Match
              </div>
            )}

            {/* Name + distance */}
            <div className="flex items-start justify-between gap-2 mb-1.5" style={{ marginTop: isBest ? "6px" : 0 }}>
              <p
                className={cn(
                  "text-sm font-semibold leading-snug flex-1",
                  isSelected ? "text-cyan" : "text-white group-hover:text-cyan/90 transition-colors"
                )}
              >
                {place.name}
              </p>
              <div className="flex items-center gap-1 shrink-0">
                <span className="text-xs font-mono text-slate-500">{distLabel}</span>
                <ChevronRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-cyan/60 transition-colors" />
              </div>
            </div>

            {/* Address */}
            <div className="flex items-center gap-1.5 mb-2.5">
              <MapPin className="w-3 h-3 text-slate-500 shrink-0" />
              <p className="text-xs text-slate-400 truncate">{place.vicinity}</p>
            </div>

            {/* Rating + open status */}
            <div className="flex items-center gap-3 mb-3">
              {place.rating != null && (
                <div className="flex items-center gap-1.5">
                  <RatingStars rating={place.rating} />
                  <span className="text-xs text-slate-400 font-mono">{place.rating.toFixed(1)}</span>
                  {place.user_ratings_total != null && (
                    <span className="flex items-center gap-0.5 text-xs text-slate-600">
                      <Users className="w-2.5 h-2.5" />
                      {place.user_ratings_total > 999
                        ? `${(place.user_ratings_total / 1000).toFixed(1)}k`
                        : place.user_ratings_total}
                    </span>
                  )}
                </div>
              )}

              {place.open_now != null && (
                <div className="flex items-center gap-1">
                  <span
                    className={cn(
                      "w-1.5 h-1.5 rounded-full",
                      place.open_now ? "bg-emerald-400 animate-pulse" : "bg-red-400"
                    )}
                  />
                  <Clock className="w-3 h-3 text-slate-500" />
                  <span
                    className={cn(
                      "text-xs font-medium",
                      place.open_now ? "text-emerald-400" : "text-red-400"
                    )}
                  >
                    {place.open_now ? "Open" : "Closed"}
                  </span>
                </div>
              )}
            </div>

            {/* Bottom action row */}
            <div className="flex items-center justify-between">
              <a
                href={directionsUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-cyan/25 text-cyan hover:bg-cyan/10 hover:border-cyan/50 transition-all"
              >
                <Navigation className="w-3 h-3" />
                Navigate
              </a>
              <span className="text-[10px] text-slate-600 group-hover:text-slate-400 transition-colors">
                Tap for details →
              </span>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
