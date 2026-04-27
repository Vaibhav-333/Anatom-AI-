"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import {
  MapPin, Search, Locate, Stethoscope, AlertCircle,
  Loader2, X, Brain, Sparkles, ChevronRight,
} from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageHero } from "@/components/ui/PageHero";
import { PAGE_IMAGES } from "@/lib/pageImages";
import { GlassCard } from "@/components/ui/GlassCard";
import { NeonButton } from "@/components/ui/NeonButton";
import { AlertBox } from "@/components/ui/AlertBox";
import { PlaceList } from "@/components/care-navigator/PlaceList";
import { PlaceDrawer } from "@/components/care-navigator/PlaceDrawer";
import { Filters } from "@/components/care-navigator/Filters";
import { useCareNavigatorStore } from "@/lib/careNavigatorZustand";
import { loadSpecialistSearch, clearSpecialistSearch } from "@/lib/careNavigatorStore";
import type { SearchFilters, SearchType } from "@/components/care-navigator/Filters";
import type { NearbyPlace } from "@/components/care-navigator/MapView";
import type { SpecialistRecommendation } from "@/lib/specialistMap";

// Google Maps uses browser APIs — SSR must be disabled
const MapView = dynamic(
  () => import("@/components/care-navigator/MapView").then((m) => m.MapView),
  { ssr: false, loading: () => <MapSkeleton /> }
);

function MapSkeleton() {
  return (
    <div className="w-full h-full rounded-xl bg-navy-800/60 border border-glass-border flex items-center justify-center">
      <div className="flex flex-col items-center gap-3 text-slate-500">
        <Loader2 className="w-6 h-6 text-cyan/40 animate-spin" />
        <p className="text-xs">Loading map…</p>
      </div>
    </div>
  );
}

// ── Scoring for "Best Match" ─────────────────────────────────────────────

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

function computeBestMatchId(
  places: NearbyPlace[],
  userLat: number,
  userLng: number,
  keyword: string
): string | null {
  if (!places.length) return null;
  const kw = keyword.toLowerCase();
  let bestId = "";
  let bestScore = -Infinity;
  for (const p of places) {
    const dist = haversineKm(userLat, userLng, p.lat, p.lng);
    const ratingScore = (p.rating ?? 0) * 18;          // 0-90 pts
    const distScore = Math.max(0, 60 - dist * 8);      // closer = more pts
    const openBonus = p.open_now === true ? 8 : 0;
    const kwBonus =
      kw &&
      (p.name.toLowerCase().includes(kw) ||
        p.types.some((t) => t.replace(/_/g, " ").includes(kw)))
        ? 12
        : 0;
    const score = ratingScore + distScore + openBonus + kwBonus;
    if (score > bestScore) {
      bestScore = score;
      bestId = p.place_id;
    }
  }
  return bestId || null;
}

const DEFAULT_COORDS = { lat: 28.6139, lng: 77.209 }; // New Delhi fallback

// ── Page ─────────────────────────────────────────────────────────────────

