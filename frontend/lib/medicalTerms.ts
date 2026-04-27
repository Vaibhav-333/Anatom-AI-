/**
 * medicalTerms.ts — Medical term → Wikipedia slug dictionary.
 *
 * Used by LinkedMedicalText to auto-link recognised medical terms in report
 * text to their Wikipedia articles. Entries are keyed by the display term
 * (any capitalisation — matching is case-insensitive) and valued by the
 * Wikipedia article slug.
 *
 * Guidelines:
 *  - Include only meaningful, unambiguous medical terms
 *  - Prefer the most specific Wikipedia article available
 *  - Max ~8 links rendered per text block (enforced in LinkedMedicalText)
 */

export const MEDICAL_TERMS: Record<string, string> = {
  // Cardiovascular
  "arrhythmia": "Arrhythmia",
  "atrial fibrillation": "Atrial_fibrillation",
  "bradycardia": "Bradycardia",
  "tachycardia": "Tachycardia",
  "hypertension": "Hypertension",
  "hypotension": "Hypotension",
  "coronary artery disease": "Coronary_artery_disease",
  "myocardial infarction": "Myocardial_infarction",
  "heart failure": "Heart_failure",
  "cardiomyopathy": "Cardiomyopathy",
  "hypertrophic cardiomyopathy": "Hypertrophic_cardiomyopathy",
  "angina": "Angina_pectoris",
  "pericarditis": "Pericarditis",
  "aortic stenosis": "Aortic_stenosis",
  "deep vein thrombosis": "Deep_vein_thrombosis",
  "pulmonary embolism": "Pulmonary_embolism",

  // Endocrine & Metabolic
  "diabetes mellitus": "Diabetes_mellitus",
  "type 2 diabetes": "Type_2_diabetes",
  "type 1 diabetes": "Type_1_diabetes",
  "hypothyroidism": "Hypothyroidism",
  "hyperthyroidism": "Hyperthyroidism",
  "hypercholesterolemia": "Hypercholesterolemia",
  "dyslipidemia": "Dyslipidemia",
  "metabolic syndrome": "Metabolic_syndrome",
  "obesity": "Obesity",
  "insulin resistance": "Insulin_resistance",

  // Respiratory
  "asthma": "Asthma",
  "pneumonia": "Pneumonia",
  "chronic obstructive pulmonary disease": "Chronic_obstructive_pulmonary_disease",
  "copd": "Chronic_obstructive_pulmonary_disease",
  "tuberculosis": "Tuberculosis",
  "bronchitis": "Bronchitis",
  "pleuritis": "Pleuritis",
  "sleep apnea": "Sleep_apnea",

  // Renal & Hepatic
  "chronic kidney disease": "Chronic_kidney_disease",
  "acute kidney injury": "Acute_kidney_injury",
  "nephrolithiasis": "Kidney_stone_disease",
  "liver cirrhosis": "Liver_cirrhosis",
  "hepatitis": "Hepatitis",
  "fatty liver": "Non-alcoholic_fatty_liver_disease",
  "non-alcoholic fatty liver disease": "Non-alcoholic_fatty_liver_disease",

  // Haematology
  "anemia": "Anemia",
  "anaemia": "Anemia",
  "sickle cell disease": "Sickle_cell_disease",
  "thalassemia": "Thalassemia",
  "leukemia": "Leukemia",
  "lymphoma": "Lymphoma",
  "thrombocytopenia": "Thrombocytopenia",
  "polycythemia": "Polycythemia",

  // Neurology
  "stroke": "Stroke",
  "migraine": "Migraine",
  "epilepsy": "Epilepsy",
  "parkinson's disease": "Parkinson%27s_disease",
  "alzheimer's disease": "Alzheimer%27s_disease",
  "multiple sclerosis": "Multiple_sclerosis",
  "neuropathy": "Peripheral_neuropathy",

  // Musculoskeletal
  "osteoporosis": "Osteoporosis",
  "osteoarthritis": "Osteoarthritis",
  "rheumatoid arthritis": "Rheumatoid_arthritis",
  "gout": "Gout",
  "scoliosis": "Scoliosis",
  "herniated disc": "Spinal_disc_herniation",

  // GI
  "gerd": "Gastroesophageal_reflux_disease",
  "gastroesophageal reflux disease": "Gastroesophageal_reflux_disease",
  "irritable bowel syndrome": "Irritable_bowel_syndrome",
  "crohn's disease": "Crohn%27s_disease",
  "ulcerative colitis": "Ulcerative_colitis",
  "peptic ulcer": "Peptic_ulcer_disease",
  "celiac disease": "Coeliac_disease",
  "pancreatitis": "Pancreatitis",

  // Lab values / biomarkers
  "troponin": "Troponin",
  "creatinine": "Creatinine",
  "hemoglobin": "Hemoglobin",
  "haemoglobin": "Hemoglobin",
  "hba1c": "Glycated_hemoglobin",
  "ldl": "Low-density_lipoprotein",
  "hdl": "High-density_lipoprotein",
  "triglycerides": "Triglyceride",
  "tsh": "Thyroid-stimulating_hormone",
  "d-dimer": "D-dimer",
  "crp": "C-reactive_protein",
  "c-reactive protein": "C-reactive_protein",
  "bun": "Blood_urea_nitrogen",
  "ferritin": "Ferritin",

  // Organs
  "myocardium": "Myocardium",
  "pericardium": "Pericardium",
  "thyroid": "Thyroid",
  "pancreas": "Pancreas",
  "spleen": "Spleen",
  "adrenal gland": "Adrenal_gland",

  // Procedures
  "ecg": "Electrocardiography",
  "electrocardiogram": "Electrocardiography",
  "echocardiogram": "Echocardiography",
  "mri": "Magnetic_resonance_imaging",
  "ct scan": "CT_scan",
  "endoscopy": "Endoscopy",
  "biopsy": "Biopsy",
  "angiography": "Angiography",
};

/**
 * Return all term keys sorted longest-first so that multi-word terms
 * (e.g. "atrial fibrillation") are matched before single-word subsets
 * (e.g. "fibrillation").
 */
export const SORTED_TERMS: string[] = Object.keys(MEDICAL_TERMS).sort(
  (a, b) => b.length - a.length
);
