"use client";

import { Building2, Stethoscope, Pill, Filter } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SearchFilters {
  radius: number;
  minRating: number;
  openNow: boolean;
}

export type SearchType = "hospital" | "doctor" | "pharmacy";

interface FiltersProps {
  searchType: SearchType;
  onSearchTypeChange: (type: SearchType) => void;
  filters: SearchFilters;
  onFiltersChange: (patch: Partial<SearchFilters>) => void;
  disabled?: boolean;
}

const TYPE_OPTIONS: { value: SearchType; label: string; icon: React.ReactNode }[] = [
  { value: "hospital", label: "Hospitals", icon: <Building2 className="w-3.5 h-3.5" /> },
  { value: "doctor", label: "Clinics", icon: <Stethoscope className="w-3.5 h-3.5" /> },
  { value: "pharmacy", label: "Pharmacies", icon: <Pill className="w-3.5 h-3.5" /> },
];

const RADIUS_OPTIONS = [
  { value: 2000, label: "2 km" },
  { value: 5000, label: "5 km" },
  { value: 10000, label: "10 km" },
];

const RATING_OPTIONS = [
  { value: 0, label: "Any" },
  { value: 4, label: "4+" },
  { value: 4.5, label: "4.5+" },
];

export function Filters({
  searchType,
  onSearchTypeChange,
  filters,
  onFiltersChange,
  disabled,
}: FiltersProps) {
  return (
    <div className="space-y-3">
      {/* Search type tabs */}
      <div className="flex gap-1 p-1 rounded-lg bg-navy-800/60 border border-glass-border">
        {TYPE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => !disabled && onSearchTypeChange(opt.value)}
            disabled={disabled}
            className={cn(
              "flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-md text-xs font-medium transition-all duration-150",
              searchType === opt.value
                ? "bg-cyan/15 text-cyan border border-cyan/30"
                : "text-slate-400 hover:text-slate-200 hover:bg-navy-700/60",
              disabled && "opacity-50 cursor-not-allowed"
            )}
          >
            {opt.icon}
            {opt.label}
          </button>
        ))}
      </div>

      {/* Secondary filters row */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1.5">
          <Filter className="w-3 h-3 text-slate-500" />
          <span className="text-xs text-slate-500 font-medium">Filters:</span>
        </div>

        {/* Radius */}
        <div className="flex items-center gap-1">
          <span className="text-xs text-slate-600">Radius:</span>
          <div className="flex gap-0.5">
            {RADIUS_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => !disabled && onFiltersChange({ radius: opt.value })}
                disabled={disabled}
                className={cn(
                  "px-2 py-1 rounded text-xs font-mono transition-all duration-150",
                  filters.radius === opt.value
                    ? "bg-cyan/15 text-cyan border border-cyan/30"
                    : "text-slate-500 hover:text-slate-300 border border-transparent hover:border-glass-border",
                  disabled && "opacity-50 cursor-not-allowed"
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Rating */}
        <div className="flex items-center gap-1">
          <span className="text-xs text-slate-600">Rating:</span>
          <div className="flex gap-0.5">
            {RATING_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => !disabled && onFiltersChange({ minRating: opt.value })}
                disabled={disabled}
                className={cn(
                  "px-2 py-1 rounded text-xs font-mono transition-all duration-150",
                  filters.minRating === opt.value
                    ? "bg-cyan/15 text-cyan border border-cyan/30"
                    : "text-slate-500 hover:text-slate-300 border border-transparent hover:border-glass-border",
                  disabled && "opacity-50 cursor-not-allowed"
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Open now */}
        <button
          onClick={() => !disabled && onFiltersChange({ openNow: !filters.openNow })}
          disabled={disabled}
          className={cn(
            "flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium transition-all duration-150 border",
            filters.openNow
              ? "bg-green/10 text-green border-green/30"
              : "text-slate-500 border-transparent hover:text-slate-300 hover:border-glass-border",
            disabled && "opacity-50 cursor-not-allowed"
          )}
        >
          <span
            className={cn(
              "w-1.5 h-1.5 rounded-full",
              filters.openNow ? "bg-green" : "bg-slate-600"
            )}
          />
          Open now
        </button>
      </div>
    </div>
  );
}
