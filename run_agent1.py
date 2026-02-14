import re
from collections import Counter, defaultdict
from typing import Dict, Any, List, Tuple

from clinical_api import fetch_trials
from cache_intent import load_cached, save_cached
from openai_tool_classifier import classify_why_stopped_openai


# -------------------------------
# Drug name cleaning
# -------------------------------
def clean_drug_name(name: str) -> str:
    """
    Normalize intervention names to reduce junk:
    - drop placebo
    - drop pure dosage strings
    - remove dosage suffixes from real drug names
    - drop obvious non-drug interventions (blood sample, imaging, etc.)
    """
    if not name:
        return ""

    n = name.strip()

    # Drop placebo
    if "placebo" in n.lower():
        return ""

    # Drop obvious non-drug "interventions" that appear in DRUG/BIOLOGICAL sometimes
    junk = {
        "blood sample", "blood", "sample",
        "mri", "pet", "ct", "scan",
        "saline",
    }
    if n.lower() in junk:
        return ""

    # Drop pure dose strings: "2 mg/day", "50 mg", "0.5 g"
    if re.fullmatch(r"\d+(\.\d+)?\s*(mg|g|mcg|ug|ml|iu)(/day)?", n.lower()):
        return ""

    # Remove dose suffix from real drug names: "CNP520 50mg" -> "CNP520"
    n = re.sub(r"\b\d+(\.\d+)?\s*(mg|g|mcg|ug|ml|iu)(/day)?\b", "", n, flags=re.I)

    # Remove fragments like "/kg"
    n = re.sub(r"\s*/\s*kg\b", "", n, flags=re.I)

    # Collapse spaces
    n = re.sub(r"\s+", " ", n).strip()

    return n


def extract_single_drug(study: Dict[str, Any]) -> Tuple[str, List[str], str]:
    """
    Returns:
      - single_drug ("" if none or multi)
      - all_clean_drugs (deduped list)
      - why_stopped
    """
    protocol = study.get("protocolSection", {})
    status_mod = protocol.get("statusModule", {})
    arms_mod = protocol.get("armsInterventionsModule", {})

    why_stopped = status_mod.get("whyStopped", "") or ""

    interventions = arms_mod.get("interventions", []) or []
    drugs: List[str] = []
    seen = set()

    for itv in interventions:
        if itv.get("type") in ("DRUG", "BIOLOGICAL"):
            raw = (itv.get("name") or "").strip()
            cleaned = clean_drug_name(raw)
            if cleaned:
                key = cleaned.lower()
                if key not in seen:
                    seen.add(key)
                    drugs.append(cleaned)

    # Keep only single-drug trials
    single = drugs[0] if len(drugs) == 1 else ""
    return single, drugs, why_stopped


def classify_with_cache(why_stopped: str) -> Dict[str, Any]:
    """
    Cache by whyStopped string so we don't pay for repeated OpenAI calls.
    """
    cached = load_cached(why_stopped)
    if cached is not None:
        return cached

    result = classify_why_stopped_openai(why_stopped)
    save_cached(why_stopped, result)
    return result


def run(disease: str, max_trials: int = 20):
    print(f"\nFetching terminated/suspended/withdrawn trials for: {disease}\n")

    studies = fetch_trials(disease, max_results=max_trials)

    counts = Counter()
    skipped = 0

    # Collect rescuable drug candidates + metadata
    rescuable_drugs = defaultdict(lambda: {
        "count": 0,
        "max_confidence": 0.0,
        "intents": Counter(),
        "examples": []
    })

    for study in studies:
        single_drug, all_drugs, why_stopped = extract_single_drug(study)

        # Skip multi-drug or none
        if not single_drug:
            skipped += 1
            continue

        # Classify reason with OpenAI (cached)
        try:
            result = classify_with_cache(why_stopped)
        except Exception as e:
            # If OpenAI errors, keep pipeline alive
            result = {"label": "AMBIGUOUS", "intent": "UNKNOWN", "confidence": 0.0, "evidence_span": ""}

        label = result.get("label", "AMBIGUOUS")
        intent = result.get("intent", "UNKNOWN")
        confidence = result.get("confidence", 0.0)
        evidence = result.get("evidence_span", "")

        counts[label] += 1

        print("\n---")
        print("Drug:", single_drug)
        print("Reason:", why_stopped)
        print("Label:", label)
        print("Intent:", intent)
        print("Confidence:", confidence)
        if evidence:
            print("Evidence span:", evidence)

        # Save rescuable drug candidates
        if label == "RESCUABLE":
            bucket = rescuable_drugs[single_drug]
            bucket["count"] += 1
            bucket["max_confidence"] = max(bucket["max_confidence"], float(confidence))
            bucket["intents"][intent] += 1
            if len(bucket["examples"]) < 3 and why_stopped:
                bucket["examples"].append(why_stopped)

    # Summary
    print("\n===== SUMMARY (single-drug trials only) =====")
    print("RESCUABLE:", counts["RESCUABLE"])
    print("NOT_RESCUABLE:", counts["NOT_RESCUABLE"])
    print("AMBIGUOUS:", counts["AMBIGUOUS"])
    print("SKIPPED (0 or multi-drug):", skipped)

    # Ranked rescuable list
    print("\n===== RESCUABLE DRUG LIST (ranked) =====")
    ranked = sorted(
        rescuable_drugs.items(),
        key=lambda kv: (kv[1]["count"], kv[1]["max_confidence"]),
        reverse=True
    )

    if not ranked:
        print("(none found in this batch)")
        return

    for drug, info in ranked:
        top_intents = info["intents"].most_common(2)
        intents_str = ", ".join([f"{k}({v})" for k, v in top_intents]) if top_intents else "UNKNOWN"
        print(f"- {drug}  | trials={info['count']} | max_conf={info['max_confidence']:.2f} | intents={intents_str}")
        for ex in info["examples"]:
            print(f"    • {ex}")


if __name__ == "__main__":
    disease = input("Enter a disease/condition: ").strip()
    if not disease:
        disease = "Alzheimer disease"  # safe default so it runs if user hits Enter
    run(disease, max_trials=20)
