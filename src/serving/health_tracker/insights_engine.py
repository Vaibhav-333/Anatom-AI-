"""
insights_engine.py — Pure-Python rule-based analytics for the Health Tracker.

No external API calls. All functions operate on lists of dicts fetched from
ht_symptom_logs and ht_medication_logs. Designed to be fast (<50ms).
"""
from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.serving.health_tracker.models import InsightAlert, InsightsResponse


# ── Trend Classification ──────────────────────────────────────────────────────

def _moving_avg(series: list[float], window: int = 3) -> list[float]:
    result = []
    for i in range(len(series)):
        start = max(0, i - window + 1)
        result.append(sum(series[start : i + 1]) / (i - start + 1))
    return result


def classify_trend(pain_series: list[float]) -> str:
    if len(pain_series) < 4:
        return "stable"
    smoothed = _moving_avg(pain_series, 3)
    mid = len(smoothed) // 2
    first_avg = sum(smoothed[:mid]) / mid
    second_avg = sum(smoothed[mid:]) / len(smoothed[mid:])
    if second_avg < first_avg * 0.85:
        return "improving"
    if second_avg > first_avg * 1.15:
        return "worsening"
    return "stable"


# ── Anomaly Detection ─────────────────────────────────────────────────────────

def detect_anomalies(logs: list[dict]) -> list[InsightAlert]:
    alerts: list[InsightAlert] = []
    if not logs:
        return alerts

    pain_values = [r["pain_level"] for r in logs if r.get("pain_level") is not None]
    fever_values = [(r["date_key"], r["fever_celsius"]) for r in logs if r.get("fever_celsius") is not None]
    sleep_values = [r["sleep_hours"] for r in logs if r.get("sleep_hours") is not None]
    mood_values = [r["mood"] for r in logs if r.get("mood") is not None]

    # PAIN_SPIKE: current entry pain > 7, previous 2-day avg < 5
    if len(pain_values) >= 3 and pain_values[-1] > 7:
        prev_avg = sum(pain_values[-3:-1]) / 2
        if prev_avg < 5:
            alerts.append(InsightAlert(
                type="anomaly", severity="warning",
                title="Pain spike detected",
                message=f"Pain jumped to {pain_values[-1]}/10 against a recent average of {prev_avg:.1f}.",
                metric="pain_level",
            ))

    # FEVER_HIGH: any entry > 38.5°C
    high_fever = [(dk, f) for dk, f in fever_values if f > 38.5]
    if high_fever:
        alerts.append(InsightAlert(
            type="anomaly", severity="critical",
            title="High fever detected",
            message=f"Fever reached {high_fever[-1][1]:.1f}°C on {high_fever[-1][0]}. Seek medical advice.",
            metric="fever_celsius",
        ))

    # FEVER_SUSTAINED: fever > 37.5 for 3+ consecutive days
    sustained = [f for _, f in fever_values if f > 37.5]
    if len(sustained) >= 3:
        alerts.append(InsightAlert(
            type="deterioration", severity="critical",
            title="Sustained elevated temperature",
            message="Fever above 37.5°C for 3 or more consecutive days. Consult a doctor.",
            metric="fever_celsius",
        ))

    # SLEEP_DEFICIT: sleep < 5 for 3+ consecutive entries
    if len(sleep_values) >= 3 and all(s < 5 for s in sleep_values[-3:]):
        alerts.append(InsightAlert(
            type="anomaly", severity="warning",
            title="Chronic sleep deficit",
            message="Sleep below 5 hours for 3 consecutive days. Poor sleep worsens recovery.",
            metric="sleep_hours",
        ))

    # MOOD_DECLINE: mood <= 2 for 3+ consecutive entries
    if len(mood_values) >= 3 and all(m <= 2 for m in mood_values[-3:]):
        alerts.append(InsightAlert(
            type="anomaly", severity="warning",
            title="Sustained low mood",
            message="Mood rated 2 or below for 3 consecutive days. Consider speaking to someone.",
            metric="mood",
        ))

    return alerts


