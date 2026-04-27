import { create } from "zustand";

export interface NutritionInfo {
  calories: number; protein_g: number; carbs_g: number; fat_g: number; fiber_g: number;
}

export interface MealEntry {
  name: string; description: string; nutrition: NutritionInfo; prep_time_min: number;
}

export interface ExerciseEntry {
  name: string; duration_min: number; intensity: "light" | "moderate" | "heavy"; instructions: string;
}

export interface LifestylePlanResponse {
  id: string; user_id: string; goal: string; dietary_pref: string;
  activity_level: string; plan_date: string;
  meals: Record<string, MealEntry[]>;
  daily_nutrition: NutritionInfo;
  exercises: ExerciseEntry[];
  avoid_list: string[];
  preventive_care: string[];
  ai_notes: string | null;
  auto_adjusted: boolean;
}

export interface LifestylePlanSummary {
  id: string; plan_date: string; goal: string; activity_level: string; auto_adjusted: boolean;
}

export interface LifestylePlanRequest {
  user_id: string;
  goal: "recovery" | "fitness" | "chronic_management";
  dietary_pref: string;
  restrictions: string[];
  activity_level: "sedentary" | "light" | "moderate" | "heavy";
  plan_date?: string;
}

interface LifestyleStore {
  latestPlan: LifestylePlanResponse | null;
  planHistory: LifestylePlanSummary[];
  isGenerating: boolean;
  formValues: LifestylePlanRequest | null;
  recommendations: string[];
  /** Set by the diagnostic report page to auto-trigger plan generation on navigation. */
  reportPreload: LifestylePlanRequest | null;
  // Actions
  setLatestPlan: (plan: LifestylePlanResponse) => void;
  setPlanHistory: (history: LifestylePlanSummary[]) => void;
  setGenerating: (v: boolean) => void;
  setFormValues: (values: LifestylePlanRequest) => void;
  setRecommendations: (recs: string[]) => void;
  setReportPreload: (req: LifestylePlanRequest | null) => void;
  resetStore: () => void;
}

export const useLifestyleStore = create<LifestyleStore>((set) => ({
  latestPlan: null, planHistory: [], isGenerating: false,
  formValues: null, recommendations: [], reportPreload: null,

  setLatestPlan: (plan) => set({ latestPlan: plan }),
  setPlanHistory: (history) => set({ planHistory: history }),
  setGenerating: (v) => set({ isGenerating: v }),
  setFormValues: (values) => set({ formValues: values }),
  setRecommendations: (recs) => set({ recommendations: recs }),
  setReportPreload: (req) => set({ reportPreload: req }),
  resetStore: () => set({ latestPlan: null, planHistory: [], formValues: null, recommendations: [], reportPreload: null }),
}));
