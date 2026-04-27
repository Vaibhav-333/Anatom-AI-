import axios from "axios";
import type {
  HealthResponse,
  VolumeResult,
  LongitudinalReport,
  TrajectoryResponse,
  UserProfile,
  ProfileRequest,
  InterpretResponse,
  GuidanceResponse,
  ReportSummary,
  ReportDetail,
  InterpretMode,
} from "./types";

// ──────────────────────────────────────────────
// Axios instance pointing at FastAPI via Next.js proxy
// ──────────────────────────────────────────────
const api = axios.create({
  baseURL: "/api",
  timeout: 60000,
  headers: { "Content-Type": "application/json" },
});

// ── Health ────────────────────────────────────
export async function checkHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>("/health");
  return data;
}

// ── User Profile ──────────────────────────────
export async function createProfile(
  payload: ProfileRequest
): Promise<UserProfile> {
  const { data } = await api.post<UserProfile>("/profile", payload);
  return data;
}

export async function getProfile(userId: string): Promise<UserProfile> {
  const { data } = await api.get<UserProfile>(`/profile/${userId}`);
  return data;
}

// ── AI Document Interpretation ────────────────
export async function interpretDocument(
  file: File,
  userId: string,
  mode: InterpretMode = "simple"
): Promise<InterpretResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("user_id", userId);
  form.append("mode", mode);
  const { data } = await api.post<InterpretResponse>("/interpret", form, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120000,
  });
  return data;
}

// ── Health Guidance ───────────────────────────
export async function generateGuidance(
  reportId: string,
  userId: string
): Promise<GuidanceResponse> {
  const { data } = await api.post<GuidanceResponse>("/guidance", {
    report_id: reportId,
    user_id: userId,
  });
  return data;
}

// ── Report History ────────────────────────────
export async function getReportHistory(
  userId: string
): Promise<ReportSummary[]> {
  const { data } = await api.get<ReportSummary[]>(`/history/${userId}`);
  return data;
}

export async function getReportDetail(
  userId: string,
  reportId: string
): Promise<ReportDetail> {
  const { data } = await api.get<ReportDetail>(
    `/history/${userId}/${reportId}`
  );
  return data;
}

export async function deleteReport(
  userId: string,
  reportId: string
): Promise<void> {
  await api.delete(`/history/${userId}/${reportId}`);
}

// ── NeuroMapper — Volumetric Analysis ─────────
export async function analyzeVolume(
  segmentation: ArrayBuffer,
  voxelSpacing: [number, number, number],
  subjectId: string
): Promise<VolumeResult> {
  const b64 = arrayBufferToBase64(segmentation);
  const { data } = await api.post<VolumeResult>("/analyze/volume", {
    segmentation: { data: b64, dtype: "int16", shape: [] },
    voxel_spacing: voxelSpacing,
    subject_id: subjectId,
  });
  return data;
}

// ── NeuroMapper — Longitudinal Tracking ───────
export async function analyzeLongitudinal(
  seg1: ArrayBuffer,
  seg2: ArrayBuffer,
  voxelSpacing: [number, number, number],
  daysElapsed: number,
  subjectId: string
): Promise<LongitudinalReport> {
  const { data } = await api.post<LongitudinalReport>(
    "/analyze/longitudinal",
    {
      segmentation_t1: {
        data: arrayBufferToBase64(seg1),
        dtype: "int16",
        shape: [],
      },
      segmentation_t2: {
        data: arrayBufferToBase64(seg2),
        dtype: "int16",
        shape: [],
      },
      voxel_spacing: voxelSpacing,
      days_elapsed: daysElapsed,
      subject_id: subjectId,
    }
  );
  return data;
}

// ── NeuroMapper — Surgical Trajectory ─────────
export async function planTrajectory(
  segmentation: ArrayBuffer,
  subjectId: string
): Promise<TrajectoryResponse> {
  const { data } = await api.post<TrajectoryResponse>("/plan/trajectory", {
    segmentation: {
      data: arrayBufferToBase64(segmentation),
      dtype: "int16",
      shape: [],
    },
    subject_id: subjectId,
  });
  return data;
}

// ── Brain Render URL ──────────────────────────
export function getBrainRenderUrl(
  subjectId: string,
  mode: "standard" | "xray" = "standard"
): string {
  return `/api/render/brain/${subjectId}?mode=${mode}`;
}

// ── PDF Report ────────────────────────────────
export async function downloadPdfReport(payload: {
  subject_id: string;
  scan_date: string;
}): Promise<Blob> {
  const { data } = await api.post("/report/pdf", payload, {
    responseType: "blob",
  });
  return data;
}

// ── Helpers ───────────────────────────────────
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  bytes.forEach((b) => (binary += String.fromCharCode(b)));
  return btoa(binary);
}

export { api };
