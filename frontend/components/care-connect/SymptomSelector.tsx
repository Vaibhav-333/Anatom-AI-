"use client";

import { useState, useRef } from "react";
import { X, Search, Plus } from "lucide-react";

const COMMON_SYMPTOMS = [
  "Headache", "Migraine", "Chest pain", "Shortness of breath", "Fever",
  "Cough", "Fatigue", "Nausea", "Vomiting", "Abdominal pain", "Back pain",
  "Joint pain", "Dizziness", "Skin rash", "Vision problems", "Ear pain",
  "Sore throat", "Anxiety", "Depression", "Insomnia", "Memory loss",
  "Numbness", "Tremor", "Weight gain", "Weight loss", "Frequent urination",
  "Heart palpitations", "Swollen joints", "Hair loss", "Blurry vision",
  "Nasal congestion", "Wheezing", "Bloating", "Constipation", "Diarrhea",
];

interface Props {
  selected: string[];
  onChange: (symptoms: string[]) => void;
}

export function SymptomSelector({ selected, onChange }: Props) {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = COMMON_SYMPTOMS.filter(
    (s) => s.toLowerCase().includes(query.toLowerCase()) && !selected.includes(s)
  );

  const add = (sym: string) => {
    if (!selected.includes(sym)) onChange([...selected, sym]);
    setQuery("");
    inputRef.current?.focus();
  };

  const remove = (sym: string) => onChange(selected.filter((s) => s !== sym));

  const addCustom = () => {
    const val = query.trim();
    if (val && !selected.includes(val)) {
      onChange([...selected, val]);
      setQuery("");
    }
  };

  return (
    <div className="space-y-3">
      {/* Selected chips */}
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selected.map((sym) => (
            <span key={sym} className="inline-flex items-center gap-1.5 bg-cyan/10 border border-cyan/30 text-cyan text-xs font-medium px-3 py-1.5 rounded-full">
              {sym}
              <button onClick={() => remove(sym)} className="hover:text-white transition-colors">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Search input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && addCustom()}
          placeholder="Search or type a symptom..."
          className="w-full bg-navy-800 border border-glass-border rounded-xl pl-9 pr-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-cyan/50 transition-colors"
        />
        {query.trim() && (
          <button onClick={addCustom} className="absolute right-3 top-1/2 -translate-y-1/2 text-cyan hover:text-white transition-colors">
            <Plus className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Suggestions */}
      {query ? (
        <div className="flex flex-wrap gap-2">
          {filtered.slice(0, 8).map((sym) => (
            <button key={sym} onClick={() => add(sym)}
              className="text-xs px-3 py-1.5 rounded-full border border-glass-border text-slate-300 hover:border-cyan/40 hover:text-cyan hover:bg-cyan/5 transition-all">
              {sym}
            </button>
          ))}
          {filtered.length === 0 && query.trim() && (
            <button onClick={addCustom}
              className="text-xs px-3 py-1.5 rounded-full border border-cyan/30 text-cyan bg-cyan/5 hover:bg-cyan/10 transition-all">
              Add &ldquo;{query}&rdquo;
            </button>
          )}
        </div>
      ) : (
        <div>
          <p className="text-xs text-slate-600 mb-2 uppercase tracking-wide font-medium">Common symptoms</p>
          <div className="flex flex-wrap gap-2">
            {COMMON_SYMPTOMS.filter((s) => !selected.includes(s)).slice(0, 16).map((sym) => (
              <button key={sym} onClick={() => add(sym)}
                className="text-xs px-3 py-1.5 rounded-full border border-glass-border text-slate-400 hover:border-cyan/40 hover:text-cyan hover:bg-cyan/5 transition-all">
                {sym}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