# ── Correlation Analysis ──────────────────────────────────────────────────────

def _pearson(x: list[float], y: list[float]) -> Optional[float]:
    n = len(x)
    if n < 7:
        return None
    mx, my = sum(x) / n, sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    den = math.sqrt(
        sum((xi - mx) ** 2 for xi in x) * sum((yi - my) ** 2 for yi in y)
    )
    return num / den if den else None


def compute_correlations(logs: list[dict]) -> list[str]:
    notes: list[str] = []
    pairs = [
        ("sleep_hours", "pain_level", "Poor sleep", "increased pain"),
        ("mood", "pain_level", "Better mood", "lower pain"),
        ("sleep_hours", "mood", "More sleep", "better mood"),
    ]
    for xa, ya, pos_label, neg_label in pairs:
        xs = [r[xa] for r in logs if r.get(xa) is not None and r.get(ya) is not None]
        ys = [r[ya] for r in logs if r.get(xa) is not None and r.get(ya) is not None]
        r = _pearson(xs, ys)
        if r is None or abs(r) < 0.45:
            continue
        direction = "correlates with" if r > 0 else "correlates with reduced"
        if xa == "sleep_hours" and ya == "pain_level":
            msg = (
                f"Poor sleep (r={r:.2f}) correlates with increased pain levels"
                if r < 0
                else f"More sleep (r={r:.2f}) correlates with lower pain levels"
            )
        elif xa == "mood" and ya == "pain_level":
            msg = (
                f"Better mood (r={r:.2f}) correlates with lower pain"
                if r < 0
                else f"Low mood (r={r:.2f}) correlates with higher pain"
            )
        else:
            msg = f"More sleep (r={r:.2f}) {direction} better mood"
        notes.append(msg)
    return notes


# ── Prediction ────────────────────────────────────────────────────────────────

def predict_next_3_days(
    pain_series: list[float], mood_series: list[float]
) -> dict:
    def _ma3(series: list[float], low: float, high: float) -> float:
        if not series:
            return (low + high) / 2
        window = series[-3:]
        val = sum(window) / len(window)
        return round(max(low, min(high, val)), 1)

    return {
        "pain": _ma3(pain_series, 0.0, 10.0),
        "mood": _ma3(mood_series, 1.0, 5.0),
    }


# ── Weekly Score ──────────────────────────────────────────────────────────────

def _sleep_bonus(avg_sleep: Optional[float]) -> float:
    if avg_sleep is None:
        return 0.0
    if avg_sleep >= 8.0:
        return 15.0
    if avg_sleep >= 7.0:
        return 10.0
    if avg_sleep >= 6.0:
        return 5.0
    return 0.0


def compute_weekly_score(
    symptom_logs: list[dict],
    medication_logs: list[dict],
    trend: str,
) -> tuple[float, list[str]]:
    score = 50.0
    badges: list[str] = []

    # Medication adherence
    total = len(medication_logs)
    taken = sum(1 for m in medication_logs if m.get("status") == "taken")
    adherence_pct = (taken / total * 100) if total > 0 else 100.0
    score += adherence_pct * 0.25

    # Pain component
    pain_vals = [r["pain_level"] for r in symptom_logs if r.get("pain_level") is not None]
    avg_pain = sum(pain_vals) / len(pain_vals) if pain_vals else 5.0
    score += max(0.0, (10 - avg_pain) * 2.0)

    # Sleep quality bonus
    sleep_vals = [r["sleep_hours"] for r in symptom_logs if r.get("sleep_hours") is not None]
    avg_sleep = sum(sleep_vals) / len(sleep_vals) if sleep_vals else None
    score += _sleep_bonus(avg_sleep)

    # Trend bonus
    if trend == "improving":
        score += 10.0
    elif trend == "worsening":
        score -= 10.0

    # Fever penalty
    fever_penalty_days = sum(
        1 for r in symptom_logs
        if r.get("fever_celsius") is not None and r["fever_celsius"] > 38.0
    )
    score -= fever_penalty_days * 5.0

    score = round(max(0.0, min(100.0, score)), 1)

    # Badge logic
    date_keys = sorted({r["date_key"] for r in symptom_logs})
    streak = _compute_streak(date_keys)
    if streak >= 30:
        badges.append("streak_30")
    elif streak >= 7:
        badges.append("streak_7")
    if adherence_pct >= 100 and total >= 7:
        badges.append("perfect_week")
    if avg_pain <= 1.0 and pain_vals:
        badges.append("pain_free")
    if avg_sleep is not None and avg_sleep >= 7.5:
        badges.append("early_bird")

    return score, badges


