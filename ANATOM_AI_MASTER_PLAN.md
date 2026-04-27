# ANATOM-AI — Master Build Plan
## Full-Stack Medical Intelligence Platform

> **For Claude:** This file is your complete project bible. Read it entirely before touching any code. At the start of each session, re-evaluate the plan and look for ways to make each phase smarter, more polished, and more production-ready. Think beyond the spec — propose and implement improvements where you see them. The goal is not just "working software" but a genuinely impressive, delightful medical platform that feels like a real product.

---

## Project Identity

**Anatom-AI** = "Google Maps + Iron Man JARVIS + Your Doctor" for medical reports.

Any person uploads a medical document → gets a human-language explanation → sees their body in 3D with the affected area highlighted → receives a personalized action plan.

**Core principle:** Complex medical intelligence, delivered with radical simplicity.

---

## Project Location

```
C:\Users\Vaibhav\OneDrive\Desktop\NeuroMapper 3D Brain Tumor Segmentation & Volume Tracking\
```

> ⚠️ The `&` in the folder name causes shell issues. Always use PowerShell for running commands:
> ```powershell
> Set-Location 'C:\Users\Vaibhav\OneDrive\Desktop\NeuroMapper 3D Brain Tumor Segmentation & Volume Tracking\frontend'
> ```
> Or use node directly:
> ```
> node "...\frontend\node_modules\next\dist\bin\next" dev
> ```

---

## Existing Codebase (NEVER BREAK THESE)

### Python Backend — `src/`
| Module | Path | Purpose |
|--------|------|---------|
| FastAPI app | `src/serving/api.py` | REST API — v5.0.0 after Phase 1 edits |
| Pydantic schemas | `src/serving/schemas.py` | ArrayPayload, VolumeRequest/Response, etc. |
| 3D U-Net | `src/models/unet3d.py` | Brain tumor segmentation (19.1M params) |
| Volumetrics | `src/analytics/volumetrics.py` | NCR/ED/ET/WT/TC volume computation |
| Longitudinal | `src/analytics/longitudinal.py` | RANO growth tracking |
| Radiomics | `src/analytics/radiomics.py` | 35+ shape/texture features |
| Risk scoring | `src/analytics/recurrence_risk.py` | 0-100 heuristic risk model |
| Trajectory | `src/analytics/trajectory_planner.py` | Surgical path planning |
| PyVista renderer | `src/ui/pyvista_renderer.py` | Off-screen 3D PNG rendering |
| PDF reports | `src/reporting/pdf_report.py` | ReportLab clinical PDFs |
| DICOM SR | `src/reporting/dicom_sr.py` | DICOM structured report export |
| Narrative | `src/reporting/narrative_report.py` | Jinja2 AI narrative |
| MRI pipeline | `src/imaging/` | Full preprocessing (N4, registration, skull-strip) |

### Existing API Endpoints (DO NOT CHANGE)
```
GET  /health
POST /analyze/volume
POST /analyze/longitudinal
POST /report/pdf
POST /report/dicom
POST /plan/trajectory
```
CORS already configured for `localhost:3000`.

### Frontend — `frontend/`
Built in Phase 1 (Next.js 14 + TypeScript + Tailwind + React Three Fiber)

```
frontend/
├── app/
│   ├── layout.tsx          ← Root layout (Sidebar + TopBar + AnimatedGrid)
│   ├── page.tsx            ← Dashboard
│   ├── upload/page.tsx     ← Upload & AI interpret
│   ├── viewer/page.tsx     ← 3D body viewer (R3F)
│   ├── results/[id]/page.tsx ← Report detail
│   ├── profile/page.tsx    ← Health profile
│   └── history/page.tsx    ← Report history
├── components/
│   ├── ui/                 ← GlassCard, MetricRow, StatusBadge/RiskBadge/SeverityBadge,
│   │                          AlertBox, NeonButton, PageHeader/SectionDivider, ValueHighlight
│   ├── layout/             ← Sidebar, TopBar, AnimatedGrid
│   ├── body-viewer/        ← BodyViewer3D (R3F canvas), HumanBodyModel (procedural),
│   │                          OrganInfoPanel, SystemToggle (stub)
│   └── report/             ← (stub — build in Phase 3+)
├── lib/
│   ├── types.ts            ← All TypeScript interfaces
│   ├── api.ts              ← FastAPI axios client
│   └── utils.ts            ← BMI, health score, formatters, localStorage helpers
├── next.config.mjs         ← Proxy: /api/* → http://localhost:8000/*
└── tailwind.config.ts      ← Custom tokens: navy, cyan, green, amber, red
```