export default function CareNavigatorPage() {
  // ── Location state
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [locationDenied, setLocationDenied] = useState(false);
  const [manualAddress, setManualAddress] = useState("");
  const [geocoding, setGeocoding] = useState(false);

  // ── Search state
  const [searchType, setSearchType] = useState<SearchType>("hospital");
  const [customKeyword, setCustomKeyword] = useState("");
  const [filters, setFilters] = useState<SearchFilters>({ radius: 5000, minRating: 0, openNow: false });
  const [rawPlaces, setRawPlaces] = useState<NearbyPlace[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // ── Drawer
  const [drawerPlace, setDrawerPlace] = useState<NearbyPlace | null>(null);

  // ── Specialist context (sessionStorage fallback + Zustand primary)
  const [specialistCtx, setSpecialistCtx] = useState<{ specialist: string; condition: string } | null>(null);
  const zustandRecs = useCareNavigatorStore((s) => s.recommendedSpecialists);
  const clearZustandAnalysis = useCareNavigatorStore((s) => s.clearAnalysis);

  // Merge: Zustand (multi-condition) wins over sessionStorage single-item
  const allRecommendations: SpecialistRecommendation[] = useMemo(() => {
    if (zustandRecs.length > 0) return zustandRecs;
    if (specialistCtx) return [{ disease: specialistCtx.condition, specialist: specialistCtx.specialist }];
    return [];
  }, [zustandRecs, specialistCtx]);

  // ── On mount: read sessionStorage + request geolocation
  useEffect(() => {
    const ctx = loadSpecialistSearch();
    if (ctx) {
      setSpecialistCtx(ctx);
      setCustomKeyword(ctx.specialist);
      clearSpecialistSearch();
    }
    if (!navigator.geolocation) { setLocationDenied(true); return; }
    navigator.geolocation.getCurrentPosition(
      (pos) => setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => setLocationDenied(true),
      { timeout: 8000, enableHighAccuracy: false }
    );
  }, []);

  // ── Auto-search when location / type / radius changes
  useEffect(() => {
    if (coords) runSearch(coords);
  }, [coords, searchType, filters.radius]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Core search handler
  const runSearch = useCallback(
    async (location: { lat: number; lng: number }) => {
      setLoading(true);
      setSearchError(null);
      setSelectedId(null);
      try {
        const res = await fetch("/api/get-nearby-places", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            lat: location.lat,
            lng: location.lng,
            radius: filters.radius,
            type: searchType,
            keyword: customKeyword || undefined,
          }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail ?? "Search failed");
        }
        const data = await res.json();
        setRawPlaces(data.results ?? []);
      } catch (e: unknown) {
        setSearchError(e instanceof Error ? e.message : "An error occurred");
        setRawPlaces([]);
      } finally {
        setLoading(false);
      }
    },
    [filters.radius, searchType, customKeyword]
  );

  // ── One-click specialist search from AI recommendations
  const handleSpecialistSearch = useCallback(
    (specialist: string) => {
      setCustomKeyword(specialist);
      setSearchType("doctor");
      if (coords) {
        setLoading(true);
        setSearchError(null);
        setSelectedId(null);
        fetch("/api/get-nearby-places", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            lat: coords.lat, lng: coords.lng,
            radius: filters.radius, type: "doctor", keyword: specialist,
          }),
        })
          .then((r) => (r.ok ? r.json() : Promise.reject()))
          .then((d) => setRawPlaces(d.results ?? []))
          .catch(() => setSearchError("Search failed. Please try again."))
          .finally(() => setLoading(false));
      }
    },
    [coords, filters.radius]
  );

  // ── Manual address geocoding via Nominatim (OpenStreetMap, no API key)
  const geocodeAddress = useCallback(async () => {
    if (!manualAddress.trim()) return;
    setGeocoding(true);
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(manualAddress)}&format=json&limit=1`,
        { headers: { "User-Agent": "NeuroMapper/1.0" } }
      );
      const data = await res.json();
      if (data.length > 0) {
        setCoords({ lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon) });
        setLocationDenied(false);
      } else {
        setSearchError("Address not found. Please try a different search.");
      }
    } catch {
      setSearchError("Geocoding failed. Please try again.");
    } finally {
      setGeocoding(false);
    }
  }, [manualAddress]);

  // ── Client-side filtering
  const filteredPlaces = useMemo(
    () =>
      rawPlaces.filter((p) => {
        if (filters.minRating > 0 && (p.rating ?? 0) < filters.minRating) return false;
        if (filters.openNow && p.open_now === false) return false;
        return true;
      }),
    [rawPlaces, filters.minRating, filters.openNow]
  );

  // ── Best match
  const displayCoords = coords ?? DEFAULT_COORDS;
  const bestMatchId = useMemo(
    () => computeBestMatchId(filteredPlaces, displayCoords.lat, displayCoords.lng, customKeyword),
    [filteredPlaces, displayCoords, customKeyword]
  );

  const dismissRecommendations = () => {
    setSpecialistCtx(null);
    setCustomKeyword("");
    clearZustandAnalysis();
  };

  // ── Render ──────────────────────────────────────────────────────────────
  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-5"
      >
        <PageHero src={PAGE_IMAGES.careNavigator} opacity={38} objectPosition="center 40%">
          <PageHeader
            title="Care Navigator"
            subtitle="AI-powered specialist finder — locate the right care near you"
            icon={<MapPin className="w-5 h-5" />}
          />
        </PageHero>

        {/* ── AI Recommendations Section ─────────────────────────────── */}
        {allRecommendations.length > 0 && (
          <motion.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}>
            <GlassCard glow="cyan">
              <div className="flex items-start justify-between gap-4 mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-cyan/10 border border-cyan/30 flex items-center justify-center shrink-0">
                    <Brain className="w-4.5 h-4.5 text-cyan" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-cyan flex items-center gap-2">
                      <Sparkles className="w-3.5 h-3.5" />
                      Recommended for Your Condition
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Based on your latest AI report analysis
                    </p>
                  </div>
                </div>
                <button
                  onClick={dismissRecommendations}
                  className="text-slate-500 hover:text-slate-300 transition-colors shrink-0 mt-0.5"
                  aria-label="Dismiss"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className={`grid gap-3 ${allRecommendations.length > 1 ? "sm:grid-cols-2" : "grid-cols-1"}`}>
                {allRecommendations.map(({ disease, specialist }) => (
                  <div
                    key={disease}
                    className="flex items-center justify-between gap-3 p-3.5 rounded-xl bg-navy-800/70 border border-glass-border"
                  >
                    <div className="min-w-0">
                      <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Detected</p>
                      <p className="text-sm font-semibold text-white truncate">{disease}</p>
                      <div className="flex items-center gap-1.5 mt-1">
                        <Stethoscope className="w-3 h-3 text-cyan" />
                        <p className="text-xs text-cyan font-medium">{specialist}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleSpecialistSearch(specialist)}
                      disabled={!coords || loading}
                      className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-cyan/10 border border-cyan/30 text-cyan text-xs font-semibold hover:bg-cyan/20 disabled:opacity-40 disabled:cursor-not-allowed transition-all shrink-0"
                    >
                      Find
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </GlassCard>
          </motion.div>
        )}

        {/* ── Location denied — manual address ──────────────────────── */}
        {locationDenied && !coords && (
          <GlassCard>
            <div className="flex items-start gap-3 mb-4">
              <AlertCircle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-semibold text-amber-400">Location access denied</p>
                <p className="text-xs text-slate-400 mt-0.5">Enter your city or address to find nearby care</p>
              </div>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={manualAddress}
                onChange={(e) => setManualAddress(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && geocodeAddress()}
                placeholder="e.g. Connaught Place, New Delhi"
                className="flex-1 bg-navy-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan/40 focus:ring-1 focus:ring-cyan/20"
              />
              <NeonButton
                variant="cyan"
                size="sm"
                icon={geocoding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                onClick={geocodeAddress}
                disabled={geocoding || !manualAddress.trim()}
              >
                Search
              </NeonButton>
            </div>
          </GlassCard>
        )}

        {/* ── Filters + keyword search ───────────────────────────────── */}
        <GlassCard>
          <div className="space-y-3">
            <Filters
              searchType={searchType}
              onSearchTypeChange={(t) => {
                setSearchType(t);
                setCustomKeyword("");
                dismissRecommendations();
              }}
              filters={filters}
              onFiltersChange={(patch) => setFilters((prev) => ({ ...prev, ...patch }))}
              disabled={!coords || loading}
            />
            <div className="flex gap-2">
              <input
                type="text"
                value={customKeyword}
                onChange={(e) => setCustomKeyword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && coords && runSearch(coords)}
                placeholder="Search by keyword — Neurologist, Cardiologist…"
                className="flex-1 bg-navy-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan/40 focus:ring-1 focus:ring-cyan/20"
              />
              <NeonButton
                variant="cyan"
                size="sm"
                icon={
                  loading
                    ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    : coords
                    ? <Search className="w-3.5 h-3.5" />
                    : <Locate className="w-3.5 h-3.5" />
                }
                onClick={() => coords && runSearch(coords)}
                disabled={!coords || loading}
              >
                {loading ? "Searching…" : "Search"}
              </NeonButton>
            </div>
          </div>
        </GlassCard>

        {/* ── Error ─────────────────────────────────────────────────── */}
        {searchError && (
          <AlertBox variant="error" dismissible onDismiss={() => setSearchError(null)}>
            {searchError}
          </AlertBox>
        )}

        {/* ── Map + Results grid ─────────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 min-h-[520px]">
          {/* Map — 3/5 width */}
          <GlassCard className="lg:col-span-3 p-0 overflow-hidden min-h-[480px]">
            <div className="w-full h-full min-h-[480px]">
              <MapView
                center={displayCoords}
                places={filteredPlaces}
                selectedId={selectedId}
                onSelect={setSelectedId}
              />
            </div>
          </GlassCard>

          {/* Results list — 2/5 width */}
          <GlassCard className="lg:col-span-2 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">
                {loading
                  ? "Searching…"
                  : `${filteredPlaces.length} result${filteredPlaces.length !== 1 ? "s" : ""} found`}
              </h3>
              {rawPlaces.length !== filteredPlaces.length && !loading && (
                <span className="text-xs text-slate-500 font-mono">
                  {rawPlaces.length - filteredPlaces.length} filtered
                </span>
              )}
            </div>
            <PlaceList
              places={filteredPlaces}
              selectedId={selectedId}
              onSelect={setSelectedId}
              onOpenDrawer={setDrawerPlace}
              userLat={displayCoords.lat}
              userLng={displayCoords.lng}
              loading={loading}
              bestMatchId={bestMatchId}
            />
          </GlassCard>
        </div>

        <AlertBox variant="info">
          Results are sourced from OpenStreetMap contributors. Always verify facility details before visiting.
          This is not a substitute for professional medical advice.
        </AlertBox>
      </motion.div>

      {/* ── Clinic detail drawer (portal-like overlay) ─────────────── */}
      <PlaceDrawer
        place={drawerPlace}
        onClose={() => setDrawerPlace(null)}
        userLat={displayCoords.lat}
        userLng={displayCoords.lng}
      />
    </>
  );
}