def _compute_streak(date_keys: list[str]) -> int:
    if not date_keys:
        return 0
    streak = 1
    for i in range(len(date_keys) - 1, 0, -1):
        d1 = datetime.strptime(date_keys[i], "%Y-%m-%d")
        d2 = datetime.strptime(date_keys[i - 1], "%Y-%m-%d")
        if (d1 - d2).days == 1:
            streak += 1
        else:
            break
    return streak


# ── Suggestions ───────────────────────────────────────────────────────────────

def generate_suggestions(
    trend: str,
    alerts: list[InsightAlert],
    adherence_pct: float,
    avg_sleep: Optional[float],
) -> list[str]:
    suggestions: list[str] = []
    severities = {a.severity for a in alerts}

    if "critical" in severities:
        suggestions.append("One or more critical symptoms detected — seek medical advice promptly.")
    if trend == "worsening":
        suggestions.append("Your symptoms are trending worse. Consider scheduling a doctor consultation.")
    if adherence_pct < 70:
        suggestions.append(f"Medication adherence is {adherence_pct:.0f}% — enable reminder nudges to stay on track.")
    if avg_sleep is not None and avg_sleep < 6:
        suggestions.append("Aim for 7–8 hours of sleep; chronic sleep deficit significantly worsens recovery.")
    if "warning" in severities and "critical" not in severities:
        suggestions.append("Some warning-level symptoms detected — monitor closely over the next 48 hours.")
    if not alerts and trend == "improving":
        suggestions.append("Great progress this week — keep up your routine and stay consistent.")
    if not suggestions:
        suggestions.append("No critical patterns detected. Keep logging daily for better insights.")
    return suggestions


# ── Orchestrator ──────────────────────────────────────────────────────────────

async def compute_insights(
    symptom_logs: list[dict],
    medication_logs: list[dict],
    weekly_score_row: Optional[dict],
) -> InsightsResponse:
    pain_series = [r["pain_level"] for r in symptom_logs if r.get("pain_level") is not None]
    mood_series = [r["mood"] for r in symptom_logs if r.get("mood") is not None]
    sleep_vals = [r["sleep_hours"] for r in symptom_logs if r.get("sleep_hours") is not None]
    avg_sleep = sum(sleep_vals) / len(sleep_vals) if sleep_vals else None

    trend = classify_trend(pain_series)
    alerts = detect_anomalies(symptom_logs)
    correlation_notes = compute_correlations(symptom_logs)
    prediction = predict_next_3_days(pain_series, mood_series)

    total_meds = len(medication_logs)
    taken_meds = sum(1 for m in medication_logs if m.get("status") == "taken")
    adherence_pct = (taken_meds / total_meds * 100) if total_meds > 0 else 100.0

    suggestions = generate_suggestions(trend, alerts, adherence_pct, avg_sleep)

    weekly_score = weekly_score_row["score"] if weekly_score_row else 50.0

    return InsightsResponse(
        trend=trend,
        weekly_score=weekly_score,
        alerts=alerts,
        suggestions=suggestions,
        correlation_notes=correlation_notes,
        prediction_next_3_days=prediction,
    )
