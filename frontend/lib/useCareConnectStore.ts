import { create } from "zustand";
import { CareReport, CareReportSummary, Doctor, GenerateReportPayload } from "./careConnectApi";

interface WizardData {
  symptoms: string[];
  age: string;
  gender: string;
  medicalHistory: string[];
  severity: "mild" | "moderate" | "severe";
  durationDays: number;
}

interface CareConnectStore {
  // Wizard state
  wizardStep: 1 | 2 | 3;
  wizardData: WizardData;
  isGenerating: boolean;

  // Current report
  currentReport: CareReport | null;
  currentDoctors: Doctor[];

  // Report history
  reportHistory: CareReportSummary[];
  historyLoaded: boolean;

  // Saved doctors
  savedDoctorIds: Set<string>;

  // Actions
  setWizardStep: (step: 1 | 2 | 3) => void;
  setWizardData: (data: Partial<WizardData>) => void;
  resetWizard: () => void;
  setGenerating: (v: boolean) => void;
  setCurrentReport: (report: CareReport, doctors: Doctor[]) => void;
  setReportHistory: (history: CareReportSummary[]) => void;
  toggleSaveDoctor: (doctorId: string) => void;
  setSavedDoctorIds: (ids: string[]) => void;
  clearCurrentReport: () => void;
}

const defaultWizardData: WizardData = {
  symptoms: [],
  age: "",
  gender: "",
  medicalHistory: [],
  severity: "moderate",
  durationDays: 3,
};

export const useCareConnectStore = create<CareConnectStore>((set) => ({
  wizardStep: 1,
  wizardData: defaultWizardData,
  isGenerating: false,
  currentReport: null,
  currentDoctors: [],
  reportHistory: [],
  historyLoaded: false,
  savedDoctorIds: new Set(),

  setWizardStep: (step) => set({ wizardStep: step }),
  setWizardData: (data) =>
    set((s) => ({ wizardData: { ...s.wizardData, ...data } })),
  resetWizard: () =>
    set({ wizardStep: 1, wizardData: defaultWizardData, isGenerating: false }),
  setGenerating: (v) => set({ isGenerating: v }),
  setCurrentReport: (report, doctors) =>
    set({ currentReport: report, currentDoctors: doctors }),
  setReportHistory: (history) =>
    set({ reportHistory: history, historyLoaded: true }),
  toggleSaveDoctor: (doctorId) =>
    set((s) => {
      const next = new Set(s.savedDoctorIds);
      if (next.has(doctorId)) next.delete(doctorId);
      else next.add(doctorId);
      return { savedDoctorIds: next };
    }),
  setSavedDoctorIds: (ids) => set({ savedDoctorIds: new Set(ids) }),
  clearCurrentReport: () =>
    set({ currentReport: null, currentDoctors: [], wizardStep: 1, wizardData: defaultWizardData }),
}));
