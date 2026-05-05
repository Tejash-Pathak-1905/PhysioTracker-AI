"""
llm_client.py
-------------
Handles all communication with Google Gemini 2.5 Flash.
Uses the new `google-genai` SDK (google.generativeai is deprecated).

Responsibilities
----------------
1. Build a system-aware prompt from the user assessment + exercises catalogue.
2. Call the API in JSON mode.
3. Validate the returned JSON structure.
4. Filter out low-confidence items (confidence < 0.6) per PRD section 6.
5. Return a clean Python dict ready for database insertion.
"""

import json
import os
import logging
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)  # reads .env into os.environ

logger = logging.getLogger(__name__)

# ── Gemini configuration ─────────────────────────────────────────────────────

def _get_client() -> genai.Client:
    load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)  # Dynamically reload key
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. Add it to your .env file."
        )
    return genai.Client(api_key=api_key)


MODEL_ID = "models/gemini-2.5-flash"

# ── Prompt construction ──────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a qualified physiotherapy AI assistant.
Your job is to create a safe, personalised exercise programme for a patient based
on their reported injury/complaint and pain level.

IMPORTANT SAFETY RULES
- Never recommend exercises that would aggravate an acute injury.
- Always include a caution note if the exercise has any contraindication.
- Confidence must reflect how appropriate the exercise is for this patient's
  specific complaint (1.0 = perfect fit, 0.0 = contraindicated).
- Exercises with confidence < 0.6 will be automatically discarded by the backend.
- LATERALLY SPECIFIC INSTRUCTIONS: If the patient mentions a specific side (e.g., 'right knee', 'left shoulder'), and the exercise is marked as 'is_unilateral': true, you MUST specify the "side" as "left" or "right". If the exercise is bilateral (is_unilateral: false) or if you want them to do both sides for balance, use "both".

OUTPUT FORMAT
Return a single JSON object exactly matching this schema, no markdown, no extra keys:

{
  "understood_condition": "<Brief 1-2 sentence medical summary>",
  "user_summary": "<Friendly paragraph for the patient dashboard>",
  "programme": [
    {
      "exercise_id": "<must match an id from the catalogue>",
      "confidence": 0.85,
      "sets": 3,
      "reps": 10,
      "side": "right", 
      "caution": "<specific note or empty string>",
      "priority": 1
    }
  ]
}
"""


def _build_user_prompt(complaint: str, pain_level: int, past_records: str, exercises_catalogue: list, age: Optional[int] = None, gender: Optional[str] = None) -> str:
    catalogue_str = json.dumps(
        [{"id": e["id"], "name": e["name"], "description": e["description"], "is_unilateral": e.get("is_unilateral", False)}
         for e in exercises_catalogue],
        indent=2,
    )
    prompt_text = ""
    if age:
        prompt_text += f"Patient Age: {age}\n"
    if gender:
        prompt_text += f"Patient Gender: {gender}\n"
        
    prompt_text += (
        f"Patient complaint: {complaint}\n"
        f"Current pain level (1-10): {pain_level}\n"
    )
    if past_records and past_records.strip():
        prompt_text += f"Past Medical Records / Surgeries: {past_records.strip()}\n"
    
    prompt_text += (
        f"\nAvailable exercises catalogue:\n{catalogue_str}\n\n"
        "Generate an appropriate physiotherapy programme from the catalogue above. "
        "If a medical report or image is attached to the prompt, please analyze it carefully and incorporate its findings into your decision making."
    )
    return prompt_text


# ── Public API ───────────────────────────────────────────────────────────────

import time as _time

def generate_exercise_plan(
    complaint: str,
    pain_level: int,
    exercises_catalogue: list,
    confidence_threshold: float = 0.6,
    past_records: str = "",
    media_bytes: Optional[bytes] = None,
    media_mime: str = "",
    age: Optional[int] = None,
    gender: Optional[str] = None,
) -> Optional[dict]:
    """
    Calls Gemini and returns a validated, filtered plan dict.
    Returns None on API / parse failure.
    Retries up to 3 times with exponential backoff on transient errors.
    """
    client = _get_client()
    user_prompt = _build_user_prompt(complaint, pain_level, past_records, exercises_catalogue, age=age, gender=gender)
    full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"

    contents = [full_prompt]
    if media_bytes and media_mime:
        contents.append(
            types.Part.from_bytes(data=media_bytes, mime_type=media_mime)
        )

    model_ids = ["models/gemini-2.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-flash"]

    for model_id in model_ids:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.4,
                    ),
                )
                raw_text = response.text
                plan = json.loads(raw_text)

                required_keys = {"understood_condition", "user_summary", "programme"}
                if not required_keys.issubset(plan.keys()):
                    logger.error("LLM response missing required keys: %s", list(plan.keys()))
                    return None

                # Filter low-confidence exercises (PRD section 6)
                original_count = len(plan["programme"])
                plan["programme"] = [
                    item for item in plan["programme"]
                    if item.get("confidence", 0) >= confidence_threshold
                ]
                filtered_count = original_count - len(plan["programme"])
                if filtered_count:
                    logger.info("Filtered %d low-confidence exercise(s).", filtered_count)

                plan["programme"].sort(key=lambda x: x.get("priority", 99))
                plan["_raw_json"] = raw_text
                return plan

            except json.JSONDecodeError as exc:
                logger.error("Failed to parse Gemini JSON: %s", exc)
                return None
            except Exception as exc:
                msg = str(exc)
                if "503" in msg or "UNAVAILABLE" in msg or "429" in msg:
                    wait = 2 ** attempt
                    logger.warning("Transient API error (attempt %d), retrying in %ds: %s", attempt+1, wait, exc)
                    _time.sleep(wait)
                    continue
                logger.error("Gemini API call failed: %s", exc)
                return None

    logger.error("All retries exhausted across all model IDs.")
    return None


# ── Report Insights API ───────────────────────────────────────────────────────

REPORT_SYSTEM_PROMPT = """You are a qualified physiotherapy AI assistant generating a personalised progress report for a patient.
Your report must be empathetic, clear, and medically grounded. Use plain English – no jargon.
You will receive patient details and their session history data, then produce structured insights.