### Design System (ALWAYS FOLLOW)
```
Palette:    navy (#0A0F1E bg), cyan (#00D4FF accent), green (#00FF88 success)
            amber (#FFB800 warning), red (#FF3B3B danger)
Typography: Inter (body), JetBrains Mono (data/code), Rajdhani (display/headers)
Style:      Glassmorphism panels, animated grid background, neon glow effects
            Scanline overlay, depth peeling aesthetic
Components: glass-panel class, btn-primary/secondary/danger, badge-* classes
```

---

## Running the App

```powershell
# Terminal 1 — Python backend
cd 'C:\Users\Vaibhav\OneDrive\Desktop\NeuroMapper 3D Brain Tumor Segmentation & Volume Tracking'
python scripts/serve.py

# Terminal 2 — Next.js frontend
powershell -Command "Set-Location '...frontend'; node node_modules\next\dist\bin\next dev"
# → http://localhost:3000
```

---

## Full 7-Phase Roadmap

---

### ✅ PHASE 1 — COMPLETE: Modern Frontend
**Goal:** Replace Streamlit with Next.js 14 dark-theme web app

**Status:** Done. Build passes. Dev server runs.
- All 6 pages built and styled
- Design system (Tailwind tokens, glass panels, neon accents)
- 3D body viewer with procedural anatomy (React Three Fiber)
- FastAPI proxy + CORS configured

---

### 🔲 PHASE 2 — User Health Profile System
**Session start prompt:** "Build Phase 2 of Anatom-AI — User Health Profile System"

**Goal:** Persistent user profiles with SQLite backend + health scoring

#### Backend files to create:
```
src/serving/database.py          ← aiosqlite connection + schema creation
src/serving/profile_manager.py   ← CRUD for user profiles
```

#### Backend schema (SQLite at `data/anatom_ai.db`):
```sql
CREATE TABLE IF NOT EXISTS profiles (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    age         INTEGER,
    gender      TEXT,
    height_cm   REAL,
    weight_kg   REAL,
    blood_type  TEXT,
    conditions  TEXT DEFAULT '[]',
    medications TEXT DEFAULT '[]',
    health_score REAL DEFAULT 50.0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS health_scores (
    id        TEXT PRIMARY KEY,
    user_id   TEXT REFERENCES profiles(id),
    score     REAL,
    date      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    report_id TEXT
);
```

#### API endpoints to add to `src/serving/api.py`:
```python
POST   /profile              ← create or update profile
GET    /profile/{user_id}    ← get profile with computed health score
DELETE /profile/{user_id}    ← delete profile and all data
```

#### Pydantic schemas to add to `src/serving/schemas.py`:
```python
class ProfileRequest(BaseModel):
    user_id: str
    name: str
    age: int
    gender: str
    height_cm: float
    weight_kg: float
    blood_type: Optional[str]
    conditions: List[str] = []
    medications: List[str] = []

class ProfileResponse(BaseModel):
    id: str
    name: str
    age: int
    gender: str
    height_cm: float
    weight_kg: float
    blood_type: Optional[str]
    conditions: List[str]
    medications: List[str]
    health_score: float
    bmi: float
    metabolic_age: int
    created_at: str
    updated_at: str
```

#### Frontend: wire `profile/page.tsx` to backend
- The profile page already exists and saves to `localStorage`
- Now: on save, POST to `/api/profile` and persist to DB
- On load: GET from `/api/profile/{userId}` if backend available, else fallback to localStorage
- Health score returned from backend (computed server-side, not just client-side)

