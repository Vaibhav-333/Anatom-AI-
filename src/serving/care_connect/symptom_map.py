"""Symptom → condition → specialization mapping logic."""
from __future__ import annotations

# Maps keywords found in symptoms/conditions to medical specializations
SYMPTOM_SPECIALIZATION_MAP: dict[str, str] = {
    # Neurology
    "headache": "Neurologist",
    "migraine": "Neurologist",
    "seizure": "Neurologist",
    "dizziness": "Neurologist",
    "numbness": "Neurologist",
    "tremor": "Neurologist",
    "memory loss": "Neurologist",
    "stroke": "Neurologist",
    "brain": "Neurosurgeon",
    "brain tumor": "Neurosurgeon",
    "spinal cord": "Neurosurgeon",
    # Cardiology
    "chest pain": "Cardiologist",
    "palpitation": "Cardiologist",
    "irregular heartbeat": "Cardiologist",
    "heart": "Cardiologist",
    "hypertension": "Cardiologist",
    "high blood pressure": "Cardiologist",
    "shortness of breath": "Pulmonologist",
    # Pulmonology
    "cough": "Pulmonologist",
    "asthma": "Pulmonologist",
    "lung": "Pulmonologist",
    "breathing": "Pulmonologist",
    "wheezing": "Pulmonologist",
    "pneumonia": "Pulmonologist",
    # Gastroenterology
    "abdominal pain": "Gastroenterologist",
    "nausea": "Gastroenterologist",
    "vomiting": "Gastroenterologist",
    "diarrhea": "Gastroenterologist",
    "constipation": "Gastroenterologist",
    "stomach": "Gastroenterologist",
    "liver": "Gastroenterologist",
    "acid reflux": "Gastroenterologist",
    "bloating": "Gastroenterologist",
    # Orthopedics
    "joint pain": "Orthopedist",
    "back pain": "Orthopedist",
    "knee pain": "Orthopedist",
    "fracture": "Orthopedist",
    "bone": "Orthopedist",
    "arthritis": "Orthopedist",
    "shoulder pain": "Orthopedist",
    # Dermatology
    "skin rash": "Dermatologist",
    "itching": "Dermatologist",
    "acne": "Dermatologist",
    "eczema": "Dermatologist",
    "psoriasis": "Dermatologist",
    "hair loss": "Dermatologist",
    "skin": "Dermatologist",
    # Ophthalmology
    "vision": "Ophthalmologist",
    "eye pain": "Ophthalmologist",
    "blurry vision": "Ophthalmologist",
    "eye": "Ophthalmologist",
    # ENT
    "ear pain": "ENT Specialist",
    "sore throat": "ENT Specialist",
    "hearing loss": "ENT Specialist",
    "nasal congestion": "ENT Specialist",
    "tonsil": "ENT Specialist",
    "sinusitis": "ENT Specialist",
    # Psychiatry
    "anxiety": "Psychiatrist",
    "depression": "Psychiatrist",
    "insomnia": "Psychiatrist",
    "panic": "Psychiatrist",
    "mood": "Psychiatrist",
    # Endocrinology
    "diabetes": "Endocrinologist",
    "thyroid": "Endocrinologist",
    "weight gain": "Endocrinologist",
    "fatigue": "General Physician",
    "hormonal": "Endocrinologist",
    # Nephrology
    "kidney": "Nephrologist",
    "urinary": "Urologist",
    "frequent urination": "Urologist",
    # General
    "fever": "General Physician",
    "cold": "General Physician",
    "flu": "General Physician",
    "weakness": "General Physician",
}

CONDITION_SPECIALIZATION_MAP: dict[str, str] = {
    "migraine": "Neurologist",
    "brain tumor": "Neurosurgeon",
    "epilepsy": "Neurologist",
    "parkinson's disease": "Neurologist",
    "multiple sclerosis": "Neurologist",
    "coronary artery disease": "Cardiologist",
    "heart failure": "Cardiologist",
    "atrial fibrillation": "Cardiologist",
    "hypertension": "Cardiologist",
    "asthma": "Pulmonologist",
    "copd": "Pulmonologist",
    "pneumonia": "Pulmonologist",
    "tuberculosis": "Pulmonologist",
    "gerd": "Gastroenterologist",
    "ibs": "Gastroenterologist",
    "crohn's disease": "Gastroenterologist",
    "cirrhosis": "Gastroenterologist",
    "osteoarthritis": "Orthopedist",
    "rheumatoid arthritis": "Rheumatologist",
    "psoriasis": "Dermatologist",
    "eczema": "Dermatologist",
    "glaucoma": "Ophthalmologist",
    "cataract": "Ophthalmologist",
    "diabetes mellitus": "Endocrinologist",
    "hypothyroidism": "Endocrinologist",
    "hyperthyroidism": "Endocrinologist",
    "chronic kidney disease": "Nephrologist",
    "urinary tract infection": "Urologist",
    "depression": "Psychiatrist",
    "anxiety disorder": "Psychiatrist",
}


def get_specialization_from_symptoms(symptoms: list[str]) -> str:
    """Return the best-matching specialization for a list of symptoms."""
    scores: dict[str, int] = {}
    for symptom in symptoms:
        s_lower = symptom.lower()
        for keyword, spec in SYMPTOM_SPECIALIZATION_MAP.items():
            if keyword in s_lower:
                scores[spec] = scores.get(spec, 0) + 2
        # partial word match — lower weight
        for keyword, spec in SYMPTOM_SPECIALIZATION_MAP.items():
            if any(word in s_lower for word in keyword.split()):
                scores[spec] = scores.get(spec, 0) + 1
    if not scores:
        return "General Physician"
    return max(scores, key=lambda k: scores[k])


def get_specialization_from_conditions(conditions: list[str]) -> str:
    """Return best-matching specialization from condition names."""
    for condition in conditions:
        c_lower = condition.lower()
        for key, spec in CONDITION_SPECIALIZATION_MAP.items():
            if key in c_lower:
                return spec
    return "General Physician"


def resolve_specialization(symptoms: list[str], conditions: list[str]) -> str:
    """Combine symptom and condition signals to find the primary specialization."""
    from_conditions = get_specialization_from_conditions(conditions)
    if from_conditions != "General Physician":
        return from_conditions
    return get_specialization_from_symptoms(symptoms)
