// ─────────────────────────────────────────────────────────────────────────────
// Annotation System Configuration
// Positions are resolved at runtime from organMeshMapRef bounding-box centres.
// positionOffset is a world-space [x, y, z] delta applied on top of that centre.
// ─────────────────────────────────────────────────────────────────────────────

export type AnnotationSystem =
  | "all"
  | "cardiovascular"
  | "respiratory"
  | "digestive"
  | "reproductive"
  | "excretory";

export type AnnotationType     = "normal" | "disease";
export type AnnotationSeverity = "low" | "medium" | "high";

export interface AnnotationDef {
  id:             string;
  organ:          string;                        // must match ORGAN_REGISTRY key
  label:          string;                        // short display name (label mode)
  shortDesc:      string;                        // one-liner description (full mode)
  system:         AnnotationSystem;              // for activeSystem filtering
  wiki:           string;
  type:           AnnotationType;
  severity?:      AnnotationSeverity;            // disease annotations only
  positionOffset: [number, number, number];      // world-space delta from mesh centre
}

// ─────────────────────────────────────────────────────────────────────────────
// Annotation data
// system: 'all'  → shown only when activeSystem === 'all'
// system: <x>    → shown when activeSystem === 'all' OR activeSystem === <x>
// ─────────────────────────────────────────────────────────────────────────────
export const ANNOTATIONS: AnnotationDef[] = [
  // ── Cardiovascular ────────────────────────────────────────────────────────
  {
    id:             "ann-heart",
    organ:          "heart",
    label:          "Heart",
    shortDesc:      "~100,000 beats/day — 5 L/min cardiac output",
    system:         "cardiovascular",
    wiki:           "https://en.wikipedia.org/wiki/Heart",
    type:           "normal",
    positionOffset: [0, 0.02, 0.01],
  },

  // ── Respiratory ───────────────────────────────────────────────────────────
  {
    id:             "ann-lung",
    organ:          "lung",
    label:          "Lungs",
    shortDesc:      "70 m² alveolar surface for O₂ / CO₂ exchange",
    system:         "respiratory",
    wiki:           "https://en.wikipedia.org/wiki/Lung",
    type:           "normal",
    positionOffset: [0, 0.01, 0],
  },

  // ── Digestive ─────────────────────────────────────────────────────────────
  {
    id:             "ann-stomach",
    organ:          "stomach",
    label:          "Stomach",
    shortDesc:      "Churns food into chyme with HCl + pepsin",
    system:         "digestive",
    wiki:           "https://en.wikipedia.org/wiki/Stomach",
    type:           "normal",
    positionOffset: [0, 0, 0],
  },
  {
    id:             "ann-liver",
    organ:          "liver",
    label:          "Liver",
    shortDesc:      "Detoxifies blood, produces bile, stores glycogen",
    system:         "digestive",
    wiki:           "https://en.wikipedia.org/wiki/Liver",
    type:           "normal",
    positionOffset: [0.01, 0, 0],
  },
  {
    id:             "ann-intestine",
    organ:          "intestine",
    label:          "Intestines",
    shortDesc:      "Absorbs nutrients; hosts trillions of gut microbiome",
    system:         "digestive",
    wiki:           "https://en.wikipedia.org/wiki/Intestine",
    type:           "normal",
    positionOffset: [0, -0.01, 0],
  },
  {
    id:             "ann-gallbladder",
    organ:          "gallbladder",
    label:          "Gallbladder",
    shortDesc:      "Stores & releases bile for fat digestion",
    system:         "digestive",
    wiki:           "https://en.wikipedia.org/wiki/Gallbladder",
    type:           "normal",
    positionOffset: [0, 0, 0],
  },
  {
    id:             "ann-pancreas",
    organ:          "pancreas",
    label:          "Pancreas",
    shortDesc:      "Secretes enzymes + insulin / glucagon for blood sugar",
    system:         "digestive",
    wiki:           "https://en.wikipedia.org/wiki/Pancreas",
    type:           "normal",
    positionOffset: [0, 0, 0],
  },

  // ── Excretory ─────────────────────────────────────────────────────────────
  {
    id:             "ann-kidney",
    organ:          "kidney",
    label:          "Kidneys",
    shortDesc:      "Filters 200 L of blood per day; regulates electrolytes",
    system:         "excretory",
    wiki:           "https://en.wikipedia.org/wiki/Kidney",
    type:           "normal",
    positionOffset: [0, 0, 0],
  },
  {
    id:             "ann-bladder",
    organ:          "bladder",
    label:          "Bladder",
    shortDesc:      "Stores up to 500 ml of urine before micturition",
    system:         "excretory",
    wiki:           "https://en.wikipedia.org/wiki/Urinary_bladder",
    type:           "normal",
    positionOffset: [0, 0, 0],
  },

  // ── system: 'all' — no dedicated filter button ────────────────────────────
  {
    id:             "ann-brain",
    organ:          "brain",
    label:          "Brain",
    shortDesc:      "86 billion neurons — controls all bodily function",
    system:         "all",
    wiki:           "https://en.wikipedia.org/wiki/Brain",
    type:           "normal",
    positionOffset: [0, 0.03, 0],
  },
  {
    id:             "ann-spleen",
    organ:          "spleen",
    label:          "Spleen",
    shortDesc:      "Blood filter and immune cell reservoir",
    system:         "all",
    wiki:           "https://en.wikipedia.org/wiki/Spleen",
    type:           "normal",
    positionOffset: [0, 0, 0],
  },

  // ── Disease annotations ───────────────────────────────────────────────────
  {
    id:             "ann-brain-tumor",
    organ:          "brain",
    label:          "Glioblastoma Risk",
    shortDesc:      "Grade IV astrocytoma — most aggressive primary brain tumour",
    system:         "all",
    wiki:           "https://en.wikipedia.org/wiki/Glioblastoma",
    type:           "disease",
    severity:       "high",
    positionOffset: [0.015, 0.045, 0.005],
  },
  {
    id:             "ann-heart-arrhythmia",
    organ:          "heart",
    label:          "Arrhythmia",
    shortDesc:      "Irregular electrical impulse causing abnormal heart rhythm",
    system:         "cardiovascular",
    wiki:           "https://en.wikipedia.org/wiki/Arrhythmia",
    type:           "disease",
    severity:       "medium",
    positionOffset: [-0.01, 0.03, 0.01],
  },
];