#### Health score formula (server-side, `src/serving/profile_manager.py`):
```python
def compute_health_score(age, bmi, conditions, medications) -> float:
    score = 80.0
    # BMI adjustments
    if bmi < 18.5: score -= 8
    elif bmi >= 25 and bmi < 30: score -= 6
    elif bmi >= 30 and bmi < 35: score -= 14
    elif bmi >= 35: score -= 22
    else: score += 5  # normal BMI bonus
    # Age factor
    if age > 60: score -= 6
    elif age > 45: score -= 3
    elif age < 30: score += 5
    # Conditions
    score -= len(conditions) * 5
    # Medications (mild penalty — managing conditions)
    score -= len(medications) * 2
    return max(5.0, min(100.0, round(score, 1)))
```

#### Enhancement ideas Claude should consider:
- Add a health trend sparkline to the profile page showing score over time
- Add a "Health Age" calculation that compares metabolic age vs chronological age
- Add a visual body silhouette that adjusts proportionally to height/weight BMI
- Add condition severity ratings (mild/moderate/severe) for more accurate scoring
- Persist profile hash to detect changes and only POST when actually changed

---

### 🔲 PHASE 3 — AI Medical Report Interpreter (Gemini API)
**Session start prompt:** "Build Phase 3 of Anatom-AI — AI Medical Report Interpreter with Gemini"

**Goal:** Gemini 1.5 Flash multimodal document analysis

#### Backend files to create:
```
src/serving/ai_interpreter.py    ← Gemini API wrapper + prompt engineering
src/serving/report_history.py    ← SQLite CRUD for uploaded reports
```

#### SQLite table to add:
```sql
CREATE TABLE IF NOT EXISTS reports (
    id              TEXT PRIMARY KEY,
    user_id         TEXT REFERENCES profiles(id),
    file_name       TEXT,
    file_type       TEXT,
    report_type     TEXT,
    interpretation  TEXT,  -- JSON
    guidance        TEXT,  -- JSON (null until Phase 5)
    affected_regions TEXT DEFAULT '[]',
    risk_level      TEXT DEFAULT 'low',
    pdf_path        TEXT,
    upload_date     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### API endpoints to add:
```python
POST /interpret                  ← multipart: file + user_id + mode ("simple"|"doctor")
GET  /history/{user_id}          ← list of ReportSummary
GET  /history/{user_id}/{report_id}  ← full ReportDetail
DELETE /history/{user_id}/{report_id}
```

#### Gemini Integration (`src/serving/ai_interpreter.py`):
```python
import google.generativeai as genai

SIMPLE_PROMPT = """
You are a compassionate medical report interpreter. Analyze the attached document.
The patient wants a simple, empathetic explanation — no medical jargon.

Return a JSON object with exactly these fields:
{
  "summary": "Plain-language summary (2-3 sentences, empathetic tone)",
  "findings": [
    {"text": "description", "severity": "normal|borderline|critical", 
     "value": "123", "unit": "mg/dL", "reference_range": "70-100"}
  ],
  "affected_regions": ["brain", "liver", "kidneys"],  // body region IDs
  "confidence": 0.85,  // 0.0 to 1.0
  "reasoning": "Why the AI flagged specific items...",
  "report_type": "blood_report|brain_mri|xray|ct|ultrasound|unknown",
  "risk_level": "low|moderate|high|critical"
}

Valid affected_region IDs: brain, heart, lungs, liver, kidneys, spine, stomach
"""

