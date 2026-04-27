"""
database.py — Async SQLite connection and schema initialisation for Anatom-AI.

Tables
------
profiles       — persistent user health profiles
health_scores  — append-only score history for trend tracking (Phase 6)

Usage
-----
    from src.serving.database import init_db, get_db

    # On startup:
    await init_db()

    # In a request handler:
    async with get_db() as db:
        await db.execute("SELECT ...", ...)
"""

from __future__ import annotations

import aiosqlite
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

DATABASE_PATH = Path("data/anatom_ai.db")

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_CREATE_PROFILES = """
CREATE TABLE IF NOT EXISTS profiles (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    age          INTEGER,
    gender       TEXT,
    height_cm    REAL,
    weight_kg    REAL,
    blood_type   TEXT,
    conditions   TEXT DEFAULT '[]',
    medications  TEXT DEFAULT '[]',
    health_score REAL DEFAULT 50.0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_HEALTH_SCORES = """
CREATE TABLE IF NOT EXISTS health_scores (
    id        TEXT PRIMARY KEY,
    user_id   TEXT REFERENCES profiles(id),
    score     REAL,
    date      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    report_id TEXT
);
"""

_CREATE_REPORTS = """
CREATE TABLE IF NOT EXISTS reports (
    id               TEXT PRIMARY KEY,
    user_id          TEXT,
    file_name        TEXT,
    file_type        TEXT,
    report_type      TEXT DEFAULT 'unknown',
    interpretation   TEXT,
    guidance         TEXT,
    affected_regions TEXT DEFAULT '[]',
    risk_level       TEXT DEFAULT 'low',
    file_hash        TEXT,
    upload_date      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


_CREATE_CARE_REPORTS = """
CREATE TABLE IF NOT EXISTS care_reports (
    id                       TEXT PRIMARY KEY,
    user_id                  TEXT NOT NULL,
    created_at               DATETIME DEFAULT CURRENT_TIMESTAMP,
    symptoms                 TEXT NOT NULL DEFAULT '[]',
    user_age                 INTEGER,
    user_gender              TEXT,
    medical_history          TEXT DEFAULT '[]',
    severity                 TEXT DEFAULT 'moderate',
    duration_days            INTEGER DEFAULT 1,
    probable_conditions      TEXT DEFAULT '[]',
    affected_organs          TEXT DEFAULT '[]',
    risk_level               TEXT DEFAULT 'low',
    red_flags                TEXT DEFAULT '[]',
    next_steps               TEXT DEFAULT '[]',
    treatment_suggestions    TEXT DEFAULT '[]',
    recommended_specialization TEXT,
    ai_raw_response          TEXT,
    pdf_path                 TEXT
);
"""

_CREATE_DOCTORS = """
CREATE TABLE IF NOT EXISTS doctors (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    specialization    TEXT NOT NULL,
    subspecialties    TEXT DEFAULT '[]',
    experience_years  INTEGER DEFAULT 0,
    rating            REAL DEFAULT 4.0,
    review_count      INTEGER DEFAULT 0,
    consultation_fee  INTEGER DEFAULT 500,
    mode              TEXT DEFAULT 'both',
    hospital          TEXT,
    city              TEXT DEFAULT 'Delhi',
    latitude          REAL,
    longitude         REAL,
    availability      TEXT DEFAULT '{}',
    verified          INTEGER DEFAULT 0,
    profile_image     TEXT,
    degrees           TEXT DEFAULT '[]',
    languages         TEXT DEFAULT '["Hindi","English"]',
    about             TEXT
);
"""

_CREATE_SHARED_REPORTS = """
CREATE TABLE IF NOT EXISTS shared_reports (
    token           TEXT PRIMARY KEY,
    report_id       TEXT NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at      DATETIME NOT NULL,
    view_count      INTEGER DEFAULT 0,
    last_viewed_at  DATETIME,
    is_revoked      INTEGER DEFAULT 0
);
"""

_CREATE_SAVED_DOCTORS = """
CREATE TABLE IF NOT EXISTS saved_doctors (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    TEXT NOT NULL,
    doctor_id  TEXT NOT NULL,
    saved_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, doctor_id)
);
"""

_CREATE_REPORT_VIEWS = """
CREATE TABLE IF NOT EXISTS report_views (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    token      TEXT NOT NULL,
    viewed_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    viewer_ip  TEXT
);
"""

# ── Health Tracker tables ────────────────────────────────────────────────────

_CREATE_HT_SYMPTOM_LOGS = """
CREATE TABLE IF NOT EXISTS ht_symptom_logs (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    logged_at       DATETIME NOT NULL,
    date_key        TEXT NOT NULL,
    pain_level      INTEGER,
    fever_celsius   REAL,
    fatigue         TEXT,
    mood            INTEGER,
    sleep_hours     REAL,
    custom_symptoms TEXT NOT NULL DEFAULT '[]',
    notes           TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_HT_SYMPTOM_LOGS_IDX = """
CREATE INDEX IF NOT EXISTS idx_ht_sl_user_date ON ht_symptom_logs(user_id, date_key);
"""

_CREATE_HT_MEDICATIONS = """
CREATE TABLE IF NOT EXISTS ht_medications (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    name            TEXT NOT NULL,
    dosage          TEXT NOT NULL,
    frequency       TEXT NOT NULL,
    duration_days   INTEGER,
    start_date      TEXT NOT NULL,
    end_date        TEXT,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_HT_MEDICATIONS_IDX = """
CREATE INDEX IF NOT EXISTS idx_ht_med_user ON ht_medications(user_id, active);
"""

_CREATE_HT_MEDICATION_LOGS = """
CREATE TABLE IF NOT EXISTS ht_medication_logs (
    id              TEXT PRIMARY KEY,
    medication_id   TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    scheduled_for   DATETIME NOT NULL,
    taken_at        DATETIME,
    status          TEXT NOT NULL DEFAULT 'pending',
    date_key        TEXT NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_HT_MED_LOGS_IDX1 = """
CREATE INDEX IF NOT EXISTS idx_ht_ml_user_date ON ht_medication_logs(user_id, date_key);
"""

_CREATE_HT_MED_LOGS_IDX2 = """
CREATE INDEX IF NOT EXISTS idx_ht_ml_med ON ht_medication_logs(medication_id);
"""

_CREATE_HT_WEEKLY_SCORES = """
CREATE TABLE IF NOT EXISTS ht_weekly_scores (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    week_key        TEXT NOT NULL,
    score           REAL NOT NULL DEFAULT 0.0,
    symptom_avg     REAL,
    adherence_pct   REAL,
    sleep_avg       REAL,
    trend           TEXT DEFAULT 'stable',
    streak_days     INTEGER DEFAULT 0,
    badges          TEXT DEFAULT '[]',
    computed_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, week_key)
);
"""

_CREATE_HT_LIFESTYLE_PLANS = """
CREATE TABLE IF NOT EXISTS ht_lifestyle_plans (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    goal            TEXT NOT NULL,
    dietary_pref    TEXT NOT NULL DEFAULT 'vegetarian',
    restrictions    TEXT NOT NULL DEFAULT '[]',
    activity_level  TEXT NOT NULL,
    plan_date       TEXT NOT NULL,
    meal_plan       TEXT NOT NULL DEFAULT '{}',
    exercise_plan   TEXT NOT NULL DEFAULT '{}',
    avoid_list      TEXT NOT NULL DEFAULT '[]',
    preventive_care TEXT NOT NULL DEFAULT '[]',
    ai_notes        TEXT,
    generated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_HT_LIFESTYLE_IDX = """
CREATE INDEX IF NOT EXISTS idx_ht_lp_user ON ht_lifestyle_plans(user_id, plan_date);
"""

# ── Auth System tables ────────────────────────────────────────────────────────

_CREATE_AUTH_USERS = """
CREATE TABLE IF NOT EXISTS auth_users (
    id                   TEXT PRIMARY KEY,
    username             TEXT NOT NULL UNIQUE,
    password_hash        TEXT NOT NULL,
    email                TEXT UNIQUE,
    phone                TEXT UNIQUE,
    email_verified       INTEGER NOT NULL DEFAULT 0,
    phone_verified       INTEGER NOT NULL DEFAULT 0,
    health_profile_done  INTEGER NOT NULL DEFAULT 0,
    is_locked            INTEGER NOT NULL DEFAULT 0,
    locked_until         DATETIME,
    failed_attempts      INTEGER NOT NULL DEFAULT 0,
    last_login           DATETIME,
    created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_AUTH_USERS_IDX = """
CREATE INDEX IF NOT EXISTS idx_au_username ON auth_users(username);
"""

_CREATE_AUTH_OTPS = """
CREATE TABLE IF NOT EXISTS auth_otps (
    id           TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    otp_hash     TEXT NOT NULL,
    purpose      TEXT NOT NULL,
    contact_type TEXT NOT NULL,
    contact_val  TEXT NOT NULL,
    attempts     INTEGER NOT NULL DEFAULT 0,
    used         INTEGER NOT NULL DEFAULT 0,
    expires_at   DATETIME NOT NULL,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_AUTH_OTPS_IDX = """
CREATE INDEX IF NOT EXISTS idx_ao_user_purpose ON auth_otps(user_id, purpose, used);
"""

_CREATE_AUTH_SESSIONS = """
CREATE TABLE IF NOT EXISTS auth_sessions (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    refresh_token TEXT NOT NULL UNIQUE,
    device_info   TEXT,
    ip_address    TEXT,
    is_revoked    INTEGER NOT NULL DEFAULT 0,
    expires_at    DATETIME NOT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_AUTH_SESSIONS_IDX = """
CREATE INDEX IF NOT EXISTS idx_as_refresh ON auth_sessions(refresh_token, is_revoked);
"""

_CREATE_AUTH_PASSWORD_HISTORY = """
CREATE TABLE IF NOT EXISTS auth_password_history (
    id           TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    password_hash TEXT NOT NULL,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_AUTH_HEALTH_PROFILES = """
CREATE TABLE IF NOT EXISTS auth_health_profiles (
    id                  TEXT PRIMARY KEY,
    user_id             TEXT NOT NULL UNIQUE REFERENCES auth_users(id) ON DELETE CASCADE,
    age                 INTEGER,
    gender              TEXT,
    height_cm           REAL,
    weight_kg           REAL,
    blood_group         TEXT,
    conditions          TEXT NOT NULL DEFAULT '[]',
    allergies           TEXT NOT NULL DEFAULT '[]',
    smoking             INTEGER NOT NULL DEFAULT 0,
    alcohol             TEXT NOT NULL DEFAULT 'none',
    activity_level      TEXT NOT NULL DEFAULT 'moderate',
    family_history      TEXT NOT NULL DEFAULT '[]',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


# ── AI Copilot tables ─────────────────────────────────────────────────────────

_CREATE_COPILOT_CONVERSATIONS = """
CREATE TABLE IF NOT EXISTS copilot_conversations (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    report_id   TEXT,
    title       TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_COPILOT_CONVERSATIONS_IDX = """
CREATE INDEX IF NOT EXISTS idx_cc_user ON copilot_conversations(user_id, updated_at);
"""

_CREATE_COPILOT_MESSAGES = """
CREATE TABLE IF NOT EXISTS copilot_messages (
    id                TEXT PRIMARY KEY,
    conversation_id   TEXT NOT NULL REFERENCES copilot_conversations(id) ON DELETE CASCADE,
    role              TEXT NOT NULL,
    content           TEXT NOT NULL,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_COPILOT_MESSAGES_IDX = """
CREATE INDEX IF NOT EXISTS idx_cm_conv ON copilot_messages(conversation_id, created_at);
"""

_REPORTS_MIGRATIONS = [
    "ALTER TABLE reports ADD COLUMN triage_data TEXT",
    "ALTER TABLE reports ADD COLUMN knowledge_graph_data TEXT",
    "ALTER TABLE reports ADD COLUMN personalized_insights TEXT DEFAULT '[]'",
    "ALTER TABLE reports ADD COLUMN triage_level TEXT",
    "ALTER TABLE reports ADD COLUMN diagnosis_data TEXT",
]


async def init_db() -> None:
    """Create the data directory and initialise all tables."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(_CREATE_PROFILES)
        await db.execute(_CREATE_HEALTH_SCORES)
        await db.execute(_CREATE_REPORTS)
        await db.execute(_CREATE_CARE_REPORTS)
        await db.execute(_CREATE_DOCTORS)
        await db.execute(_CREATE_SHARED_REPORTS)
        await db.execute(_CREATE_SAVED_DOCTORS)
        await db.execute(_CREATE_REPORT_VIEWS)
        # Health Tracker tables
        await db.execute(_CREATE_HT_SYMPTOM_LOGS)
        await db.execute(_CREATE_HT_SYMPTOM_LOGS_IDX)
        await db.execute(_CREATE_HT_MEDICATIONS)
        await db.execute(_CREATE_HT_MEDICATIONS_IDX)
        await db.execute(_CREATE_HT_MEDICATION_LOGS)
        await db.execute(_CREATE_HT_MED_LOGS_IDX1)
        await db.execute(_CREATE_HT_MED_LOGS_IDX2)
        await db.execute(_CREATE_HT_WEEKLY_SCORES)
        await db.execute(_CREATE_HT_LIFESTYLE_PLANS)
        await db.execute(_CREATE_HT_LIFESTYLE_IDX)
        # Auth system tables
        await db.execute(_CREATE_AUTH_USERS)
        await db.execute(_CREATE_AUTH_USERS_IDX)
        await db.execute(_CREATE_AUTH_OTPS)
        await db.execute(_CREATE_AUTH_OTPS_IDX)
        await db.execute(_CREATE_AUTH_SESSIONS)
        await db.execute(_CREATE_AUTH_SESSIONS_IDX)
        await db.execute(_CREATE_AUTH_PASSWORD_HISTORY)
        await db.execute(_CREATE_AUTH_HEALTH_PROFILES)
        # AI Copilot tables
        await db.execute(_CREATE_COPILOT_CONVERSATIONS)
        await db.execute(_CREATE_COPILOT_CONVERSATIONS_IDX)
        await db.execute(_CREATE_COPILOT_MESSAGES)
        await db.execute(_CREATE_COPILOT_MESSAGES_IDX)
        # Migrations: add new columns to existing tables (idempotent)
        for migration_sql in _REPORTS_MIGRATIONS:
            try:
                await db.execute(migration_sql)
            except Exception:
                pass  # Column already exists — SQLite raises OperationalError
        await db.commit()


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Yield an open aiosqlite connection with row_factory set."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
