"""
Clinical Trials Failure Tool
==============================
Claude Agent SDK Custom Tool — TreeHacks 2026

Takes a drug name → queries ClinicalTrials.gov v2 API for terminated/withdrawn/
suspended trials → classifies WHY each trial failed (business vs safety vs efficacy)
→ flags drugs dropped for non-scientific reasons as repurposing candidates.

API:  https://clinicaltrials.gov/api/v2/studies
Auth: None required
Rate: 50 requests/minute (no key needed)

SDK contract:
    @tool(name, description, input_schema)
    async def handler(args: dict) → {"content": [{"type": "text", "text": "JSON"}]}

When registered under server key "drugrescue":
    mcp__drugrescue__clinical_trial_failure
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# — SDK import (graceful fallback for testing without SDK) ——————————
try:
    from claude_agent_sdk import tool
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

    def tool(name, desc, schema):
        """Stub decorator so the file parses without SDK installed."""
        def wrapper(fn):
            fn._tool_name = name
            fn._tool_desc = desc
            fn._tool_schema = schema
            return fn
        return wrapper

logger = logging.getLogger(__name__)

_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CLASSIFICATION KEYWORDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BUSINESS_KEYWORDS = [
    "business", "commercial", "funding", "financial", "sponsor decision",
    "strategic", "portfolio", "company", "merger", "acquisition",
    "insufficient accrual", "slow enrollment", "low enrollment",
    "enrollment", "recruitment", "administrative", "budget",
    "reprioritiz", "corporate", "resource", "personnel",
]

SAFETY_KEYWORDS = [
    "safety", "adverse", "toxicity", "death", "fatal", "serious adverse",
    "side effect", "hepatotoxicity", "cardiotoxicity", "risk",
    "liver", "cardiac", "renal", "nephrotoxicity", "neurotoxicity",
    "dili", "drug-induced", "serious event", "sae",
]

EFFICACY_KEYWORDS = [
    "efficacy", "futility", "lack of efficacy", "no benefit",
    "insufficient efficacy", "did not meet", "endpoint", "ineffective",
    "no significant", "primary endpoint not met", "negative result",
]


def classify_termination(why_stopped: str) -> str:
    """Classify why_stopped free-text into a category."""
    if not why_stopped:
        return "UNKNOWN"
    text = why_stopped.lower()
    if any(kw in text for kw in SAFETY_KEYWORDS):
        return "SAFETY"
    if any(kw in text for kw in EFFICACY_KEYWORDS):
        return "EFFICACY"
    if any(kw in text for kw in BUSINESS_KEYWORDS):
        return "BUSINESS/LOGISTICS"
    return "OTHER"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SYNC HELPERS — these run in the thread pool
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CT_BASE = "https://clinicaltrials.gov/api/v2/studies"


def _fetch_failed_trials(drug_name: str, disease: str | None,
                         max_results: int) -> dict:
    """
    Query ClinicalTrials.gov for terminated/withdrawn/suspended trials.
    Runs synchronously (called from thread pool).
    """
    params: dict[str, Any] = {
        "query.intr": drug_name,
        "filter.overallStatus": "TERMINATED,WITHDRAWN,SUSPENDED",
        "pageSize": min(max_results, 100),
        "countTotal": "true",
        "sort": "@relevance",
        "fields": (
            "protocolSection.identificationModule"
            "|protocolSection.statusModule"
            "|protocolSection.designModule"
            "|protocolSection.conditionsModule"
            "|protocolSection.armsInterventionsModule"
        ),
    }
    if disease:
        params["query.cond"] = disease

    all_studies: list[dict] = []
    page_token = None
    retries = 0

    while len(all_studies) < max_results and retries < 3:
        if page_token:
            params["pageToken"] = page_token
        try:
            # requests handles headers, cookies, redirects, encoding
            # automatically — unlike urllib which fights CT.gov's bot detection.
            import requests as _requests
            resp = _requests.get(
                CT_BASE,
                params=params,
                timeout=30,
                headers={"Accept": "application/json"},
            )
            if resp.status_code == 429:
                time.sleep(2)
                retries += 1
                continue
            resp.raise_for_status()
            data = resp.json()
        except ImportError:
            # Fallback if requests somehow missing
            return {"error": "pip install requests  (required for ClinicalTrials.gov)"}
        except Exception as e:
            status = getattr(e, 'response', None)
            code = status.status_code if status is not None else "?"
            return {"error": f"ClinicalTrials.gov HTTP {code}: {e}"}

        studies = data.get("studies", [])
        if not studies:
            break
        all_studies.extend(studies)
        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(1.2)  # Stay under 50 req/min

    # Parse each study
    trials = []
    for s in all_studies[:max_results]:
        proto = s.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        status = proto.get("statusModule", {})
        design = proto.get("designModule", {})
        conds = proto.get("conditionsModule", {})
        why = status.get("whyStopped", "")

        category = classify_termination(why)
        trials.append({
            "nct_id": ident.get("nctId"),
            "title": ident.get("briefTitle", "")[:200],
            "status": status.get("overallStatus"),
            "why_stopped": why or "Not specified",
            "failure_category": category,
            "phases": design.get("phases", []),
            "conditions": conds.get("conditions", [])[:5],
            "is_repurposing_candidate": category in (
                "BUSINESS/LOGISTICS", "OTHER", "UNKNOWN"
            ),
        })

    # Summary stats
    by_cat: dict[str, int] = {}
    for t in trials:
        cat = t["failure_category"]
        by_cat[cat] = by_cat.get(cat, 0) + 1

    business = by_cat.get("BUSINESS/LOGISTICS", 0)
    safety = by_cat.get("SAFETY", 0)
    repurposable = sum(1 for t in trials if t["is_repurposing_candidate"])

    return {
        "drug": drug_name,
        "disease_filter": disease,
        "total_failed_trials": len(trials),
        "by_category": by_cat,
        "repurposing_viable": business > 0 and safety == 0,
        "repurposable_count": repurposable,
        "safety_flags": safety,
        "summary": (
            f"{len(trials)} terminated trials found. "
            f"{business} dropped for business/logistics reasons, "
            f"{safety} for safety concerns. "
            + ("NO safety red flags — candidate is viable for repurposing."
               if safety == 0 and business > 0
               else f"⚠️ {safety} safety-related terminations — investigate before proceeding."
               if safety > 0
               else "No business-related terminations found.")
        ),
        "trials": trials,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  @tool DEFINITIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@tool(
    "clinical_trial_failure",
    "Query ClinicalTrials.gov for terminated/withdrawn/suspended clinical trials "
    "of a specific drug. Classifies WHY each trial was stopped: SAFETY (adverse "
    "events, toxicity), EFFICACY (didn't work), BUSINESS/LOGISTICS (enrollment, "
    "funding, corporate decisions), or OTHER/UNKNOWN. Drugs dropped for non-scientific "
    "reasons are prime repurposing candidates. Returns per-trial details with NCT IDs, "
    "phases, and a viability assessment. No API key needed.",
    {
        "type": "object",
        "properties": {
            "drug_name": {
                "type": "string",
                "description": "Drug name to search (generic name preferred, e.g. "
                "'temozolomide', 'bevacizumab')",
            },
            "disease": {
                "type": "string",
                "description": "Optional: filter trials by disease/condition to narrow "
                "results. Omit for all indications.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum trials to return (default 15)",
                "minimum": 1,
                "maximum": 50,
            },
        },
        "required": ["drug_name"],
    },
)
async def clinical_trial_failure_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Clinical trial failure tool handler. Offloads HTTP to thread pool."""
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            _pool,
            _fetch_failed_trials,
            args["drug_name"],
            args.get("disease"),
            args.get("max_results", 15),
        )

        is_err = "error" in result and "trials" not in result
        return {
            "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
            **({"is_error": True} if is_err else {}),
        }
    except Exception as e:
        logger.exception("clinical_trial_failure failed")
        return {
            "content": [{"type": "text", "text": json.dumps({
                "error": str(e), "tool": "clinical_trial_failure",
            })}],
            "is_error": True,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EXPORTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CT_TOOLS = [clinical_trial_failure_tool]

CT_TOOL_NAMES = [
    "mcp__drugrescue__clinical_trial_failure",
]