DOCTOR_PROMPT = """
You are a clinical decision support system analyzing a medical document.
Provide a clinical-grade interpretation.

Return JSON with:
{
  "summary": "Clinical summary with differential diagnosis hints",
  "findings": [...],  // same structure, clinical terminology
  "affected_regions": [...],
  "confidence": 0.0-1.0,
  "reasoning": "Clinical reasoning...",
  "report_type": "...",
  "risk_level": "..."
}
"""
```

#### Key implementation notes:
- Use `google.generativeai` SDK (`pip install google-generativeai`)
- API key from env: `GEMINI_API_KEY` (never hardcode)
- Model: `gemini-1.5-flash` (free tier: 15 RPM, 1M TPD)
- For PDFs: upload file as `genai.upload_file()` then reference in message
- For images: base64 encode and pass as inline image data
- Use `response_mime_type="application/json"` for structured output
- Validate JSON response before returning — fallback to error response if malformed

#### Enhancement ideas Claude should consider:
- Add a "second opinion" button that re-runs with a different prompt temperature
- Cache Gemini responses by file hash to avoid re-analyzing the same document
- Add severity upgrade logic: if 3+ borderline findings → auto-upgrade risk to "moderate"
- Generate a human-readable confidence explanation ("Very confident — clear biomarker values found")
- Auto-detect if uploaded file is a brain MRI and route to Anatom AI pipeline instead of Gemini

---

### ✅ PHASE 4 — COMPLETE: 3D Human Body Visualization (Upgrade)
**Session start prompt:** "Build Phase 4 of Anatom-AI — Enhanced 3D Body Visualization"

**Goal:** Upgrade the existing procedural body with proper organ highlighting + brain integration

**Current state:** Phase 1 built a procedural Three.js body (capsules + spheres). Phase 4 upgrades it.

#### Improvements to make:
1. **Better organ geometry:** Replace sphere blobs with more anatomically shaped meshes
   - Heart: two overlapping spheres slightly offset (bi-ventricular shape)
   - Lungs: two capsules tilted slightly outward
   - Liver: flattened irregular shape using BufferGeometry
   - Use `SmoothShadow` from drei for better lighting
2. **Glow rings:** Add animated `RingGeometry` halos around highlighted organs (pulsing cyan/red)
3. **Body system layers:** Implement the system toggle properly
   - `full` → show everything at 0.18 opacity shell + organs
   - `skeleton` → show bone-colored box meshes for vertebrae + ribs only
   - `cardiovascular` → highlight heart in red, dim everything else
   - `respiratory` → highlight lungs, add breathing animation
4. **Brain PNG integration:** When a brain MRI subject is loaded:
   - Show PyVista-rendered PNG in the head region using `useTexture` + `PlaneGeometry`
   - Add a floating indicator: "Brain MRI loaded — Anatom AI analysis active"
5. **Camera animation:** Smooth camera transitions between presets (use `useSpring` from framer-motion or lerp in `useFrame`)
6. **Confidence fog:** For critical regions, add a semi-transparent fog cloud:
   ```js
   // Low-opacity sphere with additive blending around flagged organ
   <mesh>
     <sphereGeometry args={[0.5, 16, 16]} />
     <meshBasicMaterial color="#FF3B3B" transparent opacity={0.08} blending={THREE.AdditiveBlending} />
   </mesh>
   ```

#### New files to create:
```
frontend/components/body-viewer/SystemToggle.tsx   ← proper system toggle UI
frontend/components/body-viewer/BrainViewer.tsx    ← PyVista PNG overlay in 3D scene
```

#### Backend: Brain render endpoint
```python
# Add to src/serving/api.py
@app.get("/render/brain/{subject_id}")
async def render_brain(subject_id: str, mode: str = "standard"):
    # Load segmentation from outputs/analytics/{subject_id}/
    # Call NeuroRenderer.render_combined()
    # Return PNG as StreamingResponse
```

#### Enhancement ideas Claude should consider:
- Add a "scan beam" animation — a horizontal plane that sweeps up/down the body like a medical scanner
- Add organ labels that appear on hover (drei `<Text>` component, fade in/out)
- Add a "disease propagation" animation for spreading conditions (expanding sphere)
- Consider loading a real GLTF body if a CC0 model is found; otherwise keep procedural as fallback
- Add WebGL2 post-processing: bloom effect on highlighted organs (from `@react-three/postprocessing`)

---

### ✅ PHASE 5 — Personalized Health Guidance Engine (COMPLETE)
**Session start prompt:** "Build Phase 5 of Anatom-AI — Health Guidance Engine"

**Goal:** AI-generated actionable health plans from report + profile

#### Backend files to create:
```
src/serving/health_guidance.py   ← Gemini structured guidance generation
```

#### API endpoint to add:
```python
POST /guidance   ← {report_id, user_id} → GuidanceResponse
```

#### Guidance schema:
```python
class ExerciseGuidance(BaseModel):
    recommended: List[str]
    avoid: List[str]
    frequency: str

class GuidanceResponse(BaseModel):
    immediate_actions: List[str]    # Next 24h
    weekly_plan: List[str]          # Next 7 days
    monthly_plan: List[str]         # Next 30 days
    diet_recommendations: List[str]
    exercise_guidance: ExerciseGuidance
    supplements: List[str]          # Clearly marked non-medical advice
    warning_signs: List[str]        # When to go to doctor urgently
    consequence_timeline: str       # "What happens if ignored"
    disclaimer: str
