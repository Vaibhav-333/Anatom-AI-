// Maps disease/condition names to the appropriate medical specialist type.

/** A single AI-derived specialist recommendation. */
export interface SpecialistRecommendation {
  disease: string;
  specialist: string;
}

export const specialistMap: Record<string, string> = {
  // Neurology
  "Brain Tumor": "Neurologist",
  "Glioma": "Neurologist",
  "Glioblastoma": "Neurologist",
  "Meningioma": "Neurologist",
  "Stroke": "Neurologist",
  "Epilepsy": "Neurologist",
  "Multiple Sclerosis": "Neurologist",
  "Parkinson's Disease": "Neurologist",
  "Alzheimer's Disease": "Neurologist",
  "Migraine": "Neurologist",

  // Cardiology
  "Heart Disease": "Cardiologist",
  "Myocardial Infarction": "Cardiologist",
  "Coronary Artery Disease": "Cardiologist",
  "Heart Failure": "Cardiologist",
  "Arrhythmia": "Cardiologist",
  "Hypertension": "Cardiologist",
  "Atrial Fibrillation": "Cardiologist",

  // Gastroenterology
  "Ulcerative Colitis": "Gastroenterologist",
  "Crohn's Disease": "Gastroenterologist",
  "Irritable Bowel Syndrome": "Gastroenterologist",
  "Colon Cancer": "Gastroenterologist",
  "Colorectal Cancer": "Gastroenterologist",
  "Gastritis": "Gastroenterologist",
  "GERD": "Gastroenterologist",
  "Peptic Ulcer": "Gastroenterologist",

  // Hepatology
  "Liver Cirrhosis": "Hepatologist",
  "Hepatitis": "Hepatologist",
  "Fatty Liver Disease": "Hepatologist",
  "Liver Cancer": "Hepatologist",

  // Endocrinology
  "Diabetes": "Endocrinologist",
  "Type 2 Diabetes": "Endocrinologist",
  "Type 1 Diabetes": "Endocrinologist",
  "Thyroid Disease": "Endocrinologist",
  "Hypothyroidism": "Endocrinologist",
  "Hyperthyroidism": "Endocrinologist",
  "Cushing's Syndrome": "Endocrinologist",

  // Pulmonology
  "Lung Cancer": "Pulmonologist",
  "Pneumonia": "Pulmonologist",
  "COPD": "Pulmonologist",
  "Asthma": "Pulmonologist",
  "Pulmonary Fibrosis": "Pulmonologist",
  "Tuberculosis": "Pulmonologist",

  // Nephrology
  "Kidney Disease": "Nephrologist",
  "Chronic Kidney Disease": "Nephrologist",
  "Kidney Stones": "Nephrologist",
  "Glomerulonephritis": "Nephrologist",

  // Rheumatology / Orthopedics
  "Arthritis": "Rheumatologist",
  "Rheumatoid Arthritis": "Rheumatologist",
  "Lupus": "Rheumatologist",
  "Osteoporosis": "Orthopedist",
  "Osteoarthritis": "Orthopedist",

  // Oncology
  "Cancer": "Oncologist",
  "Lymphoma": "Oncologist",
  "Leukemia": "Oncologist",
  "Breast Cancer": "Oncologist",
};

/**
 * Returns the best-matching specialist for a given condition name.
 * Tries exact match first, then case-insensitive keyword scan.
 * Falls back to "General Physician".
 */
export function getSpecialist(condition: string): string {
  if (!condition) return "General Physician";

  // Exact match
  if (specialistMap[condition]) return specialistMap[condition];

  // Case-insensitive exact match
  const lower = condition.toLowerCase();
  for (const [key, specialist] of Object.entries(specialistMap)) {
    if (key.toLowerCase() === lower) return specialist;
  }

  // Keyword scan — find if the condition contains any known key substring
  for (const [key, specialist] of Object.entries(specialistMap)) {
    if (lower.includes(key.toLowerCase()) || key.toLowerCase().includes(lower)) {
      return specialist;
    }
  }

  return "General Physician";
}

/**
 * Returns de-duplicated specialist recommendations for a list of detected conditions.
 * Multiple conditions mapping to the same specialist are collapsed into one entry.
 */
export function getRecommendedSpecialists(
  conditions: string[]
): SpecialistRecommendation[] {
  const seen = new Set<string>();
  const results: SpecialistRecommendation[] = [];
  for (const condition of conditions) {
    if (!condition) continue;
    const specialist = getSpecialist(condition);
    const key = specialist.toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      results.push({ disease: condition, specialist });
    }
  }
  return results;
}
