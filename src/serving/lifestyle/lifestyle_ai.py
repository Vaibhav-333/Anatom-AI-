"""
lifestyle_ai.py — Gemini-powered lifestyle plan generation with fallback.

Pattern mirrors src/serving/care_connect/report_gen.py.
"""
from __future__ import annotations

import json
import os
from typing import Optional

# ── Fallback plan templates ───────────────────────────────────────────────────

_FALLBACK_PLANS: dict[str, dict] = {
    "recovery": {
        "meals": {
            "breakfast": [{"name": "Oats with banana", "description": "Rolled oats topped with sliced banana and honey",
                           "nutrition": {"calories": 320, "protein_g": 9, "carbs_g": 58, "fat_g": 6, "fiber_g": 5},
                           "prep_time_min": 10}],
            "lunch": [{"name": "Dal khichdi", "description": "Moong dal and rice cooked soft with turmeric and ghee",
                       "nutrition": {"calories": 420, "protein_g": 16, "carbs_g": 70, "fat_g": 8, "fiber_g": 6},
                       "prep_time_min": 25}],
            "dinner": [{"name": "Vegetable soup with toast", "description": "Light mixed vegetable broth with whole wheat toast",
                        "nutrition": {"calories": 280, "protein_g": 8, "carbs_g": 42, "fat_g": 5, "fiber_g": 7},
                        "prep_time_min": 20}],
            "snacks": [{"name": "Coconut water + banana", "description": "Rehydration snack with natural electrolytes",
                        "nutrition": {"calories": 160, "protein_g": 2, "carbs_g": 38, "fat_g": 0, "fiber_g": 3},
                        "prep_time_min": 2}],
        },
        "daily_nutrition": {"calories": 1180, "protein_g": 35, "carbs_g": 208, "fat_g": 19, "fiber_g": 21},
        "exercises": [
            {"name": "Gentle morning walk", "duration_min": 15, "intensity": "light",
             "instructions": "Walk at a comfortable pace outdoors or indoors. Stop if fatigued."},
            {"name": "Seated deep breathing", "duration_min": 10, "intensity": "light",
             "instructions": "Inhale 4 counts, hold 4, exhale 6. Repeat 10 cycles."},
        ],
        "avoid_list": ["Fried foods", "Alcohol", "Caffeine excess", "Raw salads (if digestion is weak)", "Spicy foods"],
        "preventive_care": [
            "Rest for at least 8 hours per night.",
            "Stay hydrated — minimum 2.5 litres of water daily.",
            "Avoid strenuous activity until pain levels drop below 4.",
            "Monitor temperature twice daily.",
        ],
        "ai_notes": "Recovery plan prioritises easily digestible, anti-inflammatory foods and minimal physical strain.",
    },
    "fitness": {
        "meals": {
            "breakfast": [{"name": "Paneer bhurji with multigrain roti", "description": "Scrambled paneer with bell peppers and 2 rotis",
                           "nutrition": {"calories": 480, "protein_g": 28, "carbs_g": 42, "fat_g": 18, "fiber_g": 6},
                           "prep_time_min": 15}],
            "lunch": [{"name": "Rajma rice bowl", "description": "Kidney bean curry over brown rice with raita",
                       "nutrition": {"calories": 580, "protein_g": 24, "carbs_g": 88, "fat_g": 10, "fiber_g": 12},
                       "prep_time_min": 30}],
            "dinner": [{"name": "Tofu stir-fry with quinoa", "description": "Pan-seared tofu with mixed vegetables over quinoa",
                        "nutrition": {"calories": 460, "protein_g": 26, "carbs_g": 52, "fat_g": 14, "fiber_g": 9},
                        "prep_time_min": 25}],
            "snacks": [{"name": "Greek yogurt with nuts", "description": "High-protein snack between meals",
                        "nutrition": {"calories": 220, "protein_g": 16, "carbs_g": 18, "fat_g": 8, "fiber_g": 2},
                        "prep_time_min": 2}],
        },
        "daily_nutrition": {"calories": 1740, "protein_g": 94, "carbs_g": 200, "fat_g": 50, "fiber_g": 29},
        "exercises": [
            {"name": "Brisk walk or jog", "duration_min": 30, "intensity": "moderate",
             "instructions": "Maintain a pace where you can hold a conversation but feel challenged."},
            {"name": "Bodyweight circuit", "duration_min": 20, "intensity": "moderate",
             "instructions": "3 rounds: 10 squats, 10 push-ups, 15 crunches, 30s plank. Rest 60s between rounds."},
            {"name": "Evening yoga flow", "duration_min": 20, "intensity": "light",
             "instructions": "Sun salutation x5, warrior poses, child's pose cooldown."},
        ],
        "avoid_list": ["Processed snacks", "Sugary drinks", "Trans fats", "Late-night heavy meals"],
        "preventive_care": [
            "Warm up for 5 minutes before every workout.",
            "Stretch and cool down after exercise.",
            "Track protein intake — aim for 1.2g per kg body weight.",
        ],
        "ai_notes": "Fitness plan balances strength and endurance with high-protein vegetarian nutrition.",
    },
    "chronic_management": {
        "meals": {
            "breakfast": [{"name": "Moong dal chilla", "description": "Protein-rich lentil pancakes with mint chutney",
                           "nutrition": {"calories": 340, "protein_g": 18, "carbs_g": 48, "fat_g": 7, "fiber_g": 8},
                           "prep_time_min": 20}],
            "lunch": [{"name": "Palak tofu sabzi with roti", "description": "Spinach and tofu curry with 2 whole wheat rotis",
                       "nutrition": {"calories": 460, "protein_g": 22, "carbs_g": 58, "fat_g": 12, "fiber_g": 10},
                       "prep_time_min": 30}],
            "dinner": [{"name": "Vegetable barley soup", "description": "Anti-inflammatory barley and mixed vegetable soup",
                        "nutrition": {"calories": 310, "protein_g": 10, "carbs_g": 52, "fat_g": 4, "fiber_g": 9},
                        "prep_time_min": 35}],
            "snacks": [{"name": "Handful of walnuts + apple", "description": "Omega-3 and fibre-rich afternoon snack",
                        "nutrition": {"calories": 240, "protein_g": 5, "carbs_g": 28, "fat_g": 14, "fiber_g": 5},
                        "prep_time_min": 1}],
        },
        "daily_nutrition": {"calories": 1350, "protein_g": 55, "carbs_g": 186, "fat_g": 37, "fiber_g": 32},
        "exercises": [
            {"name": "Chair yoga", "duration_min": 20, "intensity": "light",
             "instructions": "Seated twists, neck rolls, ankle circles. Gentle range-of-motion exercises."},
            {"name": "Short outdoor walk", "duration_min": 20, "intensity": "light",
             "instructions": "Flat ground preferred. Stop if pain exceeds 5/10. Aim for consistency over intensity."},
        ],
        "avoid_list": ["Processed foods", "High-sodium foods", "Refined sugar", "Alcohol", "Red meat"],
        "preventive_care": [
            "Maintain a consistent daily routine — wake, eat, and sleep at the same times.",
            "Track symptom changes after meals to identify food triggers.",
            "Keep emergency medication accessible at all times.",
            "Schedule regular check-ins with your treating physician.",
        ],
        "ai_notes": "Chronic management plan focuses on anti-inflammatory foods, low-impact movement, and routine stability.",
    },
}


