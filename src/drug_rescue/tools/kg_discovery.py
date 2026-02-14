"""
KG Discovery Tool
==================
Claude Agent SDK Custom Tool — TreeHacks 2026

Takes a disease → scores ALL ~24K compounds in DRKG using trained RotatE
embeddings → cross-refs dropped_drugs.db → returns ranked, enriched candidates.

Data used:
    data/embeddings/  → RotatE entity + relation embeddings, ID mappings
    data/database/    → dropped_drugs.db (enrichment + classification)

SDK contract:
    @tool(name, description, input_schema)
    async def handler(args: dict) → {"content": [{"type": "text", "text": "JSON"}]}

When registered under server key "drugrescue":
    mcp__drugrescue__discover_candidates
    mcp__drugrescue__score_specific_drugs
    mcp__drugrescue__kg_info
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
from pathlib import Path
from typing import Any

# ── SDK import (graceful fallback for testing without SDK) ──────────────
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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GLOBAL STATE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
#  The DRKGScorer holds ~190MB of embeddings in memory. We load it ONCE
#  on first tool call and keep it alive. Safe because SDK MCP tools run
#  in-process (same Python interpreter).
#
#  ThreadPoolExecutor for the CPU-bound numpy work — numpy releases the
#  GIL during matrix operations so threads are fine here.

_scorer = None
_data_dir = "./data"
_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)


def set_data_dir(path: str):
    """Point tools at your data/ directory. Call before first invocation."""
    global _data_dir, _name_lookup, _scorer
    _data_dir = path
    _name_lookup = None  # Reset so lookup reloads from new path
    _scorer = None        # Reset so scorer reloads from new path


def _get_scorer():
    """Lazy-load the DRKGScorer. First call ~2s, then instant."""
    global _scorer
    if _scorer is None:
        from ..engines.scorer import DRKGScorer
        _scorer = DRKGScorer(
            embeddings_dir=str(Path(_data_dir) / "embeddings"),
            db_path=str(Path(_data_dir) / "database" / "dropped_drugs.db"),
        )
    return _scorer


# ── Name resolution ──────────────────────────────────────────────────
# PubChem/MeSH sometimes return wrong or ugly names. Fix them here.

_NAME_FIXES = {
    "Compound::DB00515": "CISPLATIN",       # PubChem returns "TRANS-PLATIN"
    "Compound::DB00853": "TEMOZOLOMIDE",
    "Compound::DB00112": "BEVACIZUMAB",
}

_name_lookup: dict[str, str] | None = None


def _get_name_lookup() -> dict[str, str]:
    """Load drug name lookup files once. Returns entity → name mapping."""
    global _name_lookup
    if _name_lookup is not None:
        return _name_lookup

    _name_lookup = {}
    data = Path(_data_dir)

    # Source 1: kg_entity_lookup.json
    p1 = data / "database" / "kg_entity_lookup.json"
    if p1.exists():
        try:
            with open(p1) as f:
                for entity, info in json.load(f).items():
                    if info.get("drug_name"):
                        _name_lookup[entity] = info["drug_name"]
        except Exception:
            pass

    # Source 2: drugbank_to_name.json
    p2 = data / "drugbank_to_name.json"
    if p2.exists():
        try:
            with open(p2) as f:
                for db_id, name in json.load(f).items():
                    entity = f"Compound::{db_id}"
                    if entity not in _name_lookup:
                        _name_lookup[entity] = name
        except Exception:
            pass

    # Apply manual fixes
    _name_lookup.update(_NAME_FIXES)
    logger.info("Name lookup: %d entries", len(_name_lookup))
    return _name_lookup


def _resolve_name(drug_name: str, drkg_entity: str) -> str:
    """Resolve a drug name: fix overrides, strip [OBSOLETE], try lookup."""
    lookup = _get_name_lookup()

    # 1. Manual fix
    if drkg_entity in _NAME_FIXES:
        return _NAME_FIXES[drkg_entity]

    # 2. If name is a raw ID, try lookup
    raw_id = drkg_entity.replace("Compound::", "")
    if drug_name == raw_id:
        resolved = lookup.get(drkg_entity)
        if resolved:
            drug_name = resolved

    # 3. Strip MeSH [OBSOLETE]
    if drug_name.startswith("[OBSOLETE]"):
        drug_name = drug_name.replace("[OBSOLETE]", "").strip()

    return drug_name


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SYNC HELPERS — these run in the thread pool
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _run_discovery(disease: str, max_candidates: int,
                   min_percentile: float, include_novel: bool) -> dict:
    """
    The actual computation:
      1. Score ALL compounds against disease (vectorized numpy)
      2. Cross-reference top hits against dropped_drugs.db
      3. Classify each as dropped / withdrawn / novel
      4. Return structured dict
    """
    from ..engines.discover import discover_candidates as engine_discover

    result = engine_discover(
        disease=disease,
        data_dir=_data_dir,
        top_k=max(500, max_candidates * 10) if not include_novel else max(100, max_candidates * 3),
        max_candidates=max_candidates,
        min_percentile=min_percentile,
        include_novel=include_novel,
    )

    if result.error:
        return {"error": result.error}

    return {
        "disease": result.disease,
        "method": result.method,
        "total_compounds_scored": result.total_compounds_scored,
        "candidates_returned": len(result.candidates),
        "timing_ms": result.timing_ms,
        "disease_entities_used": result.disease_entities_used,
        "treatment_relations_used": result.treatment_relations_used,
        "stats": result.stats,
        "candidates": [
            {
                "drug_name": _resolve_name(c.drug_name, c.drkg_entity),
                "drkg_entity": c.drkg_entity,
                "status": c.status,
                "chembl_id": c.chembl_id,
                "drugbank_id": c.drugbank_id,
                "smiles": c.smiles,
                "max_phase": c.max_phase,
                "molecule_type": c.molecule_type,
                "kg_score": c.kg_score,
                "kg_percentile": c.kg_percentile,
                "kg_z_score": c.kg_z_score,
                "kg_normalized": c.kg_normalized,
                "kg_rank": c.kg_rank,
                "kg_relation": c.kg_relation,
            }
            for c in result.candidates
        ],
    }


def _run_score_drugs(drug_names: list[str], disease: str) -> dict:
    """Score specific drugs by name against a disease."""
    scorer = _get_scorer()
    result = scorer.score_specific_drugs(drug_names, disease)

    if result.error and not result.predictions:
        return {"error": result.error}

    return {
        "disease": disease,
        "drugs_found": len(result.predictions),
        "drugs_missing": [n for n in drug_names
                          if not any(p.drug_name == n for p in result.predictions)],
        "predictions": [
            {
                "drug_name": p.drug_name,
                "score": p.score,
                "percentile": p.percentile,
                "z_score": p.z_score,
                "normalized_score": p.normalized_score,
                "rank": p.rank,
                "relation_used": p.relation_used,
            }
            for p in result.predictions
        ],
    }


def _run_get_info() -> dict:
    """Return graph metadata."""
    return _get_scorer().info()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  @tool DEFINITIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@tool(
    "discover_candidates",
    "Score ALL ~24,000 compounds in the DRKG knowledge graph against a disease "
    "using trained RotatE embeddings. Returns ranked drug candidates enriched "
    "with names, SMILES structures, clinical phase history, and classification "
    "(dropped/withdrawn/novel). Each candidate includes kg_percentile (0-100, "
    "higher = stronger graph evidence) and kg_normalized (0-1). Candidates with "
    "status='dropped' were in Phase I-III trials but never approved — prime "
    "repurposing targets. status='novel' means the compound is in the graph but "
    "not in our clinical database. Fast: scores all compounds in <1 second.",
    {
        "type": "object",
        "properties": {
            "disease": {
                "type": "string",
                "description": "Disease to investigate. Examples: glioblastoma, "
                "alzheimer, parkinson, als, breast cancer, lung cancer, leukemia, "
                "depression, diabetes, epilepsy, multiple myeloma, ipf",
            },
            "max_candidates": {
                "type": "integer",
                "description": "Maximum candidates to return (default 20)",
                "minimum": 1,
                "maximum": 100,
            },
            "min_percentile": {
                "type": "number",
                "description": "Minimum KG percentile to include (default 75.0). "
                "Use 90+ for only the strongest signals.",
                "minimum": 0,
                "maximum": 100,
            },
            "include_novel": {
                "type": "boolean",
                "description": "Include compounds not in dropped_drugs database "
                "(default false). Set true to also see approved/novel drugs.",
            },
        },
        "required": ["disease"],
    },
)
async def discover_candidates_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Discovery tool handler. Offloads numpy computation to thread pool."""
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            _pool,
            _run_discovery,
            args["disease"],
            args.get("max_candidates", 20),
            args.get("min_percentile", 75.0),
            args.get("include_novel", False),
        )

        if "error" in result and "candidates" not in result:
            return {
                "content": [{"type": "text", "text": json.dumps({
                    "error": result["error"],
                    "hint": "Try: glioblastoma, alzheimer, parkinson, als, "
                            "breast cancer, lung cancer, leukemia, diabetes, "
                            "epilepsy, depression, multiple myeloma, ipf",
                }, indent=2)}],
                "is_error": True,
            }

        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    except Exception as e:
        logger.exception("discover_candidates failed")
        return {
            "content": [{"type": "text", "text": json.dumps({
                "error": str(e), "tool": "discover_candidates",
            })}],
            "is_error": True,
        }


