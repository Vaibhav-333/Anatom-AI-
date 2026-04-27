/**
 * Zustand store for Care Navigator cross-page state.
 * Persists analysis results from the Results page so the Care Navigator
 * can immediately show AI-recommended specialists on arrival.
 */
import { create } from "zustand";
import type { SpecialistRecommendation } from "./specialistMap";

interface CareNavigatorState {
  /** Raw condition strings extracted from the AI report */
  analysisConditions: string[];
  /** De-duplicated specialist recommendations derived from analysisConditions */
  recommendedSpecialists: SpecialistRecommendation[];

  // Actions
  setAnalysisResult: (
    conditions: string[],
    recommendations: SpecialistRecommendation[]
  ) => void;
  clearAnalysis: () => void;
}

export const useCareNavigatorStore = create<CareNavigatorState>()((set) => ({
  analysisConditions: [],
  recommendedSpecialists: [],

  setAnalysisResult: (conditions, recommendations) =>
    set({ analysisConditions: conditions, recommendedSpecialists: recommendations }),

  clearAnalysis: () =>
    set({ analysisConditions: [], recommendedSpecialists: [] }),
}));
