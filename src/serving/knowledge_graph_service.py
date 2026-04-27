"""
knowledge_graph_service.py — Medical Knowledge Graph for Anatom-AI.

Builds a structured Disease → Organ → Symptom → Treatment graph for any
diagnosed condition. Uses a seeded dictionary for ~35 common conditions and
falls back to Gemini-generated graph data for unknown conditions.

Graph structure:
    Disease --[HAS_ORGAN]--> Organ
    Disease --[HAS_SYMPTOM]--> Symptom
    Disease --[HAS_TREATMENT]--> Treatment
    Symptom --[ASSOCIATED_WITH]--> Disease   (reverse link for exploration)

Architecture note: A Neo4jAdapter stub is included at the bottom. Swap
`_MockGraphAdapter` for `_Neo4jAdapter` in `build_knowledge_graph()` when a
Neo4j instance is available.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any

import google.generativeai as genai

# ---------------------------------------------------------------------------
# Seeded medical knowledge base
# ---------------------------------------------------------------------------

# Each entry: { "organs": [], "symptoms": [], "treatments": [] }
_MEDICAL_KB: dict[str, dict[str, list[str]]] = {
    "arrhythmia": {
        "organs": ["Heart"],
        "symptoms": ["Palpitations", "Dizziness", "Shortness of breath", "Chest discomfort", "Fatigue"],
        "treatments": ["ECG monitoring", "Antiarrhythmic medication", "Cardioversion", "Ablation therapy", "Pacemaker"],
    },
    "hypertension": {
        "organs": ["Heart", "Kidneys", "Blood vessels", "Brain"],
        "symptoms": ["Headache", "Blurred vision", "Nosebleed", "Shortness of breath", "Chest pain"],
        "treatments": ["ACE inhibitors", "Beta-blockers", "Diuretics", "Lifestyle modification", "Low-sodium diet"],
    },
    "diabetes mellitus": {
        "organs": ["Pancreas", "Kidneys", "Eyes", "Nerves"],
        "symptoms": ["Excessive thirst", "Frequent urination", "Fatigue", "Blurred vision", "Slow wound healing"],
        "treatments": ["Insulin therapy", "Metformin", "Dietary control", "Exercise", "Blood glucose monitoring"],
    },
    "type 2 diabetes": {
        "organs": ["Pancreas", "Kidneys", "Liver"],
        "symptoms": ["Excessive thirst", "Fatigue", "Frequent urination", "Blurred vision"],
        "treatments": ["Metformin", "Dietary modification", "Physical activity", "Insulin (if needed)", "Weight loss"],
    },
    "anemia": {
        "organs": ["Blood", "Bone marrow", "Spleen"],
        "symptoms": ["Fatigue", "Pale skin", "Shortness of breath", "Dizziness", "Cold hands and feet"],
        "treatments": ["Iron supplementation", "Vitamin B12 supplementation", "Folate supplementation", "Blood transfusion", "Dietary changes"],
    },
    "hypothyroidism": {
        "organs": ["Thyroid gland"],
        "symptoms": ["Fatigue", "Weight gain", "Cold intolerance", "Depression", "Dry skin", "Constipation"],
        "treatments": ["Levothyroxine", "Thyroid hormone replacement", "Regular TSH monitoring", "Dietary iodine adjustment"],
    },
    "hyperthyroidism": {
        "organs": ["Thyroid gland", "Heart"],
        "symptoms": ["Weight loss", "Rapid heartbeat", "Anxiety", "Heat intolerance", "Tremors"],
        "treatments": ["Antithyroid medications", "Radioactive iodine", "Beta-blockers", "Thyroidectomy"],
    },
    "coronary artery disease": {
        "organs": ["Heart", "Coronary arteries"],
        "symptoms": ["Chest pain (angina)", "Shortness of breath", "Heart palpitations", "Fatigue", "Sweating"],
        "treatments": ["Statins", "Aspirin", "Beta-blockers", "Angioplasty", "Coronary bypass surgery"],
    },
    "heart failure": {
        "organs": ["Heart", "Lungs", "Kidneys"],
        "symptoms": ["Breathlessness", "Leg swelling", "Fatigue", "Rapid heartbeat", "Reduced exercise tolerance"],
        "treatments": ["ACE inhibitors", "Diuretics", "Beta-blockers", "Cardiac resynchronization therapy", "Heart transplant"],
    },
    "asthma": {
        "organs": ["Lungs", "Airways"],
        "symptoms": ["Wheezing", "Coughing", "Chest tightness", "Shortness of breath"],
        "treatments": ["Bronchodilators (inhaler)", "Corticosteroids", "Leukotriene modifiers", "Allergy management", "Trigger avoidance"],
    },
    "chronic obstructive pulmonary disease": {
        "organs": ["Lungs", "Airways"],
        "symptoms": ["Chronic cough", "Excessive mucus", "Shortness of breath", "Wheezing", "Chest tightness"],
        "treatments": ["Bronchodilators", "Inhaled corticosteroids", "Oxygen therapy", "Pulmonary rehabilitation", "Smoking cessation"],
    },
    "copd": {
        "organs": ["Lungs", "Airways"],
        "symptoms": ["Chronic cough", "Shortness of breath", "Wheezing", "Fatigue"],
        "treatments": ["Bronchodilators", "Inhaled steroids", "Pulmonary rehabilitation", "Smoking cessation"],
    },
    "pneumonia": {
        "organs": ["Lungs"],
        "symptoms": ["Fever", "Cough with phlegm", "Chest pain", "Shortness of breath", "Fatigue"],
        "treatments": ["Antibiotics", "Antivirals", "Rest", "Hydration", "Oxygen therapy"],
    },
    "kidney disease": {
        "organs": ["Kidneys"],
        "symptoms": ["Swelling in ankles/feet", "Fatigue", "Reduced urination", "Shortness of breath", "Nausea"],
        "treatments": ["Blood pressure management", "Dietary protein restriction", "Dialysis", "Kidney transplant", "Diuretics"],
    },
    "chronic kidney disease": {
        "organs": ["Kidneys", "Heart"],
        "symptoms": ["Fatigue", "Swelling", "Reduced urination", "Nausea", "Itching"],
        "treatments": ["Blood pressure control", "Low-protein diet", "Dialysis", "Erythropoietin therapy", "Kidney transplant"],
    },
    "liver disease": {
        "organs": ["Liver", "Spleen"],
        "symptoms": ["Jaundice", "Abdominal pain", "Fatigue", "Nausea", "Loss of appetite"],
        "treatments": ["Alcohol abstinence", "Antiviral therapy", "Liver transplant", "Dietary modification", "Diuretics"],
    },
    "fatty liver disease": {
        "organs": ["Liver"],
        "symptoms": ["Fatigue", "Upper right abdominal discomfort", "Enlarged liver", "Nausea"],
        "treatments": ["Weight loss", "Exercise", "Dietary change", "Vitamin E supplementation", "Glucose control"],
    },
    "osteoporosis": {
        "organs": ["Bones", "Spine"],
        "symptoms": ["Back pain", "Height loss", "Bone fractures", "Stooped posture"],
        "treatments": ["Calcium supplementation", "Vitamin D", "Bisphosphonates", "Weight-bearing exercise", "Fall prevention"],
    },
    "arthritis": {
        "organs": ["Joints", "Cartilage"],
        "symptoms": ["Joint pain", "Swelling", "Stiffness", "Reduced range of motion"],
        "treatments": ["NSAIDs", "Physiotherapy", "Joint replacement surgery", "Corticosteroid injections", "Exercise"],
    },
    "rheumatoid arthritis": {
        "organs": ["Joints", "Synovium"],
        "symptoms": ["Symmetric joint pain", "Morning stiffness", "Fatigue", "Joint swelling"],
        "treatments": ["Methotrexate", "Biologic DMARDs", "Corticosteroids", "Physiotherapy", "NSAIDs"],
    },
    "depression": {
        "organs": ["Brain", "Nervous system"],
        "symptoms": ["Persistent sadness", "Fatigue", "Sleep disturbances", "Loss of appetite", "Concentration difficulty"],
        "treatments": ["Antidepressants (SSRIs)", "Psychotherapy", "CBT", "Exercise", "Lifestyle modification"],
    },
    "anxiety disorder": {
        "organs": ["Brain", "Nervous system"],
        "symptoms": ["Excessive worry", "Restlessness", "Rapid heartbeat", "Sweating", "Insomnia"],
        "treatments": ["SSRIs", "CBT", "Relaxation techniques", "Mindfulness", "Beta-blockers"],
    },
    "hypertrophic cardiomyopathy": {
        "organs": ["Heart", "Cardiac muscle"],
        "symptoms": ["Chest pain", "Shortness of breath", "Palpitations", "Fainting", "Fatigue"],
        "treatments": ["Beta-blockers", "Calcium channel blockers", "ICD implantation", "Septal myectomy", "Alcohol septal ablation"],
    },
    "atrial fibrillation": {
        "organs": ["Heart", "Left atrium"],
        "symptoms": ["Irregular heartbeat", "Palpitations", "Fatigue", "Dizziness", "Shortness of breath"],
        "treatments": ["Anticoagulants", "Rate control medication", "Rhythm control", "Cardioversion", "Ablation"],
    },
    "high cholesterol": {
        "organs": ["Blood vessels", "Heart", "Arteries"],
        "symptoms": ["Often asymptomatic", "Chest pain (if arteries blocked)", "Xanthomas"],
        "treatments": ["Statins", "Dietary modification", "Exercise", "Ezetimibe", "PCSK9 inhibitors"],
    },
    "hypercholesterolemia": {
        "organs": ["Blood vessels", "Heart"],
        "symptoms": ["Usually asymptomatic", "Corneal arcus", "Xanthelasma"],
        "treatments": ["Statins", "Dietary change", "Exercise", "Cholesterol absorption inhibitors"],
    },
    "gerd": {
        "organs": ["Esophagus", "Stomach"],
        "symptoms": ["Heartburn", "Acid reflux", "Chest discomfort", "Nausea", "Regurgitation"],
        "treatments": ["Proton pump inhibitors", "Antacids", "H2 blockers", "Dietary modification", "Elevated sleeping position"],
    },
    "irritable bowel syndrome": {
        "organs": ["Colon", "Small intestine"],
        "symptoms": ["Abdominal pain", "Bloating", "Diarrhea", "Constipation", "Cramping"],
        "treatments": ["Dietary changes (low FODMAP)", "Stress management", "Antispasmodics", "Probiotics", "Fiber supplementation"],
    },
    "migraine": {
        "organs": ["Brain", "Blood vessels"],
        "symptoms": ["Throbbing headache", "Nausea", "Sensitivity to light", "Sensitivity to sound", "Aura"],
        "treatments": ["Triptans", "NSAIDs", "Preventive medications", "Trigger avoidance", "Biofeedback"],
    },
    "obesity": {
        "organs": ["Adipose tissue", "Heart", "Joints", "Liver"],
        "symptoms": ["Excess body weight", "Breathlessness", "Joint pain", "Fatigue", "Sleep apnea"],
        "treatments": ["Caloric restriction", "Exercise program", "Behavioral therapy", "Bariatric surgery", "Medications"],
    },
    "sleep apnea": {
        "organs": ["Upper airway", "Brain", "Heart"],
        "symptoms": ["Loud snoring", "Gasping during sleep", "Morning headache", "Daytime sleepiness", "Difficulty concentrating"],
        "treatments": ["CPAP therapy", "Weight loss", "Positional therapy", "Oral appliance", "Surgery"],
    },
}

# ---------------------------------------------------------------------------
# Node / edge builders
# ---------------------------------------------------------------------------

def _make_node(label: str, node_type: str, description: str = "") -> dict[str, str]:
    return {
        "id": re.sub(r"\s+", "_", label.lower()),
        "label": label,
        "type": node_type,
        "description": description,
    }


def _make_edge(source_label: str, target_label: str, relation: str) -> dict[str, str]:
    return {
        "source": re.sub(r"\s+", "_", source_label.lower()),
        "target": re.sub(r"\s+", "_", target_label.lower()),
        "relation": relation,
    }


def _build_graph_from_kb(condition_name: str, kb_entry: dict) -> dict[str, Any]:
    nodes: list[dict] = [_make_node(condition_name, "disease")]
    edges: list[dict] = []

    for organ in kb_entry.get("organs", [])[:4]:
        nodes.append(_make_node(organ, "organ"))
        edges.append(_make_edge(condition_name, organ, "affects"))

    for symptom in kb_entry.get("symptoms", [])[:5]:
        nodes.append(_make_node(symptom, "symptom"))
        edges.append(_make_edge(condition_name, symptom, "causes"))

    for treatment in kb_entry.get("treatments", [])[:4]:
        nodes.append(_make_node(treatment, "treatment"))
        edges.append(_make_edge(condition_name, treatment, "treated_by"))

    return {
        "nodes": nodes,
        "edges": edges,
        "primary_condition": condition_name,
    }


# ---------------------------------------------------------------------------
# Gemini fallback for unknown conditions
# ---------------------------------------------------------------------------

_GRAPH_PROMPT = """\
You are a medical knowledge graph generator. Given a medical condition name,
output a structured JSON knowledge graph.

