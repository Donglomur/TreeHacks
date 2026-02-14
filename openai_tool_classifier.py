import json
import os
from typing import Any, Dict

from openai import OpenAI

# We force JSON output via response_format, so we don't need regex parsing.
# But we still validate fields to be safe.

SYSTEM_PROMPT = """
You are a clinical trials termination intent classifier.

Input: free-text 'whyStopped' from ClinicalTrials.gov.

Return STRICT JSON only with:
{
  "label": "RESCUABLE" | "NOT_RESCUABLE" | "AMBIGUOUS",
  "intent": "BUSINESS" | "ENROLLMENT" | "FUNDING" | "LOGISTICS" | "OWNERSHIP" |
            "SAFETY" | "EFFICACY" | "REGULATORY" | "OTHER" | "UNKNOWN",
  "confidence": 0.0,
  "evidence_span": "exact substring from input"
}

Definitions:
- RESCUABLE = stopped for business/funding/recruitment/logistics/ownership/strategic reasons,
              not because the drug failed.
- NOT_RESCUABLE = stopped for safety/toxicity, lack of efficacy/futility/failed endpoints,
                  or clear harm/regulatory safety concerns.
- AMBIGUOUS = unclear/insufficient information.

Rules:
- Do NOT do naive keyword matching; infer meaning from the sentence.
- Handle negation correctly: "not related to safety or efficacy" => RESCUABLE.
- If unsure, return AMBIGUOUS with lower confidence.
- evidence_span must be an EXACT substring from the input text (copy it exactly).
"""

ALLOWED_LABELS = {"RESCUABLE", "NOT_RESCUABLE", "AMBIGUOUS"}
ALLOWED_INTENTS = {
    "BUSINESS", "ENROLLMENT", "FUNDING", "LOGISTICS", "OWNERSHIP",
    "SAFETY", "EFFICACY", "REGULATORY", "OTHER", "UNKNOWN"
}


def classify_why_stopped_openai(
    why_stopped: str,
    model: str = "gpt-4.1-mini",
) -> Dict[str, Any]:
    """
    Uses OpenAI to classify a ClinicalTrials.gov 'whyStopped' string into:
    - label: RESCUABLE / NOT_RESCUABLE / AMBIGUOUS
    - intent: reason category
    - confidence: 0..1
    - evidence_span: exact substring from input
    """

    # If empty, no reason given => ambiguous
    if not why_stopped or not why_stopped.strip():
        return {
            "label": "AMBIGUOUS",
            "intent": "UNKNOWN",
            "confidence": 0.0,
            "evidence_span": ""
        }

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not set. In PowerShell: $env:OPENAI_API_KEY='...'"
        )

    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": why_stopped.strip()},
        ],
    )

    content = response.choices[0].message.content or "{}"

    # Parse JSON
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # If something goes wrong, fail safe
        return {
            "label": "AMBIGUOUS",
            "intent": "UNKNOWN",
            "confidence": 0.0,
            "evidence_span": ""
        }

    # Validate + normalize output
    label = data.get("label", "AMBIGUOUS")
    if label not in ALLOWED_LABELS:
        label = "AMBIGUOUS"

    intent = data.get("intent", "UNKNOWN")
    if intent not in ALLOWED_INTENTS:
        intent = "UNKNOWN"

    conf = data.get("confidence", 0.0)
    try:
        conf = float(conf)
    except Exception:
        conf = 0.0
    conf = max(0.0, min(1.0, conf))

    evidence = data.get("evidence_span", "")
    if not isinstance(evidence, str):
        evidence = ""

    # Optional: if evidence isn't actually a substring, blank it
    # (prevents hallucinated evidence spans)
    if evidence and evidence not in why_stopped:
        evidence = ""

    return {
        "label": label,
        "intent": intent,
        "confidence": conf,
        "evidence_span": evidence
    }
