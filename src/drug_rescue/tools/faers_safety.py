"""
FAERS Inverse Signal Detector Tool
====================================
Claude Agent SDK Custom Tool — TreeHacks 2026

Thin @tool wrapper around engines/faers.py.

Takes candidate drugs + disease → async OpenFDA queries with drug-variant
resolution → 2×2 contingency tables → ROR + p-values → optional Bonferroni /
BH-FDR correction → inverse signal detection.

Key: this tool is async-native (engine uses asyncio.to_thread), so no
run_in_executor needed here — we await the engine directly.

SDK contract:
    @tool(name, description, input_schema)
    async def handler(args: dict) → {"content": [{"type": "text", "text": "JSON"}]}

When registered under server key "drugrescue":
    mcp__drugrescue__faers_inverse_signal
    mcp__drugrescue__faers_suggest_events
"""

from __future__ import annotations

import json
import logging
from typing import Any

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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GLOBAL STATE — lazy-initialized
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        from ..engines.faers import FAERSEngine
        _engine = FAERSEngine()
    return _engine


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  @tool DEFINITIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@tool(
    "faers_inverse_signal",
    "Screen candidate drugs against a disease in FDA FAERS adverse event data. "
    "Detects INVERSE SIGNALS (drugs with fewer disease-symptom reports than "
    "expected → protective association) using ROR with 95% CI and one-sided "
    "p-values.  Supports Bonferroni and Benjamini-Hochberg FDR correction. "
    "Can screen MULTIPLE drugs in one call (batched). Automatically resolves "
    "drug names to the highest-coverage openFDA query variant. Built-in MedDRA "
    "mappings for 12 diseases; custom event terms accepted. Async with caching.",
    {
        "type": "object",
        "properties": {
            "disease": {
                "type": "string",
                "description": "Disease name. Built-in: glioblastoma, alzheimer, "
                "parkinson, als, breast cancer, lung cancer, depression, diabetes, "
                "ipf, epilepsy, multiple myeloma, leukemia. Others auto-resolve.",
            },
            "candidate_drugs": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "description": "Drug generic names to screen, e.g. "
                "['metformin', 'temozolomide', 'aspirin'].",
            },
            "disease_events": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional: override built-in MedDRA terms. "
                "Use exact MedDRA Preferred Terms (case-sensitive).",
            },
            "correction": {
                "type": "string",
                "enum": ["none", "bonferroni", "fdr"],
                "description": "Multiple testing correction (default 'none'). "
                "Use 'fdr' when screening many drugs × events.",
            },
            "alpha": {
                "type": "number",
                "description": "Significance level (default 0.05).",
                "minimum": 0.001,
                "maximum": 0.20,
            },
        },
        "required": ["disease", "candidate_drugs"],
    },
)
async def faers_inverse_signal_tool(args: dict[str, Any]) -> dict[str, Any]:
    """FAERS inverse signal screening — async-native, no executor needed."""
    try:
        engine = _get_engine()
        result = await engine.screen(
            drugs=args["candidate_drugs"],
            disease=args["disease"],
            disease_events=args.get("disease_events"),
            alpha=float(args.get("alpha", 0.05)),
            correction=args.get("correction", "none"),
        )

        output = result.to_dict()

        # Human-readable summary for Claude
        inv = result.inverse_signals
        output["summary"] = (
            f"Screened {len(args['candidate_drugs'])} drug(s) × "
            f"{len(result.events)} event(s) = {result.tests_run} tests. "
            f"Found {len(inv)} inverse signal(s) "
            f"(correction: {result.correction_method}). "
        )
        if inv:
            t = inv[0]
            output["summary"] += (
                f"Strongest: {t.drug} on '{t.event}' "
                f"(ROR={t.ror}, CI=[{t.ci_lower}, {t.ci_upper}], "
                f"p={t.p_value:.4g})."
            )
        else:
            output["summary"] += "No protective associations detected."

        # Per-drug verdict for Claude's reasoning
        output["drug_verdicts"] = {}
        for sig in result.strongest_by_drug:
            output["drug_verdicts"][sig.drug] = {
                "has_inverse_signal": sig.is_inverse_signal,
                "has_positive_signal": sig.is_positive_signal,
                "best_ror": sig.ror,
                "best_event": sig.event,
                "report_count": sig.report_count,
                "normalized_score": sig.normalized_score,
                "interpretation": sig.interpretation,
            }

        return {"content": [{"type": "text", "text": json.dumps(output, indent=2)}]}

    except Exception as e:
        logger.exception("faers_inverse_signal failed")
        return {
            "content": [{"type": "text", "text": json.dumps({
                "error": str(e), "tool": "faers_inverse_signal",
            })}],
            "is_error": True,
        }


@tool(
    "faers_suggest_events",
    "Fetch the most-reported MedDRA event terms from FAERS for a specific drug "
    "or globally. Use to discover what adverse events are associated with a drug "
    "before running inverse signal screening, or to find good custom event terms "
    "for diseases not in the built-in mapping.",
    {
        "type": "object",
        "properties": {
            "drug": {
                "type": "string",
                "description": "Drug name to filter events for. Omit for global top events.",
            },
            "limit": {
                "type": "integer",
                "description": "Number of top events to return (default 25, max 1000).",
                "minimum": 1,
                "maximum": 1000,
            },
        },
    },
)
async def faers_suggest_events_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Suggest MedDRA event terms from FAERS — async-native."""
    try:
        engine = _get_engine()
        terms = await engine.suggest_events(
            drug=args.get("drug"),
            limit=int(args.get("limit", 25)),
        )
        output = {
            "drug": args.get("drug"),
            "events_found": len(terms),
            "events": [{"term": t, "count": c} for t, c in terms],
        }
        return {"content": [{"type": "text", "text": json.dumps(output, indent=2)}]}

    except Exception as e:
        logger.exception("faers_suggest_events failed")
        return {
            "content": [{"type": "text", "text": json.dumps({
                "error": str(e), "tool": "faers_suggest_events",
            })}],
            "is_error": True,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EXPORTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FAERS_TOOLS = [faers_inverse_signal_tool, faers_suggest_events_tool]

FAERS_TOOL_NAMES = [
    "mcp__drugrescue__faers_inverse_signal",
    "mcp__drugrescue__faers_suggest_events",
]
