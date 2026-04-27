import { create } from "zustand";

export interface SymptomLogResponse {
  id: string; user_id: string; logged_at: string; date_key: string;
  pain_level: number | null; fever_celsius: number | null; fatigue: string | null;
  mood: number | null; sleep_hours: number | null;
  custom_symptoms: string[]; notes: string | null;
}

export interface SymptomTrendPoint {
  date: string; avg_pain: number | null; avg_mood: number | null;
  avg_sleep: number | null; avg_fever: number | null; entry_count: number;
}

export interface CalendarHeatmapPoint { date: string; intensity: number; }

export interface MedicationResponse {
  id: string; user_id: string; name: string; dosage: string;
  frequency: string; duration_days: number | null;
  start_date: string; end_date: string | null; active: boolean;
}

export interface AdherenceStats {
  medication_id: string; medication_name: string;
  total_doses: number; taken: number; missed: number;
  adherence_pct: number; last_7_days: { date: string; status: string }[];
}

export interface MedLogResponse {
  id: string; medication_id: string; user_id: string;
  scheduled_for: string; taken_at: string | null; status: string; date_key: string;
}

export interface InsightAlert {
  type: string; severity: string; title: string; message: string; metric: string | null;
}

export interface InsightsResponse {
  trend: string; weekly_score: number; alerts: InsightAlert[];
  suggestions: string[]; correlation_notes: string[];
  prediction_next_3_days: { pain: number; mood: number };
}

export interface WeeklyScoreResponse {
  id: string; user_id: string; week_key: string; score: number;
  symptom_avg: number | null; adherence_pct: number | null;
  sleep_avg: number | null; trend: string; streak_days: number; badges: string[];
}

interface HealthTrackerStore {
  symptomLogs: SymptomLogResponse[];
  trendData: SymptomTrendPoint[];
  heatmapData: CalendarHeatmapPoint[];
  heatmapYear: number;
  heatmapMonth: number;
  symptomsLoaded: boolean;
  medications: MedicationResponse[];
  adherenceStats: AdherenceStats[];
  todayMedLogs: MedLogResponse[];
  medicationsLoaded: boolean;
  insights: InsightsResponse | null;
  weeklyScores: WeeklyScoreResponse[];
  insightsLoaded: boolean;
  trendPeriod: "weekly" | "monthly";
  selectedMedId: string | null;
  // Actions
  setSymptomLogs: (logs: SymptomLogResponse[]) => void;
  addSymptomLog: (log: SymptomLogResponse) => void;
  removeSymptomLog: (id: string) => void;
  setTrendData: (data: SymptomTrendPoint[]) => void;
  setHeatmapData: (data: CalendarHeatmapPoint[]) => void;
  setHeatmapMonth: (year: number, month: number) => void;
  setSymptomsLoaded: (v: boolean) => void;
  setMedications: (meds: MedicationResponse[]) => void;
  addMedication: (med: MedicationResponse) => void;
  removeMedication: (id: string) => void;
  setAdherenceStats: (stats: AdherenceStats[]) => void;
  setTodayMedLogs: (logs: MedLogResponse[]) => void;
  addMedLog: (log: MedLogResponse) => void;
  setMedicationsLoaded: (v: boolean) => void;
  setInsights: (insights: InsightsResponse) => void;
  setWeeklyScores: (scores: WeeklyScoreResponse[]) => void;
  setInsightsLoaded: (v: boolean) => void;
  setTrendPeriod: (p: "weekly" | "monthly") => void;
  setSelectedMedId: (id: string | null) => void;
  resetStore: () => void;
}

const now = new Date();

export const useHealthTrackerStore = create<HealthTrackerStore>((set) => ({
  symptomLogs: [], trendData: [], heatmapData: [],
  heatmapYear: now.getFullYear(), heatmapMonth: now.getMonth() + 1,
  symptomsLoaded: false,
  medications: [], adherenceStats: [], todayMedLogs: [], medicationsLoaded: false,
  insights: null, weeklyScores: [], insightsLoaded: false,
  trendPeriod: "weekly", selectedMedId: null,

  setSymptomLogs: (logs) => set({ symptomLogs: logs, symptomsLoaded: true }),
  addSymptomLog: (log) => set((s) => ({ symptomLogs: [log, ...s.symptomLogs] })),
  removeSymptomLog: (id) => set((s) => ({ symptomLogs: s.symptomLogs.filter((l) => l.id !== id) })),
  setTrendData: (data) => set({ trendData: data }),
  setHeatmapData: (data) => set({ heatmapData: data }),
  setHeatmapMonth: (year, month) => set({ heatmapYear: year, heatmapMonth: month }),
  setSymptomsLoaded: (v) => set({ symptomsLoaded: v }),
  setMedications: (meds) => set({ medications: meds, medicationsLoaded: true }),
  addMedication: (med) => set((s) => ({ medications: [med, ...s.medications] })),
  removeMedication: (id) => set((s) => ({ medications: s.medications.filter((m) => m.id !== id) })),
  setAdherenceStats: (stats) => set({ adherenceStats: stats }),
  setTodayMedLogs: (logs) => set({ todayMedLogs: logs }),
  addMedLog: (log) => set((s) => ({ todayMedLogs: [log, ...s.todayMedLogs] })),
  setMedicationsLoaded: (v) => set({ medicationsLoaded: v }),
  setInsights: (insights) => set({ insights, insightsLoaded: true }),
  setWeeklyScores: (scores) => set({ weeklyScores: scores }),
  setInsightsLoaded: (v) => set({ insightsLoaded: v }),
  setTrendPeriod: (p) => set({ trendPeriod: p }),
  setSelectedMedId: (id) => set({ selectedMedId: id }),
  resetStore: () => set({
    symptomLogs: [], trendData: [], heatmapData: [],
    medications: [], adherenceStats: [], todayMedLogs: [],
    insights: null, weeklyScores: [],
    symptomsLoaded: false, medicationsLoaded: false, insightsLoaded: false,
  }),
}));
