"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Network, ChevronDown, ChevronUp } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { NeonButton } from "@/components/ui/NeonButton";
import type { KnowledgeGraphData, KnowledgeGraphNode, KnowledgeGraphEdge } from "@/lib/types";

// ── Embedded local medical knowledge base ───────────────────────────────────
// Mirrors the backend _MEDICAL_KB — always available, no network needed.

const _LOCAL_KB: Record<string, { organs: string[]; symptoms: string[]; treatments: string[] }> = {
  "hypertension": {
    organs: ["Heart", "Kidneys", "Blood vessels", "Brain"],
    symptoms: ["Headache", "Blurred vision", "Chest pain", "Shortness of breath", "Nosebleed"],
    treatments: ["ACE inhibitors", "Beta-blockers", "Diuretics", "Low-sodium diet", "Lifestyle changes"],
  },
  "hypertensive urgency": {
    organs: ["Heart", "Kidneys", "Blood vessels", "Brain"],
    symptoms: ["Severe headache", "Chest discomfort", "Blurred vision", "Dizziness", "Nausea"],
    treatments: ["Oral antihypertensives", "Blood pressure monitoring", "Urgent medical review", "Lifestyle changes"],
  },
  "essential hypertension": {
    organs: ["Heart", "Kidneys", "Blood vessels"],
    symptoms: ["Headache", "Dizziness", "Fatigue", "Blurred vision"],
    treatments: ["ACE inhibitors", "Beta-blockers", "Diuretics", "Dietary changes", "Exercise"],
  },
  "cardiovascular autonomic dysfunction": {
    organs: ["Heart", "Nervous system", "Blood vessels"],
    symptoms: ["Dizziness", "Palpitations", "Fainting", "Difficulty concentrating", "Fatigue"],
    treatments: ["Lifestyle adjustments", "Hydration", "Salt intake review", "Autonomic testing", "Specialist review"],
  },
  "arrhythmia": {
    organs: ["Heart"],
    symptoms: ["Palpitations", "Dizziness", "Shortness of breath", "Chest discomfort", "Fatigue"],
    treatments: ["ECG monitoring", "Antiarrhythmic medication", "Cardioversion", "Ablation therapy", "Pacemaker"],
  },
  "diabetes mellitus": {
    organs: ["Pancreas", "Kidneys", "Eyes", "Nerves"],
    symptoms: ["Excessive thirst", "Frequent urination", "Fatigue", "Blurred vision", "Slow wound healing"],
    treatments: ["Insulin therapy", "Metformin", "Dietary control", "Exercise", "Blood glucose monitoring"],
  },
  "type 2 diabetes": {
    organs: ["Pancreas", "Kidneys", "Liver"],
    symptoms: ["Excessive thirst", "Fatigue", "Frequent urination", "Blurred vision"],
    treatments: ["Metformin", "Dietary modification", "Physical activity", "Weight loss"],
  },
  "anemia": {
    organs: ["Blood", "Bone marrow", "Spleen"],
    symptoms: ["Fatigue", "Pale skin", "Shortness of breath", "Dizziness", "Cold hands"],
    treatments: ["Iron supplementation", "Vitamin B12", "Folate", "Blood transfusion", "Dietary changes"],
  },
  "hypothyroidism": {
    organs: ["Thyroid gland"],
    symptoms: ["Fatigue", "Weight gain", "Cold intolerance", "Depression", "Dry skin"],
    treatments: ["Levothyroxine", "Thyroid hormone replacement", "TSH monitoring"],
  },
  "coronary artery disease": {
    organs: ["Heart", "Coronary arteries"],
    symptoms: ["Chest pain", "Shortness of breath", "Palpitations", "Fatigue", "Sweating"],
    treatments: ["Statins", "Aspirin", "Beta-blockers", "Angioplasty", "Bypass surgery"],
  },
  "heart failure": {
    organs: ["Heart", "Lungs", "Kidneys"],
    symptoms: ["Breathlessness", "Leg swelling", "Fatigue", "Rapid heartbeat"],
    treatments: ["ACE inhibitors", "Diuretics", "Beta-blockers", "Cardiac resynchronization"],
  },
  "asthma": {
    organs: ["Lungs", "Airways"],
    symptoms: ["Wheezing", "Coughing", "Chest tightness", "Shortness of breath"],
    treatments: ["Bronchodilators", "Corticosteroids", "Allergy management", "Trigger avoidance"],
  },
  "copd": {
    organs: ["Lungs", "Airways"],
    symptoms: ["Chronic cough", "Shortness of breath", "Wheezing", "Fatigue"],
    treatments: ["Bronchodilators", "Inhaled steroids", "Pulmonary rehabilitation", "Smoking cessation"],
  },
  "high cholesterol": {
    organs: ["Blood vessels", "Heart", "Arteries"],
    symptoms: ["Often asymptomatic", "Chest pain if blocked"],
    treatments: ["Statins", "Dietary modification", "Exercise", "Cholesterol inhibitors"],
  },
  "depression": {
    organs: ["Brain", "Nervous system"],
    symptoms: ["Persistent sadness", "Fatigue", "Sleep disturbance", "Loss of appetite"],
    treatments: ["SSRIs", "Psychotherapy", "CBT", "Exercise", "Lifestyle changes"],
  },
  "anxiety disorder": {
    organs: ["Brain", "Nervous system"],
    symptoms: ["Excessive worry", "Restlessness", "Rapid heartbeat", "Sweating", "Insomnia"],
    treatments: ["SSRIs", "CBT", "Relaxation techniques", "Mindfulness", "Beta-blockers"],
  },
  "migraine": {
    organs: ["Brain", "Blood vessels"],
    symptoms: ["Throbbing headache", "Nausea", "Light sensitivity", "Sound sensitivity", "Aura"],
    treatments: ["Triptans", "NSAIDs", "Preventive medication", "Trigger avoidance"],
  },
  "obesity": {
    organs: ["Adipose tissue", "Heart", "Joints", "Liver"],
    symptoms: ["Excess body weight", "Breathlessness", "Joint pain", "Fatigue"],
    treatments: ["Caloric restriction", "Exercise program", "Behavioral therapy", "Bariatric surgery"],
  },
  "kidney disease": {
    organs: ["Kidneys"],
    symptoms: ["Swelling", "Fatigue", "Reduced urination", "Nausea"],
    treatments: ["Blood pressure control", "Low-protein diet", "Dialysis", "Kidney transplant"],
  },
  "atrial fibrillation": {
    organs: ["Heart", "Left atrium"],
    symptoms: ["Irregular heartbeat", "Palpitations", "Fatigue", "Dizziness", "Shortness of breath"],
    treatments: ["Anticoagulants", "Rate control medication", "Cardioversion", "Ablation"],
  },
};