```

#### Gemini Guidance Prompt:
```
Given this patient profile: {profile_summary}
And this medical finding: {interpretation_summary}

Generate a structured health action plan. Be specific, practical, and empathetic.
Include dietary recommendations for their specific condition.
List exercises to do AND explicitly list what to avoid.
Give realistic warning signs that mean they should go to a doctor urgently.

Return JSON matching the GuidanceResponse schema exactly.
```

#### Frontend:
- Add `GuidancePanel` component to `components/report/GuidancePanel.tsx`
- Show 3-column layout: 24h / 7 days / 30 days action cards
- Wire the "Generate Guidance" button on results/[id]/page.tsx
- Cache guidance in SQLite so it doesn't re-generate on every view

#### Enhancement ideas Claude should consider:
- Add a "severity tier" to each guidance item (🔴 Critical / 🟡 Important / 🟢 Optional)
- Add a daily checklist that user can "check off" (state in localStorage)
- Add a calorie/nutrition breakdown for diet recommendations
- Generate a printable PDF summary of the guidance plan
- Add a "personalize further" button that lets user give feedback ("I'm vegetarian", "I can't exercise")

---

### 🔲 PHASE 6 — Report History & Longitudinal Tracking
**Session start prompt:** "Build Phase 6 of Anatom-AI — Report History and Longitudinal Tracking"

**Goal:** Multi-report timeline, comparison view, health score trends

#### Frontend components to create:
```
frontend/components/report/LongitudinalChart.tsx  ← Recharts trend line
frontend/components/report/ReportTimeline.tsx     ← vertical timeline
frontend/components/report/ComparisonView.tsx     ← side-by-side diff
```

#### Features:
1. **Health Journey Timeline:** Vertical timeline on `history/page.tsx`
   - Each report is a node on the timeline
   - Color-coded by risk level
   - Click node → expand to show findings summary
2. **Side-by-side comparison:** Select 2 reports → show delta
   - Findings that appeared, disappeared, or worsened
   - Color-coded delta arrows (↑ worse, ↓ better, → stable)
3. **Health score trend:** Recharts `<LineChart>` with cyan gradient
4. **Brain tumor RANO tracking:** For brain MRI reports, automatically use `/analyze/longitudinal` endpoint
5. **Export:** "Download Health Summary PDF" using existing `/report/pdf` endpoint extended with new sections

#### Enhancement ideas Claude should consider:
- Add a "projected trajectory" — if current trend continues, where will health score be in 6 months?
- Add a "milestone" system: "First report uploaded", "Health score improved 10 points"
- Allow user to add manual health events (doctor visit, surgery, medication change)
- Generate a "Year in Review" summary for the year's reports

---

### 🔲 PHASE 7 — Production Polish
**Session start prompt:** "Build Phase 7 of Anatom-AI — Production Polish"

**Goal:** PWA, multi-language, TTS, what-if simulator, share feature

#### Feature list (implement in this order):
1. **PWA:** `frontend/public/manifest.json` + service worker (Next.js built-in via `next-pwa`)
2. **Text-to-speech:** Web Speech API — "Listen" button on summaries and guidance
3. **Dark/light mode:** Already using Tailwind `dark:` — add a toggle that sets `class` on `<html>`
4. **Multi-language:** `react-i18next` + Gemini translation endpoint on backend
5. **What-if simulator:** "What if I improve my diet?" → re-run guidance with a modified profile
6. **Smart alerts:** Date-based reminders ("Your cholesterol test was 3 months ago — consider retesting")
7. **Share report:** Generate a shareable URL with anonymized summary (no PII)
8. **Keyboard shortcuts:** `Ctrl+U` → Upload, `Ctrl+/` → Help, `Esc` → Close panels

#### Enhancement ideas Claude should consider:
- Add an onboarding tutorial overlay (shadcn-style spotlight tour)
- Add a "health chatbot" sidebar powered by Gemini (ask questions about your reports)
- Add biometric device integration (Apple Health / Google Fit API)
- Add a symptom checker: "I have a headache and fever" → guided analysis
- Add a doctor-share feature: generate a clean PDF summary formatted for clinical use

---

## Technical Constraints (ALL PHASES)

- **NEVER** replace or break existing FastAPI endpoints at `src/serving/api.py`
- **NEVER** modify `src/models/`, `src/imaging/`, `src/analytics/`, `src/reporting/` (only extend)
- **NEVER** commit `.env` files or API keys
- **ALWAYS** read files before editing
- **ALWAYS** keep files under 500 lines (split if longer)
- **ALWAYS** run `npm run build` equivalent after frontend changes
- **ALWAYS** add a disclaimer to any AI-generated health content: "Not medical advice"
- API key setup: `GEMINI_API_KEY` in `.env` at project root (Python backend reads it)
- SQLite DB: `data/anatom_ai.db` (create `data/` dir if missing)
- File uploads: `data/uploads/{user_id}/` (sanitize filenames)

---

## Commands Reference

```bash
# Start backend
python scripts/serve.py
# → FastAPI at http://localhost:8000/docs

