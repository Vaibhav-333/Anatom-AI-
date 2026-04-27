// ─────────────────────────────────────────────────────────────────────────────
// Disease Registry — single source of truth for disease → organ mapping.
// Used by BodyScene (scan UI) and OrganPanel (disease info card).
// ─────────────────────────────────────────────────────────────────────────────

export interface DiseaseData {
  label:       string    // display name
  organ:       string    // must match ORGAN_REGISTRY key (heart / lung / etc.)
  system:      string    // body system name
  color:       string    // alert colour — distinct from the organ's default colour
  wiki:        string    // Wikipedia disease URL
  description: string    // one-line clinical summary
  keywords:    string[]  // lowercase patterns used by extractDisease()
}

export const DISEASE_MAP: Record<string, DiseaseData> = {

  // ── Cardiovascular ──────────────────────────────────────────────────────────
  arrhythmia: {
    label: "Arrhythmia",
    organ: "heart", system: "Cardiovascular",
    color: "#FF3B3B",
    wiki: "https://en.wikipedia.org/wiki/Arrhythmia",
    description: "Irregular electrical impulse causing abnormal heart rhythm.",
    keywords: ["arrhythmia", "irregular heartbeat", "irregular heart", "palpitation"],
  },
  heart_failure: {
    label: "Heart Failure",
    organ: "heart", system: "Cardiovascular",
    color: "#FF3B3B",
    wiki: "https://en.wikipedia.org/wiki/Heart_failure",
    description: "Heart cannot pump blood efficiently to meet the body's needs.",
    keywords: ["heart failure", "cardiac failure", "congestive heart", "chf"],
  },
  coronary_artery_disease: {
    label: "Coronary Artery Disease",
    organ: "heart", system: "Cardiovascular",
    color: "#FF3B3B",
    wiki: "https://en.wikipedia.org/wiki/Coronary_artery_disease",
    description: "Plaque buildup in coronary arteries reducing blood flow to heart muscle.",
    keywords: ["coronary artery disease", "cad", "coronary disease", "angina", "atherosclerosis"],
  },
  cardiomyopathy: {
    label: "Cardiomyopathy",
    organ: "heart", system: "Cardiovascular",
    color: "#FF3B3B",
    wiki: "https://en.wikipedia.org/wiki/Cardiomyopathy",
    description: "Disease of the heart muscle making it harder to pump blood.",
    keywords: ["cardiomyopathy", "heart muscle disease", "dilated cardiomyopathy", "hypertrophic cardiomyopathy"],
  },

  // ── Respiratory ─────────────────────────────────────────────────────────────
  pneumonia: {
    label: "Pneumonia",
    organ: "lung", system: "Respiratory",
    color: "#4FC3F7",
    wiki: "https://en.wikipedia.org/wiki/Pneumonia",
    description: "Infection inflaming the air sacs (alveoli) in one or both lungs.",
    keywords: ["pneumonia", "lung infection", "alveolar infection"],
  },
  asthma: {
    label: "Asthma",
    organ: "lung", system: "Respiratory",
    color: "#4FC3F7",
    wiki: "https://en.wikipedia.org/wiki/Asthma",
    description: "Chronic airway inflammation causing recurring breathing difficulty.",
    keywords: ["asthma", "bronchospasm", "wheezing", "inhaler"],
  },
  copd: {
    label: "COPD",
    organ: "lung", system: "Respiratory",
    color: "#4FC3F7",
    wiki: "https://en.wikipedia.org/wiki/Chronic_obstructive_pulmonary_disease",
    description: "Progressive obstruction of airflow, typically from long-term smoking.",
    keywords: ["copd", "chronic obstructive pulmonary", "emphysema", "chronic bronchitis"],
  },
  lung_cancer: {
    label: "Lung Cancer",
    organ: "lung", system: "Respiratory",
    color: "#4FC3F7",
    wiki: "https://en.wikipedia.org/wiki/Lung_cancer",
    description: "Malignant tumour arising from lung tissue, most often from smoking.",
    keywords: ["lung cancer", "pulmonary carcinoma", "non-small cell lung", "small cell lung"],
  },

  // ── Digestive — Stomach ─────────────────────────────────────────────────────
  gastritis: {
    label: "Gastritis",
    organ: "stomach", system: "Digestive",
    color: "#FFA726",
    wiki: "https://en.wikipedia.org/wiki/Gastritis",
    description: "Inflammation of the stomach lining, often from H. pylori or NSAIDs.",
    keywords: ["gastritis", "stomach inflammation", "stomach lining"],
  },
  peptic_ulcer: {
    label: "Peptic Ulcer",
    organ: "stomach", system: "Digestive",
    color: "#FFA726",
    wiki: "https://en.wikipedia.org/wiki/Peptic_ulcer_disease",
    description: "Open sore on the inner stomach lining due to acid erosion.",
    keywords: ["peptic ulcer", "stomach ulcer", "gastric ulcer", "duodenal ulcer"],
  },
  gerd: {
    label: "GERD",
    organ: "stomach", system: "Digestive",
    color: "#FFA726",
    wiki: "https://en.wikipedia.org/wiki/Gastroesophageal_reflux_disease",
    description: "Chronic acid reflux from stomach into the oesophagus.",
    keywords: ["gerd", "acid reflux", "heartburn", "gastroesophageal reflux"],
  },
  gastric_cancer: {
    label: "Gastric Cancer",
    organ: "stomach", system: "Digestive",
    color: "#FFA726",
    wiki: "https://en.wikipedia.org/wiki/Stomach_cancer",
    description: "Malignant tumour originating in the stomach lining.",
    keywords: ["gastric cancer", "stomach cancer", "gastric carcinoma"],
  },

  // ── Digestive — Liver ───────────────────────────────────────────────────────
  hepatitis: {
    label: "Hepatitis",
    organ: "liver", system: "Digestive / Metabolic",
    color: "#EF5350",
    wiki: "https://en.wikipedia.org/wiki/Hepatitis",
    description: "Liver inflammation from viral infection (A/B/C), toxins, or autoimmunity.",
    keywords: ["hepatitis", "liver inflammation", "hbv", "hcv", "jaundice"],
  },
  cirrhosis: {
    label: "Cirrhosis",
    organ: "liver", system: "Digestive / Metabolic",
    color: "#EF5350",
    wiki: "https://en.wikipedia.org/wiki/Cirrhosis",
    description: "Scarring of liver tissue that impairs function, often from chronic hepatitis or alcohol.",
    keywords: ["cirrhosis", "liver fibrosis", "liver scarring", "liver failure"],
  },
  nafld: {
    label: "Non-alcoholic Fatty Liver Disease",
    organ: "liver", system: "Digestive / Metabolic",
    color: "#EF5350",
    wiki: "https://en.wikipedia.org/wiki/Non-alcoholic_fatty_liver_disease",
    description: "Excess fat accumulation in the liver unrelated to alcohol consumption.",
    keywords: ["nafld", "fatty liver", "non-alcoholic fatty liver", "nash"],
  },

  // ── Excretory — Kidneys ─────────────────────────────────────────────────────
  chronic_kidney_disease: {
    label: "Chronic Kidney Disease",
    organ: "kidney", system: "Excretory",
    color: "#8D6E63",
    wiki: "https://en.wikipedia.org/wiki/Chronic_kidney_disease",
    description: "Gradual loss of kidney function over months or years.",
    keywords: ["chronic kidney disease", "ckd", "renal failure", "kidney failure", "renal insufficiency"],
  },
  kidney_stones: {
    label: "Kidney Stones",
    organ: "kidney", system: "Excretory",
    color: "#8D6E63",
    wiki: "https://en.wikipedia.org/wiki/Kidney_stone_disease",
    description: "Hard mineral deposits formed inside the kidneys causing severe pain.",
    keywords: ["kidney stone", "renal calculi", "nephrolithiasis", "urolithiasis"],
  },
  glomerulonephritis: {
    label: "Glomerulonephritis",
    organ: "kidney", system: "Excretory",
    color: "#8D6E63",
    wiki: "https://en.wikipedia.org/wiki/Glomerulonephritis",
    description: "Inflammation of the kidney's filtering units (glomeruli).",
    keywords: ["glomerulonephritis", "glomerular disease", "nephritis"],
  },

  // ── Digestive — Intestines ──────────────────────────────────────────────────
  ibs: {
    label: "Irritable Bowel Syndrome",
    organ: "intestine", system: "Digestive",
    color: "#D4A017",
    wiki: "https://en.wikipedia.org/wiki/Irritable_bowel_syndrome",
    description: "Functional gut disorder with recurrent abdominal pain and altered bowel habits.",
    keywords: ["ibs", "irritable bowel", "irritable bowel syndrome"],
  },
  crohns: {
    label: "Crohn's Disease",
    organ: "intestine", system: "Digestive",
    color: "#D4A017",
    wiki: "https://en.wikipedia.org/wiki/Crohn%27s_disease",
    description: "Chronic inflammatory bowel disease affecting any part of the GI tract.",
    keywords: ["crohn", "crohn's disease", "inflammatory bowel disease", "ibd"],
  },
  colorectal_cancer: {
    label: "Colorectal Cancer",
    organ: "intestine", system: "Digestive",
    color: "#D4A017",
    wiki: "https://en.wikipedia.org/wiki/Colorectal_cancer",
    description: "Cancer of the colon or rectum, often preceded by polyps.",
    keywords: ["colorectal cancer", "colon cancer", "rectal cancer", "bowel cancer", "colorectal carcinoma"],
  },

  // ── Nervous System — Brain ──────────────────────────────────────────────────
  stroke: {
    label: "Stroke",
    organ: "brain", system: "Nervous",
    color: "#CE93D8",
    wiki: "https://en.wikipedia.org/wiki/Stroke",
    description: "Sudden disruption of blood supply to part of the brain.",
    keywords: ["stroke", "cerebrovascular accident", "cva", "brain infarction", "tia", "transient ischemic"],
  },
  alzheimers: {
    label: "Alzheimer's Disease",
    organ: "brain", system: "Nervous",
    color: "#CE93D8",
    wiki: "https://en.wikipedia.org/wiki/Alzheimer%27s_disease",
    description: "Progressive neurodegenerative disease causing memory loss and cognitive decline.",
    keywords: ["alzheimer", "alzheimer's", "dementia", "memory loss"],
  },
  brain_tumour: {
    label: "Brain Tumour",
    organ: "brain", system: "Nervous",
    color: "#CE93D8",
    wiki: "https://en.wikipedia.org/wiki/Brain_tumor",
    description: "Abnormal mass of tissue in the brain, benign or malignant.",
    keywords: ["brain tumour", "brain tumor", "glioma", "glioblastoma", "meningioma", "gbm", "astrocytoma"],
  },
  parkinsons: {
    label: "Parkinson's Disease",
    organ: "brain", system: "Nervous",
    color: "#CE93D8",
    wiki: "https://en.wikipedia.org/wiki/Parkinson%27s_disease",
    description: "Neurodegenerative disorder causing tremor, rigidity, and bradykinesia.",
    keywords: ["parkinson", "parkinson's", "parkinsonism", "bradykinesia", "tremor"],
  },
  epilepsy: {
    label: "Epilepsy",
    organ: "brain", system: "Nervous",
    color: "#CE93D8",
    wiki: "https://en.wikipedia.org/wiki/Epilepsy",
    description: "Neurological disorder marked by recurrent unprovoked seizures.",
    keywords: ["epilepsy", "seizure", "epileptic", "convulsion"],
  },

  // ── Excretory — Bladder ─────────────────────────────────────────────────────
  uti: {
    label: "Urinary Tract Infection",
    organ: "bladder", system: "Excretory",
    color: "#64B5F6",
    wiki: "https://en.wikipedia.org/wiki/Urinary_tract_infection",
    description: "Bacterial infection of the urinary tract, most commonly the bladder.",
    keywords: ["urinary tract infection", "uti", "cystitis", "bladder infection"],
  },
  bladder_cancer: {
    label: "Bladder Cancer",
    organ: "bladder", system: "Excretory",
    color: "#64B5F6",
    wiki: "https://en.wikipedia.org/wiki/Bladder_cancer",
    description: "Malignant tumour arising in the lining of the urinary bladder.",
    keywords: ["bladder cancer", "bladder carcinoma", "urothelial carcinoma"],
  },

  // ── Endocrine — Pancreas ────────────────────────────────────────────────────
  diabetes: {
    label: "Diabetes Mellitus",
    organ: "pancreas", system: "Endocrine",
    color: "#FFB300",
    wiki: "https://en.wikipedia.org/wiki/Diabetes_mellitus",
    description: "Metabolic disorder characterised by chronic high blood glucose levels.",
    keywords: ["diabetes", "diabetic", "type 1 diabetes", "type 2 diabetes", "hyperglycemia", "insulin resistance"],
  },
  pancreatitis: {
    label: "Pancreatitis",
    organ: "pancreas", system: "Digestive",
    color: "#FFB300",
    wiki: "https://en.wikipedia.org/wiki/Pancreatitis",
    description: "Inflammation of the pancreas causing severe abdominal pain.",
    keywords: ["pancreatitis", "pancreas inflammation"],
  },
  pancreatic_cancer: {
    label: "Pancreatic Cancer",
    organ: "pancreas", system: "Digestive",
    color: "#FFB300",
    wiki: "https://en.wikipedia.org/wiki/Pancreatic_cancer",
    description: "Aggressive malignancy arising from pancreatic tissue.",
    keywords: ["pancreatic cancer", "pancreas cancer", "pancreatic carcinoma", "pancreatic adenocarcinoma"],
  },

  // ── Digestive — Gallbladder ─────────────────────────────────────────────────
  gallstones: {
    label: "Gallstones",
    organ: "gallbladder", system: "Digestive",
    color: "#9CCC65",
    wiki: "https://en.wikipedia.org/wiki/Gallstone",
    description: "Hardened deposits of bile forming in the gallbladder.",
    keywords: ["gallstone", "cholelithiasis", "biliary colic", "gallbladder stone"],
  },
  cholecystitis: {
    label: "Cholecystitis",
    organ: "gallbladder", system: "Digestive",
    color: "#9CCC65",
    wiki: "https://en.wikipedia.org/wiki/Cholecystitis",
    description: "Inflammation of the gallbladder, usually caused by gallstones.",
    keywords: ["cholecystitis", "gallbladder inflammation", "acute cholecystitis"],
  },

  // ── Lymphatic / Immune — Spleen ─────────────────────────────────────────────
  splenomegaly: {
    label: "Splenomegaly",
    organ: "spleen", system: "Lymphatic / Immune",
    color: "#F06292",
    wiki: "https://en.wikipedia.org/wiki/Splenomegaly",
    description: "Abnormal enlargement of the spleen, often due to infection or blood disorders.",
    keywords: ["splenomegaly", "enlarged spleen", "spleen enlargement"],
  },
  lymphoma: {
    label: "Lymphoma",
    organ: "spleen", system: "Lymphatic / Immune",
    color: "#F06292",
    wiki: "https://en.wikipedia.org/wiki/Lymphoma",
    description: "Cancer of the lymphatic system, including the spleen and lymph nodes.",
    keywords: ["lymphoma", "hodgkin", "non-hodgkin", "lymphatic cancer"],
  },
}

// ─────────────────────────────────────────────────────────────────────────────
// extractDisease
// Pure keyword-match: scans reportText for any disease keyword.
// Returns the first DISEASE_MAP key matched, or null if nothing found.
// O(diseases × keywords) — deterministic, no randomness, no side effects.
// ─────────────────────────────────────────────────────────────────────────────
export function extractDisease(reportText: string): string | null {
  const lower = reportText.toLowerCase()
  for (const [key, data] of Object.entries(DISEASE_MAP)) {
    if (data.keywords.some((kw) => lower.includes(kw))) return key
  }
  return null
}