Return a single JSON object with this exact schema:
{
  "headline": "<1 sentence overall progress statement (positive but honest)>",
  "recovery_status": "<one of: 'On Track', 'Progressing Well', 'Needs Attention', 'Just Started'>",
  "progress_narrative": "<3-4 sentences explaining what the data shows in plain English, referencing their specific complaint>",
  "strongest_exercise": "<name of the exercise they performed best in, with a brief reason>",
  "needs_work": "<the exercise or area needing most improvement, with actionable advice>",
  "form_insight": "<specific insight about their form quality – what errors appeared most, what it means for their recovery>",
  "next_session_tip": "<1 concrete tip for their next session based on the data>",
  "motivational_message": "<short personalised motivational message tied to their specific injury/goal>",
  "consistency_advice": "<advice on their workout consistency pattern>",
  "caution_flag": "<any concern the therapist should know, or empty string if none>"
}
"""


def generate_report_insights(
    complaint: str,
    pain_level: int,
    sessions_summary: str,
    age: Optional[int] = None,
    gender: Optional[str] = None,
) -> Optional[dict]:
    """
    Calls Gemini to produce an AI-powered personalised report narrative.
    Returns a dict of insights or None on failure.
    """
    client = _get_client()

    user_prompt = ""
    if age:
        user_prompt += f"Patient Age: {age}\n"
    if gender:
        user_prompt += f"Patient Gender: {gender}\n"

    user_prompt += (
        f"Patient complaint: {complaint}\n"
        f"Initial pain level reported: {pain_level}/10\n\n"
        f"Session data summary:\n{sessions_summary}\n\n"
        "Based on the above, generate a personalised physiotherapy progress report."
    )

    model_ids = ["models/gemini-2.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-flash"]

    for model_id in model_ids:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents=[f"{REPORT_SYSTEM_PROMPT}\n\n{user_prompt}"],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.5,
                    ),
                )
                return json.loads(response.text)
            except json.JSONDecodeError as exc:
                logger.error("Failed to parse report insights JSON: %s", exc)
                return None
            except Exception as exc:
                msg = str(exc)
                if "503" in msg or "UNAVAILABLE" in msg or "429" in msg:
                    wait = 2 ** attempt
                    _time.sleep(wait)
                    continue
                logger.error("Report insights API call failed: %s", exc)
                return None

    logger.error("All retries exhausted for report insights.")
    return None
