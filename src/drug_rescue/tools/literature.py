"""
Literature Research Tool
=========================
Claude Agent SDK Custom Tool — TreeHacks 2026

Thin @tool wrapper around engines/literature.py.

Runs a 4-query Perplexity Sonar pipeline per drug × disease:
    1. Mechanism of action + pathway relevance
    2. Clinical/preclinical evidence (NCTs, case reports, animal models)
    3. Regulatory + patent + safety status
    4. Recent developments (2024-2026)

Returns structured report with evidence level (STRONG/MODERATE/WEAK/NONE),
recommendation (PURSUE/INVESTIGATE_FURTHER/DEPRIORITIZE), key findings,
safety notes, aggregated citations, and cost estimate.

SDK contract:
    @tool(name, description, input_schema)
    async def handler(args: dict) → {"content": [{"type": "text", "text": "JSON"}]}

When registered under server key "drugrescue":
    mcp__drugrescue__literature_search
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ._cache import load_cached_output, save_cached_output

try:
    from claude_agent_sdk import tool
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

    def tool(name, desc, schema):
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
        from ..engines.literature import LiteratureEngine
        _engine = LiteratureEngine()
    return _engine


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  @tool DEFINITION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@tool(
    "literature_search",
    "Research a drug-disease pair using Perplexity Sonar Pro with a 4-query "
    "biomedical pipeline: (1) mechanism of action + pathway relevance, "
    "(2) clinical/preclinical evidence including NCT numbers, case reports, "
    "and animal models, (3) regulatory/patent/safety status, (4) recent "
    "2024-2026 developments. Returns structured report with evidence level "
    "(STRONG/MODERATE/WEAK/NONE), recommendation (PURSUE/INVESTIGATE_FURTHER/"
    "DEPRIORITIZE), key findings, safety notes, and aggregated citations from "
    "PubMed, ClinicalTrials.gov, FDA, Nature, NEJM, and more. "
    "Requires PERPLEXITY_API_KEY. ~10-15 seconds per drug (4 API calls).",
    {
        "type": "object",
        "properties": {
            "drug_name": {
                "type": "string",
                "description": "Drug name to research (generic name preferred).",
            },
            "disease": {
                "type": "string",
                "description": "Disease/condition to research repurposing for.",
            },
        },
        "required": ["drug_name", "disease"],
    },
)
async def literature_search_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Literature research tool — async-native, no executor needed."""
    cache_args = {
        "drug_name": str(args["drug_name"]).strip().upper(),
        "disease": str(args["disease"]).strip().lower(),
    }
    cached = load_cached_output("literature_search", cache_args)
    if cached is not None:
        return {"content": [{"type": "text", "text": json.dumps(cached, indent=2)}]}

    try:
        engine = _get_engine()
        report = await engine.research(
            drug_name=args["drug_name"],
            disease=args["disease"],
        )

        output = report.to_dict()

        # Add a concise summary for Claude
        output["summary"] = (
            f"Evidence: {report.evidence_level} → {report.recommendation}. "
            f"{report.citation_count} citations across 4 queries. "
            f"{len(report.key_findings)} key findings extracted. "
            f"Cost: ${report.total_cost_estimate:.4f}."
        )

        save_cached_output("literature_search", cache_args, output)
        return {"content": [{"type": "text", "text": json.dumps(output, indent=2)}]}

    except Exception as e:
        logger.exception("literature_search failed")
        return {
            "content": [{"type": "text", "text": json.dumps({
                "error": str(e),
                "tool": "literature_search",
                "drug": args.get("drug_name"),
                "disease": args.get("disease"),
            })}],
            "is_error": True,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EXPORTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LIT_TOOLS = [literature_search_tool]

LIT_TOOL_NAMES = [
    "mcp__drugrescue__literature_search",
]