async def generate_lifestyle_plan(
    goal: str,
    dietary_pref: str,
    restrictions: list[str],
    activity_level: str,
    symptom_trend: Optional[str],
    avg_pain: Optional[float],
    user_profile: Optional[dict],
) -> tuple[dict, bool]:
    """
    Returns (plan_dict, auto_adjusted).
    auto_adjusted=True when activity_level was downgraded due to worsening trend.
    """
    auto_adjusted = False

    # Auto-adjustment: if worsening + high activity, drop to light
    if symptom_trend == "worsening" and activity_level in ("moderate", "heavy"):
        activity_level = "light"
        auto_adjusted = True

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key or len(api_key) < 10:
        return _FALLBACK_PLANS.get(goal, _FALLBACK_PLANS["recovery"]), auto_adjusted

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        restriction_str = ", ".join(restrictions) if restrictions else "none"
        profile_str = ""
        if user_profile:
            profile_str = (
                f"User profile: age={user_profile.get('age','unknown')}, "
                f"conditions={user_profile.get('conditions','[]')}."
            )

        prompt = f"""You are a certified nutritionist and fitness coach. Generate a one-day lifestyle plan.

Goal: {goal}
Dietary preference: {dietary_pref}
Restrictions: {restriction_str}
Activity level: {activity_level}
Symptom trend: {symptom_trend or 'stable'}
Average pain score (0-10): {avg_pain if avg_pain is not None else 'unknown'}
{profile_str}

Return ONLY valid JSON with this exact structure (no markdown, no explanation):
{{
  "meals": {{
    "breakfast": [{{"name": "string", "description": "string", "nutrition": {{"calories": int, "protein_g": float, "carbs_g": float, "fat_g": float, "fiber_g": float}}, "prep_time_min": int}}],
    "lunch": [...],
    "dinner": [...],
    "snacks": [...]
  }},
  "daily_nutrition": {{"calories": int, "protein_g": float, "carbs_g": float, "fat_g": float, "fiber_g": float}},
  "exercises": [{{"name": "string", "duration_min": int, "intensity": "light|moderate|heavy", "instructions": "string"}}],
  "avoid_list": ["string"],
  "preventive_care": ["string"],
  "ai_notes": "string"
}}

Rules:
- Vegetarian meals unless dietary_pref specifies otherwise
- For recovery/worsening: prioritise light exercises only
- Include 3-5 avoid_list items relevant to the goal and restrictions
- Include 3-4 preventive_care tips
- All meals should be practical, Indian-context friendly, and nutritious"""

        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        plan = json.loads(text.strip())
        return plan, auto_adjusted

    except Exception:
        return _FALLBACK_PLANS.get(goal, _FALLBACK_PLANS["recovery"]), auto_adjusted
