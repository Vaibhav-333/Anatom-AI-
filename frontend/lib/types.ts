// ──────────────────────────────────────────────
// Anatom-AI TypeScript Interfaces
// ──────────────────────────────────────────────

// ── Health Profile ──────────────────────────
export interface UserProfile {
  id: string;
  name: string;
  age: number;
  gender: "male" | "female" | "other";
  height_cm: number;
  weight_kg: number;
  blood_type?: string;
  conditions: string[];
  medications: string[];
  health_score: number;
  bmi?: number;
  metabolic_age?: number;
  created_at: string;
  updated_at: string;
}

export interface ProfileRequest {
  user_id: string;
  name: string;
  age: number;
  gender: string;
  height_cm: number;
  weight_kg: number;
  blood_type?: string;
  conditions: string[];
  medications: string[];
}

// ── Medical Report ───────────────────────────
export type Severity = "normal" | "borderline" | "critical";
export type ReportType =
  | "brain_mri"
  | "xray"
  | "blood_report"
  | "ct"
  | "ultrasound"
  | "unknown";
export type RiskLevel = "low" | "moderate" | "high" | "critical";

export interface Finding {
  text: string;
  severity: Severity;
  value?: string;
  unit?: string;
  reference_range?: string;
}

export interface AnatomicalMappingItem {
  region_id: string;
  finding_index: number;
  camera_focus: [number, number, number];
  severity: Severity;
}

export interface InterpretResponse {
  report_id: string;
  summary: string;
  findings: Finding[];
  affected_regions: string[];
  confidence: number;
  reasoning: string;
  report_type: ReportType;
  risk_level: RiskLevel;
  anatomical_mapping?: AnatomicalMappingItem[];
}

// ── Health Guidance ──────────────────────────
export interface DietRecommendation {
  nutrient: string;
  direction: "up" | "down" | "neutral";
  detail: string;
}

export interface ExerciseItem {
  name: string;
  duration: string;
  frequency: string;
}

export interface ExerciseGuidance {
  recommended: ExerciseItem[];
  avoid: string[];
  frequency: string;
}

export interface RedFlag {
  sign: string;
  severity: "er" | "urgent" | "monitor";
  action: string;
}

export interface GuidanceResponse {
  immediate_actions: string[];
  weekly_plan: string[];
  monthly_plan: string[];
  diet_recommendations: DietRecommendation[];
  exercise_guidance: ExerciseGuidance;
  warning_signs: string[];
  red_flags?: RedFlag[];
  supplements?: string[];
  consequence_timeline?: string;
  disclaimer: string;
}

export interface ScoreHistoryPoint {
  day: number;
  score: number;
}

// ── Report History ───────────────────────────
export type TriageLevel = "low" | "moderate" | "high" | "emergency";

export interface TriageResult {
  level: TriageLevel;
  recommendation: string;
  explanation: string;
  triggered_by: string[];
}

export interface KnowledgeGraphNode {
  id: string;
  label: string;
  type: "disease" | "organ" | "symptom" | "treatment";
  description?: string;
}

export interface KnowledgeGraphEdge {
  source: string;
  target: string;
  relation: string;
}

export interface KnowledgeGraphData {
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
  primary_condition: string;
}

export interface PersonalizedInsight {
  factor: string;
  impact: string;
  severity: "low" | "moderate" | "high";
}

export interface DiagnosisProbableCondition {
  name: string;
  confidence_pct: number;
  description: string;
}

export interface DiagnosisData {
  probable_conditions: DiagnosisProbableCondition[];
  affected_organs: string[];
  risk_level: string;
  red_flags: string[];
  next_steps: string[];
  treatment_suggestions: string[];
  recommended_specialization: string;
  personalized_insights?: PersonalizedInsight[];
  personalized_ai_summary?: string;
  disclaimer?: string;
}

export interface ReportSummary {
  id: string;
  user_id: string;
  file_name: string;
  file_type: string;
  report_type: ReportType;
  risk_level: RiskLevel;
  upload_date: string;
  summary_snippet: string;
  affected_regions: string[];
  triage_level?: TriageLevel;
}

export interface ReportDetail extends ReportSummary {
  interpretation: InterpretResponse;
  guidance?: GuidanceResponse;
  triage?: TriageResult;
  knowledge_graph?: KnowledgeGraphData;
  personalized_insights?: PersonalizedInsight[];
  diagnosis_data?: DiagnosisData;
}

// ── NeuroMapper API ──────────────────────────
export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
}

export interface VolumeResult {
  subject_id: string;
  wt_mm3: number;
  tc_mm3: number;
  et_mm3: number;
  volumes_mm3: Record<string, number>;
  fractions: Record<string, number>;
  tumor_centroid?: [number, number, number];
}

export interface LongitudinalReport {
  subject_id: string;
  days_elapsed: number;
  volumes_t1: Record<string, number>;
  volumes_t2: Record<string, number>;
  delta_mm3: Record<string, number>;
  rate_mm3_per_day: Record<string, number>;
  pct_change: Record<string, number>;
  rano_category: "CR" | "PR" | "SD" | "PD";
  rano_pct_change: number;
}

export interface TrajectoryResult {
  entry_point: [number, number, number];
  target_point: [number, number, number];
  path_length_mm: number;
  safety_score: number;
  composite_score: number;
  warnings: string[];
}

export interface TrajectoryResponse {
  tumor_centroid: [number, number, number];
  trajectories: TrajectoryResult[];
  subject_id: string;
}

// ── 3D Body Viewer ───────────────────────────
export type BodySystem =
  | "full"
  | "skeleton"
  | "muscular"
  | "cardiovascular"
  | "nervous"
  | "digestive"
  | "respiratory";

export interface BodyRegionInfo {
  id: string;
  name: string;
  description: string;
  relatedConditions: string[];
  position: [number, number, number];
}

export type CameraPreset = "front" | "back" | "left" | "right" | "top";

// ── UI State ─────────────────────────────────
export type InterpretMode = "simple" | "doctor";

export interface UploadState {
  file: File | null;
  uploading: boolean;
  progress: number;
  result?: InterpretResponse;
  error?: string;
}

export interface DashboardMetrics {
  healthScore: number;
  totalReports: number;
  lastUpload?: string;
  activeConditions: number;
  riskLevel: RiskLevel;
}
