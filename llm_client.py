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

load_dotenv()  # reads .env into os.environ

logger = logging.getLogger(__name__)

# ── Gemini configuration ─────────────────────────────────────────────────────

def _get_client() -> genai.Client:
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
      "caution": "<specific note or empty string>",
      "priority": 1
    }
  ]
}
"""


def _build_user_prompt(complaint: str, pain_level: int, exercises_catalogue: list) -> str:
    catalogue_str = json.dumps(
        [{"id": e["id"], "name": e["name"], "description": e["description"]}
         for e in exercises_catalogue],
        indent=2,
    )
    return (
        f"Patient complaint: {complaint}\n"
        f"Current pain level (1-10): {pain_level}\n\n"
        f"Available exercises catalogue:\n{catalogue_str}\n\n"
        "Generate an appropriate physiotherapy programme from the catalogue above."
    )


# ── Public API ───────────────────────────────────────────────────────────────

import time as _time

def generate_exercise_plan(
    complaint: str,
    pain_level: int,
    exercises_catalogue: list,
    confidence_threshold: float = 0.6,
) -> Optional[dict]:
    """
    Calls Gemini and returns a validated, filtered plan dict.
    Returns None on API / parse failure.
    Retries up to 3 times with exponential backoff on transient errors.
    """
    client = _get_client()
    user_prompt = _build_user_prompt(complaint, pain_level, exercises_catalogue)
    full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"

    model_ids = ["models/gemini-2.5-flash", "models/gemini-2.0-flash"]

    for model_id in model_ids:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents=full_prompt,
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