const _makeId = (s: string) => s.toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, "");

function _buildLocalGraph(
  conditions: Array<{ name: string; confidence_pct: number }>
): KnowledgeGraphData | null {
  if (!conditions.length) return null;

  const top = [...conditions].sort((a, b) => b.confidence_pct - a.confidence_pct)[0];
  const name = top.name;
  const nameLower = name.toLowerCase().trim();

  // Exact match → partial match → generic
  let entry =
    _LOCAL_KB[nameLower] ??
    Object.entries(_LOCAL_KB).find(([k]) => nameLower.includes(k) || k.includes(nameLower))?.[1];

  if (!entry) {
    // Generic fallback so we always render something
    entry = {
      organs: ["Body system"],
      symptoms: ["Refer to clinical findings"],
      treatments: ["Seek medical evaluation", "Follow physician recommendations"],
    };
  }

  const nodes: KnowledgeGraphNode[] = [{ id: _makeId(name), label: name, type: "disease" }];
  const edges: KnowledgeGraphEdge[] = [];

  entry.organs.slice(0, 4).forEach((o) => {
    nodes.push({ id: _makeId(o), label: o, type: "organ" });
    edges.push({ source: _makeId(name), target: _makeId(o), relation: "affects" });
  });
  entry.symptoms.slice(0, 5).forEach((s) => {
    nodes.push({ id: _makeId(s), label: s, type: "symptom" });
    edges.push({ source: _makeId(name), target: _makeId(s), relation: "causes" });
  });
  entry.treatments.slice(0, 4).forEach((t) => {
    nodes.push({ id: _makeId(t), label: t, type: "treatment" });
    edges.push({ source: _makeId(name), target: _makeId(t), relation: "treated_by" });
  });

  return { nodes, edges, primary_condition: name };
}