@tool(
    "score_specific_drugs",
    "Score specific drugs by name against a disease in the DRKG knowledge graph. "
    "Unlike discover_candidates which finds NEW candidates, this checks how "
    "specific drugs (that you already know about) rank in the graph. "
    "Accepts generic names (metformin), DrugBank IDs (DB00331), or ChEMBL IDs.",
    {
        "type": "object",
        "properties": {
            "drug_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Drug names, DrugBank IDs, or ChEMBL IDs to score",
            },
            "disease": {
                "type": "string",
                "description": "Disease to score against",
            },
        },
        "required": ["drug_names", "disease"],
    },
)
async def score_specific_drugs_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Score specific drugs against a disease."""
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            _pool, _run_score_drugs, args["drug_names"], args["disease"],
        )
        is_err = "error" in result and not result.get("predictions")
        return {
            "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
            **({"is_error": True} if is_err else {}),
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
            "is_error": True,
        }


@tool(
    "kg_info",
    "Get metadata about the DRKG knowledge graph: number of compounds, diseases, "
    "genes, embedding method (RotatE/TransE), embedding dimensions, and available "
    "treatment relations.",
    {"type": "object", "properties": {}},
)
async def kg_info_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Return graph metadata."""
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(_pool, _run_get_info)
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    except Exception as e:
        return {
            "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
            "is_error": True,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EXPORTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

KG_TOOLS = [discover_candidates_tool, score_specific_drugs_tool, kg_info_tool]

KG_TOOL_NAMES = [
    "mcp__drugrescue__discover_candidates",
    "mcp__drugrescue__score_specific_drugs",
    "mcp__drugrescue__kg_info",
]
