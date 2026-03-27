import base64
import json
import re
import time
import anthropic
from config import ANTHROPIC_API_KEY

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_RETRYABLE_STATUS = {529, 500, 502, 503, 504}
_MAX_RETRIES = 3
_BACKOFF_BASE = 2  # seconds

SYSTEM_PROMPT = """You are a food identification and nutrition assistant. Given an image of food, identify every distinct food item visible.

Return ONLY a valid JSON array — no markdown, no explanation, no code fences. Each element must have:
- "name": descriptive name of the food as it appears (e.g. "grilled chicken breast")
- "quantity": estimated portion size with unit (e.g. "200g", "1 cup", "1 medium")
- "search_term": simplified term for nutrition database lookup (e.g. "chicken breast", "white rice", "banana")
- "est_kcal": integer — your best estimate of total calories for this exact portion
- "est_protein_g": integer — estimated protein in grams for this exact portion
- "est_carbs_g": integer — estimated carbohydrates in grams for this exact portion
- "est_fat_g": integer — estimated fat in grams for this exact portion

Use your nutritional knowledge to produce accurate estimates. These are used as fallback data when the nutrition database is unavailable.

Example:
[{"name":"grilled chicken breast","quantity":"200g","search_term":"chicken breast","est_kcal":330,"est_protein_g":62,"est_carbs_g":0,"est_fat_g":7}]

If no food is visible, return: []"""


def identify_foods(jpeg_bytes: bytes) -> list[dict]:
    """Call Claude vision API with JPEG bytes, return list of food dicts."""
    b64 = base64.standard_b64encode(jpeg_bytes).decode("utf-8")

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = _client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": b64,
                                },
                            },
                            {
                                "type": "text",
                                "text": "Identify all food items in this image.",
                            },
                        ],
                    }
                ],
            )
            break  # success
        except anthropic.APIStatusError as exc:
            last_exc = exc
            if exc.status_code not in _RETRYABLE_STATUS or attempt == _MAX_RETRIES - 1:
                raise
            time.sleep(_BACKOFF_BASE**attempt)
    else:
        raise last_exc  # type: ignore[misc]

    raw = response.content[0].text.strip()

    # Strip markdown code fences defensively
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    raw = raw.strip()

    return json.loads(raw)
