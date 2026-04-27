import axios from "axios";

const api = axios.create({ baseURL: "/api", timeout: 30000 });

export const healthTrackerApi = {
  // ── Symptoms ──────────────────────────────────────────────────────────────
  logSymptom: (payload: object) =>
    api.post("/health-tracker/symptoms", payload),
  getSymptoms: (userId: string, params?: object) =>
    api.get(`/health-tracker/symptoms/${userId}`, { params }),
  getTrends: (userId: string, params?: object) =>
    api.get(`/health-tracker/symptoms/${userId}/trends`, { params }),
  getHeatmap: (userId: string, year: number, month: number) =>
    api.get(`/health-tracker/symptoms/${userId}/heatmap`, { params: { year, month } }),
  deleteSymptomLog: (logId: string) =>
    api.delete(`/health-tracker/symptoms/${logId}`),

  // ── Medications ───────────────────────────────────────────────────────────
  addMedication: (payload: object) =>
    api.post("/health-tracker/medications", payload),
  getMedications: (userId: string, activeOnly = true) =>
    api.get(`/health-tracker/medications/${userId}`, { params: { active_only: activeOnly } }),
  deactivateMedication: (medId: string) =>
    api.patch(`/health-tracker/medications/${medId}/deactivate`),
  deleteMedication: (medId: string) =>
    api.delete(`/health-tracker/medications/${medId}`),

  // ── Medication Logs ───────────────────────────────────────────────────────
  logDose: (payload: object) =>
    api.post("/health-tracker/medication-logs", payload),
  getAdherence: (userId: string, params?: object) =>
    api.get(`/health-tracker/medication-logs/${userId}/adherence`, { params }),
  getMedCalendar: (userId: string, year: number, month: number) =>
    api.get(`/health-tracker/medication-logs/${userId}/calendar`, { params: { year, month } }),

  // ── Insights ──────────────────────────────────────────────────────────────
  getInsights: (userId: string, days = 14) =>
    api.get(`/health-tracker/insights/${userId}`, { params: { days } }),

  // ── Scores ────────────────────────────────────────────────────────────────
  getScores: (userId: string, weeks = 8) =>
    api.get(`/health-tracker/scores/${userId}`, { params: { weeks } }),
  computeScore: (userId: string) =>
    api.post(`/health-tracker/scores/${userId}/compute`),

  // ── Export ────────────────────────────────────────────────────────────────
  getPdfUrl: (userId: string, start?: string, end?: string) =>
    `/api/health-tracker/export/${userId}/pdf?start=${start ?? ""}&end=${end ?? ""}`,

  // ── Share ─────────────────────────────────────────────────────────────────
  shareReport: (payload: object) =>
    api.post("/health-tracker/share", payload),
  getSharedReport: (token: string) =>
    api.get(`/health-tracker/share/${token}`),
};
