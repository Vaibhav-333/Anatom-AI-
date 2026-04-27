import axios from "axios";

const api = axios.create({ baseURL: "/api" });

// ── Types ──────────────────────────────────────────────────────────────────

export interface ProbableCondition {
  name: string;
  confidence_pct: number;
  description: string;
}

export interface CareReport {
  id: string;
  user_id: string;
  created_at: string;
  symptoms: string[];
  user_age: number | null;
  user_gender: string | null;
  medical_history: string[];
  severity: string;
  duration_days: number;
  probable_conditions: ProbableCondition[];
  affected_organs: string[];
  risk_level: "low" | "medium" | "high" | "critical";
  red_flags: string[];
  next_steps: string[];
  treatment_suggestions: string[];
  recommended_specialization: string;
  pdf_path: string | null;
}

export interface CareReportSummary {
  id: string;
  created_at: string;
  symptoms: string[];
  risk_level: string;
  recommended_specialization: string;
  probable_conditions: ProbableCondition[];
}

export interface Doctor {
  id: string;
  name: string;
  specialization: string;
  subspecialties: string[];
  experience_years: number;
  rating: number;
  review_count: number;
  consultation_fee: number;
  mode: "online" | "offline" | "both";
  hospital: string;
  city: string;
  latitude: number;
  longitude: number;
  availability: Record<string, string[]>;
  verified: boolean;
  profile_image: string | null;
  degrees: string[];
  languages: string[];
  about: string;
  relevance_score?: number;
}

export interface GenerateReportPayload {
  user_id: string;
  symptoms: string[];
  age?: number;
  gender?: string;
  medical_history?: string[];
  severity: "mild" | "moderate" | "severe";
  duration_days: number;
}

export interface GenerateReportResponse {
  report_id: string;
  report: CareReport;
  recommended_doctors: Doctor[];
}

export interface ShareResponse {
  token: string;
  share_url: string;
  expires_at: string;
  view_count: number;
}

export interface PublicReportResponse {
  report_id: string;
  created_at: string;
  symptoms: string[];
  probable_conditions: ProbableCondition[];
  risk_level: string;
  red_flags: string[];
  next_steps: string[];
  recommended_specialization: string;
  expires_at: string;
  view_count: number;
}

// ── API Functions ──────────────────────────────────────────────────────────

export const careConnectApi = {
  // Report Generation
  generateReport: async (payload: GenerateReportPayload): Promise<GenerateReportResponse> => {
    const { data } = await api.post("/care-connect/report/generate", payload);
    return data;
  },

  getReport: async (reportId: string): Promise<GenerateReportResponse> => {
    const { data } = await api.get(`/care-connect/report/${reportId}`);
    return data;
  },

  listReports: async (userId: string): Promise<CareReportSummary[]> => {
    const { data } = await api.get(`/care-connect/reports/${userId}`);
    return data;
  },

  deleteReport: async (reportId: string): Promise<void> => {
    await api.delete(`/care-connect/report/${reportId}`);
  },

  // PDF
  downloadPdfUrl: (reportId: string) => `/api/care-connect/report/${reportId}/pdf`,

  // Sharing
  shareReport: async (reportId: string, expiryHours: number): Promise<ShareResponse> => {
    const { data } = await api.post(`/care-connect/report/${reportId}/share`, {
      expiry_hours: expiryHours,
    });
    return data;
  },

  getSharedReport: async (token: string): Promise<PublicReportResponse> => {
    const { data } = await api.get(`/care-connect/share/${token}`);
    return data;
  },

  revokeShare: async (token: string): Promise<void> => {
    await api.post(`/care-connect/share/${token}/revoke`);
  },

  // Doctors
  listDoctors: async (params?: {
    specialization?: string;
    mode?: string;
    max_fee?: number;
    min_rating?: number;
  }): Promise<Doctor[]> => {
    const { data } = await api.get("/care-connect/doctors", { params });
    return data;
  },

  getDoctor: async (doctorId: string): Promise<Doctor> => {
    const { data } = await api.get(`/care-connect/doctors/${doctorId}`);
    return data;
  },

  recommendDoctors: async (payload: {
    conditions?: string[];
    specialization?: string;
    city?: string;
    max_fee?: number;
    mode?: string;
  }): Promise<Doctor[]> => {
    const { data } = await api.post("/care-connect/doctors/recommend", payload);
    return data;
  },

  // Saved doctors
  saveDoctor: async (userId: string, doctorId: string): Promise<void> => {
    await api.post("/care-connect/saved-doctors", { user_id: userId, doctor_id: doctorId });
  },

  getSavedDoctors: async (userId: string): Promise<Doctor[]> => {
    const { data } = await api.get(`/care-connect/saved-doctors/${userId}`);
    return data;
  },

  unsaveDoctor: async (userId: string, doctorId: string): Promise<void> => {
    await api.delete(`/care-connect/saved-doctors/${userId}/${doctorId}`);
  },
};