# Start frontend (PowerShell, handles & in path)
powershell -Command "Set-Location 'C:\Users\Vaibhav\OneDrive\Desktop\NeuroMapper 3D Brain Tumor Segmentation & Volume Tracking\frontend'; node node_modules\next\dist\bin\next dev"
# → Next.js at http://localhost:3000

# Build frontend (verify TypeScript)
node "...\frontend\node_modules\next\dist\bin\next" build

# Install new Python dependency
pip install <package> && pip freeze > requirements.txt

# Install new npm dependency  
cd frontend && npm install <package>
```

---

## New Phase Session Checklist

When starting a new phase session, Claude should:

1. **Read this file completely** before writing any code
2. **Read the relevant existing files** (api.py, schemas.py, relevant page files)
3. **Check git status** — understand what changed in the last session
4. **Look for improvements** — is there a smarter way to implement this phase?
5. **Plan before coding** — write a brief plan as a comment at the top of new files
6. **Build incrementally** — backend first, then wire frontend
7. **Test the build** — `npm run build` must pass before declaring done
8. **Update this file** — mark the phase as ✅ COMPLETE with what was built

---

## Claude's Mandate for Future Phases

> You are building a product people will actually use to understand their health. Every phase should feel like a feature you'd find in a polished consumer app — not a developer prototype.

When implementing each phase, ask yourself:
- **Would a non-technical user understand this?** If not, simplify.
- **Does this feel responsive and alive?** Add loading states, transitions, micro-animations.
- **Is the error state handled?** Never show raw error messages to users.
- **Is it accessible?** WCAG 2.1 AA — labels, contrast, keyboard nav.
- **Can it be improved beyond the spec?** Yes — propose and implement smart improvements.

Examples of going beyond the spec:
- Phase 2: Instead of just a health score number, add a visual gauge with animated fill
- Phase 3: Instead of just listing findings, add a "What does this mean for me?" expanding section
- Phase 4: Instead of static organ highlighting, add a pulse animation that draws attention
- Phase 5: Instead of generic guidance, ask the user for preferences first (vegetarian? no gym?)

**The spec is a floor, not a ceiling.**

---

## Dependency Versions (Phase 1 Frozen)

```json
// frontend/package.json key deps
"next": "14.x",
"react": "^18.3.1",
"react-dom": "^18.3.1",
"@react-three/fiber": "^8.x",
"@react-three/drei": "^9.x",
"three": "^0.167.x",
"framer-motion": "latest",
"lucide-react": "latest",
"axios": "latest",
"recharts": "latest",
"react-hook-form": "latest",
"@hookform/resolvers": "latest",
"zod": "latest",
"clsx": "latest",
"tailwind-merge": "latest"
```

```
# requirements.txt key deps (Python)
fastapi
uvicorn
pydantic>=2.0
aiosqlite         ← ADD for Phase 2
google-generativeai  ← ADD for Phase 3
python-multipart  ← ADD for Phase 3 (file uploads)
pyvista>=0.44
torch>=2.1
pyradiomics
reportlab
pydicom
nibabel
numpy
scipy
```

---

*Last updated: Phases 1–4 complete.*
*Next: Phase 5 — Personalized Health Guidance Engine*