Condition: {condition}

Return ONLY valid JSON — no markdown, no extra text:
{{
  "organs": ["Organ1", "Organ2"],
  "symptoms": ["Symptom1", "Symptom2", "Symptom3", "Symptom4"],
  "treatments": ["Treatment1", "Treatment2", "Treatment3"]
}}

Rules:
- organs: 1-4 organs affected by this condition
- symptoms: 3-6 key symptoms
- treatments: 2-5 common treatments or management approaches
- Use plain medical terminology
- treatments: lifestyle and clinical (do not prescribe specific dosages)
"""


def _get_model() -> genai.GenerativeModel | None:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name="gemini-flash-lite-latest",
        generation_config={"response_mime_type": "application/json"},
    )


def _strip_json(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else text


async def _llm_build_graph(condition_name: str) -> dict[str, Any] | None:
    model = _get_model()
    if model is None:
        return None
    try:
        prompt = _GRAPH_PROMPT.format(condition=condition_name)
        response = model.generate_content(prompt)
        raw = json.loads(_strip_json(response.text))
        return {
            "organs": [str(o) for o in raw.get("organs", [])[:4]],
            "symptoms": [str(s) for s in raw.get("symptoms", [])[:5]],
            "treatments": [str(t) for t in raw.get("treatments", [])[:4]],
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Minimal fallback graph
# ---------------------------------------------------------------------------

def _minimal_graph(condition_name: str) -> dict[str, Any]:
    """Last-resort graph with only the disease node."""
    return {
        "nodes": [_make_node(condition_name, "disease")],
        "edges": [],
        "primary_condition": condition_name,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def build_knowledge_graph(
    conditions: list[dict],
) -> dict[str, Any]:
    """
    Build a medical knowledge graph for the top diagnosed condition.

    Args:
        conditions: List of probable_conditions dicts with 'name' and 'confidence_pct'.

    Returns:
        KnowledgeGraphData dict with keys: nodes, edges, primary_condition.
    """
    if not conditions:
        return {"nodes": [], "edges": [], "primary_condition": ""}

    # Take the highest-confidence condition
    top = sorted(conditions, key=lambda c: c.get("confidence_pct", 0), reverse=True)[0]
    condition_name = top.get("name", "Unknown")

    # Try exact match in KB
    kb_key = condition_name.lower().strip()
    if kb_key in _MEDICAL_KB:
        return _build_graph_from_kb(condition_name, _MEDICAL_KB[kb_key])

    # Try partial match (e.g. "Type 2 Diabetes Mellitus" → "diabetes mellitus")
    for kb_name, kb_entry in _MEDICAL_KB.items():
        if kb_name in kb_key or kb_key in kb_name:
            return _build_graph_from_kb(condition_name, kb_entry)

    # Fallback: ask Gemini
    llm_entry = await _llm_build_graph(condition_name)
    if llm_entry:
        return _build_graph_from_kb(condition_name, llm_entry)

    # Last resort
    return _minimal_graph(condition_name)


# ---------------------------------------------------------------------------
# Neo4j adapter stub (future integration)
# ---------------------------------------------------------------------------

class _Neo4jAdapter:
    """
    Stub for future Neo4j integration.
    Replace `build_knowledge_graph` with a version that calls this adapter.

    Usage:
        adapter = _Neo4jAdapter(uri="bolt://localhost:7687", user="neo4j", password="...")
        await adapter.connect()
        graph = await adapter.query_condition("Arrhythmia")
        await adapter.close()
    """

    def __init__(self, uri: str, user: str, password: str) -> None:
        self._uri = uri
        self._user = user
        self._password = password
        self._driver = None

    async def connect(self) -> None:
        try:
            from neo4j import AsyncGraphDatabase  # type: ignore
            self._driver = AsyncGraphDatabase.driver(
                self._uri, auth=(self._user, self._password)
            )
        except ImportError:
            raise RuntimeError("neo4j package not installed. Run: pip install neo4j")

    async def query_condition(self, condition: str) -> dict[str, Any]:
        if self._driver is None:
            raise RuntimeError("Call connect() first.")
        cypher = """
        MATCH (d:Disease {name: $name})
        OPTIONAL MATCH (d)-[:HAS_ORGAN]->(o:Organ)
        OPTIONAL MATCH (d)-[:HAS_SYMPTOM]->(s:Symptom)
        OPTIONAL MATCH (d)-[:HAS_TREATMENT]->(t:Treatment)
        RETURN d, collect(DISTINCT o) AS organs,
               collect(DISTINCT s) AS symptoms,
               collect(DISTINCT t) AS treatments
        """
        async with self._driver.session() as session:
            result = await session.run(cypher, name=condition)
            record = await result.single()
            if record is None:
                return _minimal_graph(condition)
            return _build_graph_from_kb(condition, {
                "organs": [r["name"] for r in record["organs"]],
                "symptoms": [r["name"] for r in record["symptoms"]],
                "treatments": [r["name"] for r in record["treatments"]],
            })

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
