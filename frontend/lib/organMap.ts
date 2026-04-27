// ─────────────────────────────────────────────────────────────────────────────
// organMap.ts — Maps Gemini-returned organ names to 3D mesh keys
// and provides severity / risk colour utilities.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Maps any anatomical organ name (any case, common synonyms) to the
 * corresponding key used in `organRegistry.ts` and `ORGAN_REGISTRY` in
 * `SkeletonModel.tsx`.
 */
const ORGAN_KEY_MAP: Record<string, string> = {
  // Heart
  heart:        "heart",
  cardiac:      "heart",
  myocardium:   "heart",
  "heart muscle": "heart",

  // Lungs
  lungs:        "lung",
  lung:         "lung",
  pulmonary:    "lung",
  respiratory:  "lung",
  bronchi:      "lung",
  bronchial:    "lung",

  // Brain
  brain:        "brain",
  cerebral:     "brain",
  cerebrum:     "brain",
  cerebellum:   "brain",
  neurological: "brain",
  cranial:      "brain",

  // Liver
  liver:        "liver",
  hepatic:      "liver",

  // Kidneys
  kidney:       "kidney",
  kidneys:      "kidney",
  renal:        "kidney",

  // Stomach
  stomach:      "stomach",
  gastric:      "stomach",
  gastro:       "stomach",

  // Intestines / Colon
  colon:        "intestine",
  intestine:    "intestine",
  intestines:   "intestine",
  bowel:        "intestine",
  gut:          "intestine",
  colorectal:   "intestine",
  rectal:       "intestine",

  // Bladder
  bladder:      "bladder",
  "urinary bladder": "bladder",
  urinary:      "bladder",

  // Pancreas
  pancreas:     "pancreas",
  pancreatic:   "pancreas",

  // Gallbladder
  gallbladder:  "gallbladder",
  "gall bladder": "gallbladder",
  biliary:      "gallbladder",

  // Spleen
  spleen:       "spleen",
  splenic:      "spleen",
  lymphatic:    "spleen",

  // Eye
  eye:                "eye",
  eyes:               "eye",
  eyeball:            "eye",
  eyeballs:           "eye",
  ocular:             "eye",
  orbital:            "eye",
  optic:              "eye",
  retinal:            "eye",

  // Vertebral Column / Spine
  "vertebral column": "vertebral_column",
  vertebral:          "vertebral_column",
  vertebrae:          "vertebral_column",
  spine:              "vertebral_column",
  spinal:             "vertebral_column",
  "spinal cord":      "vertebral_column",
  lumbar:             "vertebral_column",
  thoracic:           "vertebral_column",

  // Mouth
  mouth:              "mouth",
  oral:               "mouth",
  jaw:                "mouth",
  mandible:           "mouth",
  dental:             "mouth",
  teeth:              "mouth",
  tongue:             "mouth",
}

/**
 * Resolve an organ name string to an organRegistry mesh key.
 * Returns null if no match found.
 */
export function resolveOrganKey(organName: string): string | null {
  return ORGAN_KEY_MAP[organName.toLowerCase().trim()] ?? null
}

// ─────────────────────────────────────────────────────────────────────────────
// Severity → glow / highlight colour
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Maps AI-returned severity strings to the glow sphere / emissive colour.
 * mild → amber · moderate → orange · severe → red
 */
export function severityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case "severe":   return "#FF3B3B"    // red
    case "moderate": return "#FF6B2C"    // orange
    case "mild":     return "#FFB300"    // amber
    default:         return "#4FC3F7"    // cyan (fallback / unknown)
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Condition → Organ mapping  id="mapping"
// Maps condition/disease names to affected anatomical organ names so the
// 3D viewer can auto-highlight the relevant body regions.
// ─────────────────────────────────────────────────────────────────────────────