// ── Node colour map ─────────────────────────────────────────────────────────

const NODE_COLORS: Record<KnowledgeGraphNode["type"], string> = {
  disease: "#22d3ee",    // cyan  — primary condition
  organ: "#f59e0b",      // amber — affected organs
  symptom: "#f87171",    // red   — symptoms
  treatment: "#34d399",  // green — treatments
};

const NODE_LABELS: Record<KnowledgeGraphNode["type"], string> = {
  disease: "Condition",
  organ: "Organ",
  symptom: "Symptom",
  treatment: "Treatment",
};

// ── SVG Graph renderer ──────────────────────────────────────────────────────

interface GraphViewProps {
  data: KnowledgeGraphData;
}

function GraphView({ data }: GraphViewProps) {
  const { nodes, edges } = data;

  // Layout: disease node centre, spokes by type
  const CENTER = { x: 280, y: 200 };
  const RADII: Record<KnowledgeGraphNode["type"], number> = {
    disease: 0,
    organ: 130,
    symptom: 145,
    treatment: 155,
  };
  const ANGLES: Record<KnowledgeGraphNode["type"], number> = {
    disease: 0,
    organ: -90,       // top-left quadrant
    symptom: 30,      // right quadrant
    treatment: 200,   // bottom-left quadrant
  };

  // Compute positions
  const typeCount: Record<string, number> = {};
  const typeIndex: Record<string, number> = {};

  nodes.forEach((n) => {
    if (n.type !== "disease") {
      typeCount[n.type] = (typeCount[n.type] || 0) + 1;
    }
  });

  const positions: Record<string, { x: number; y: number }> = {};

  nodes.forEach((n) => {
    if (n.type === "disease") {
      positions[n.id] = CENTER;
      return;
    }
    const idx = typeIndex[n.type] || 0;
    typeIndex[n.type] = idx + 1;
    const count = typeCount[n.type] || 1;
    const baseAngle = ANGLES[n.type] * (Math.PI / 180);
    const spread = count > 1 ? (Math.PI / 2.5) / (count - 1) : 0;
    const angle = baseAngle - (spread * (count - 1)) / 2 + spread * idx;
    const r = RADII[n.type];
    positions[n.id] = {
      x: CENTER.x + r * Math.cos(angle),
      y: CENTER.y + r * Math.sin(angle),
    };
  });

  // SVG dimensions
  const W = 560;
  const H = 400;

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        style={{ maxHeight: 360, minWidth: 320 }}
        aria-label="Medical knowledge graph"
      >
        {/* Edges */}
        {edges.map((edge, i) => {
          const from = positions[edge.source];
          const to = positions[edge.target];
          if (!from || !to) return null;
          const midX = (from.x + to.x) / 2;
          const midY = (from.y + to.y) / 2;
          return (
            <g key={i}>
              <line
                x1={from.x} y1={from.y}
                x2={to.x} y2={to.y}
                stroke="#334155"
                strokeWidth={1.5}
                strokeDasharray={edge.relation === "treats" ? "4 3" : undefined}
              />
              <text
                x={midX} y={midY - 4}
                textAnchor="middle"
                fontSize={8}
                fill="#475569"
                className="select-none"
              >
                {edge.relation}
              </text>
            </g>
          );
        })}

        {/* Nodes */}
        {nodes.map((node) => {
          const pos = positions[node.id];
          if (!pos) return null;
          const color = NODE_COLORS[node.type] || "#94a3b8";
          const r = node.type === "disease" ? 32 : 22;
          const fontSize = node.type === "disease" ? 10 : 8;
          const label = node.label.length > 18 ? node.label.slice(0, 16) + "…" : node.label;

          return (
            <g key={node.id}>
              {/* Glow ring for disease node */}
              {node.type === "disease" && (
                <circle
                  cx={pos.x} cy={pos.y} r={r + 6}
                  fill="none"
                  stroke={color}
                  strokeWidth={1}
                  strokeOpacity={0.2}
                />
              )}
              <circle
                cx={pos.x} cy={pos.y} r={r}
                fill={`${color}18`}
                stroke={color}
                strokeWidth={node.type === "disease" ? 2 : 1.5}
              />
              <text
                x={pos.x} y={pos.y - 2}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={fontSize}
                fontWeight={node.type === "disease" ? "600" : "400"}
                fill={color}
                className="select-none"
              >
                {label}
              </text>
              {/* Type label */}
              <text
                x={pos.x} y={pos.y + r + 12}
                textAnchor="middle"
                fontSize={7}
                fill="#475569"
                className="select-none"
              >
                {NODE_LABELS[node.type]}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ── Legend ──────────────────────────────────────────────────────────────────

function Legend() {
  const items: { type: KnowledgeGraphNode["type"]; label: string }[] = [
    { type: "disease", label: "Condition" },
    { type: "organ", label: "Organ" },
    { type: "symptom", label: "Symptom" },
    { type: "treatment", label: "Treatment" },
  ];
  return (
    <div className="flex flex-wrap gap-3 mt-3 pt-3 border-t border-glass-border">
      {items.map(({ type, label }) => (
        <div key={type} className="flex items-center gap-1.5">
          <span
            className="w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: NODE_COLORS[type] }}
          />
          <span className="text-xs text-slate-500">{label}</span>
        </div>
      ))}
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

interface KnowledgeGraphPanelProps {
  /** Pre-loaded graph data (from report object). If null, fetched lazily. */
  initialData?: KnowledgeGraphData | null;
  /** Conditions list for lazy fetch when initialData is not available. */
  conditions?: Array<{ name: string; confidence_pct: number }>;
}

export function KnowledgeGraphPanel({
  initialData,
  conditions,
}: KnowledgeGraphPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [graphData, setGraphData] = useState<KnowledgeGraphData | null>(() => {
    // Pre-compute locally on mount so expand is instant
    if (initialData) return initialData;
    if (conditions?.length) return _buildLocalGraph(conditions);
    return null;
  });

  const handleExpand = useCallback(() => {
    setExpanded((prev) => !prev);
    // Ensure we have graph data (handles cases where state was initialised null)
    if (!graphData && conditions?.length) {
      const local = _buildLocalGraph(conditions);
      if (local) setGraphData(local);
    }
  }, [graphData, conditions]);

  // Hide entirely if no data and no conditions to fetch
  if (!initialData && (!conditions || conditions.length === 0)) {
    return null;
  }

  return (
    <GlassCard>
      {/* Header / toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-cyan" />
          <div>
            <h3 className="section-title text-base">Medical Knowledge Graph</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Visualise condition → organs → symptoms → treatments
            </p>
          </div>
        </div>
        <NeonButton
          variant="cyan"
          size="sm"
          icon={
            expanded
              ? <ChevronUp className="w-3.5 h-3.5" />
              : <ChevronDown className="w-3.5 h-3.5" />
          }
          onClick={handleExpand}
        >
          {expanded ? "Collapse" : "View Medical Graph"}
        </NeonButton>
      </div>

      {/* Expandable panel */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            key="graph-panel"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="mt-4 pt-4 border-t border-glass-border">
              {graphData ? (
                <>
                  {/* Primary condition label */}
                  {graphData.primary_condition && (
                    <p className="text-xs text-slate-500 mb-3">
                      Showing graph for:{" "}
                      <span className="text-cyan font-medium">
                        {graphData.primary_condition}
                      </span>
                    </p>
                  )}

                  {graphData.nodes.length === 0 ? (
                    <p className="text-sm text-slate-500 text-center py-6">
                      No graph data available for this condition.
                    </p>
                  ) : (
                    <>
                      <GraphView data={graphData} />
                      <Legend />
                    </>
                  )}
                </>
              ) : (
                <p className="text-xs text-slate-500 text-center py-6">
                  No condition data available to build graph.
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </GlassCard>
  );
}