const CONDITION_ORGAN_MAP: Record<string, string[]> = {
  // Cardiovascular
  "hypertension":               ["heart", "kidney"],
  "high blood pressure":        ["heart", "kidney"],
  "arrhythmia":                 ["heart"],
  "atrial fibrillation":        ["heart"],
  "heart failure":              ["heart"],
  "coronary artery disease":    ["heart"],
  "myocardial infarction":      ["heart"],
  "heart attack":               ["heart"],
  "cardiac":                    ["heart"],
  "pericarditis":               ["heart"],
  "cardiomyopathy":             ["heart"],
  // Respiratory
  "asthma":                     ["lung"],
  "pneumonia":                  ["lung"],
  "copd":                       ["lung"],
  "chronic obstructive":        ["lung"],
  "pulmonary embolism":         ["lung"],
  "bronchitis":                 ["lung"],
  "tuberculosis":               ["lung"],
  "pleural":                    ["lung"],
  // Neurological
  "stroke":                     ["brain"],
  "epilepsy":                   ["brain"],
  "migraine":                   ["brain"],
  "brain tumor":                ["brain"],
  "alzheimer":                  ["brain"],
  "dementia":                   ["brain"],
  "parkinson":                  ["brain"],
  "meningitis":                 ["brain"],
  "multiple sclerosis":         ["brain"],
  "neuropathy":                 ["brain"],
  // Metabolic / Endocrine
  "diabetes":                   ["pancreas", "kidney"],
  "type 2 diabetes":            ["pancreas", "kidney"],
  "type 1 diabetes":            ["pancreas"],
  "hypothyroidism":             ["stomach"],
  "hyperthyroidism":            ["stomach"],
  "thyroid":                    ["stomach"],
  // Renal
  "chronic kidney disease":     ["kidney"],
  "kidney stones":              ["kidney", "bladder"],
  "urinary tract":              ["bladder", "kidney"],
  "renal failure":              ["kidney"],
  "nephritis":                  ["kidney"],
  // Hepatic
  "fatty liver":                ["liver"],
  "hepatitis":                  ["liver"],
  "cirrhosis":                  ["liver"],
  "liver disease":              ["liver"],
  "jaundice":                   ["liver"],
  // Gastrointestinal
  "irritable bowel":            ["intestine"],
  "inflammatory bowel":         ["intestine"],
  "crohn":                      ["intestine"],
  "colitis":                    ["intestine"],
  "gastritis":                  ["stomach"],
  "peptic ulcer":               ["stomach"],
  "gallstones":                 ["gallbladder"],
  "pancreatitis":               ["pancreas"],
  "appendicitis":               ["intestine"],
  // Haematological
  "anemia":                     ["spleen"],
  "leukemia":                   ["spleen"],
  "lymphoma":                   ["spleen"],
  // Spinal / Musculoskeletal
  "spondylitis":                ["vertebral_column"],
  "disc herniation":            ["vertebral_column"],
  "spinal stenosis":            ["vertebral_column"],
  "osteoporosis":               ["vertebral_column"],
  // Ophthalmic
  "glaucoma":                   ["eye"],
  "cataract":                   ["eye"],
  "retinopathy":                ["eye"],
  "macular degeneration":       ["eye"],
};

/**
 * Map a condition / disease name to the list of organ names it affects.
 * Uses partial substring matching so e.g. "Type 2 Diabetes Mellitus" → ["pancreas", "kidney"].
 * Returns [] if no mapping found.
 */
export function conditionToOrgans(condition: string): string[] {
  const lower = condition.toLowerCase().trim();
  // Exact match first
  if (CONDITION_ORGAN_MAP[lower]) return CONDITION_ORGAN_MAP[lower];
  // Partial keyword match
  for (const [key, organs] of Object.entries(CONDITION_ORGAN_MAP)) {
    if (lower.includes(key) || key.includes(lower)) return organs;
  }
  return [];
}

/**
 * Maps risk_level strings to UI badge colours.
 * low → green · moderate → amber · high → orange · critical → red
 */
export function riskColor(riskLevel: string): string {
  switch (riskLevel.toLowerCase()) {
    case "critical": return "#FF3B3B"
    case "high":     return "#FF6B2C"
    case "moderate": return "#FFB300"
    default:         return "#00FF88"    // green = low
  }
}
