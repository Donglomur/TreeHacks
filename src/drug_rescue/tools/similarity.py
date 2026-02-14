"""
Molecular Similarity Screener Tool
====================================
Claude Agent SDK Custom Tool — TreeHacks 2026

Compares candidate drugs against approved treatments using Morgan/ECFP4
fingerprints (2048-bit) and Tanimoto similarity.

Fully functional:
    - Fetches SMILES from PubChem REST API for ANY drug name (no hardcoding)
    - Computes Morgan fingerprints via RDKit
    - Vectorized Tanimoto against pre-computed database (if available)
    - Pairwise Tanimoto between candidate and approved drugs
    - Caches PubChem lookups within session

API:  https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/CanonicalSMILES/JSON
Auth: None (free, no key)
Rate: 5 requests/second

SDK contract:
    @tool(name, description, input_schema)
    async def handler(args: dict) → {"content": [{"type": "text", "text": "JSON"}]}

When registered under server key "drugrescue":
    mcp__drugrescue__molecular_similarity
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

import numpy as np

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

_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GLOBAL STATE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_fp_matrix: Optional[np.ndarray] = None
_bit_counts: Optional[np.ndarray] = None
_drug_index: Optional[list[dict]] = None
_name_to_idx: dict[str, int] = {}  # drug name → row in _fp_matrix
_data_dir = "./data"
_smiles_cache: dict[str, Optional[str]] = {}
_rdkit_available: Optional[bool] = None


def set_data_dir(path: str):
    global _data_dir
    _data_dir = path


# Known approved drugs per disease — CACHE, not single source of truth.
# PubChem lookup fills gaps for anything not here.
APPROVED_DRUGS: dict[str, list[str]] = {
    "glioblastoma": ["Temozolomide", "Carmustine", "Lomustine", "Bevacizumab"],
    "alzheimer": ["Donepezil", "Memantine", "Rivastigmine", "Galantamine"],
    "parkinson": ["Levodopa", "Rasagiline", "Selegiline", "Pramipexole", "Ropinirole"],
    "als": ["Riluzole", "Edaravone"],
    "breast cancer": ["Tamoxifen", "Letrozole", "Anastrozole", "Trastuzumab"],
    "lung cancer": ["Erlotinib", "Gefitinib", "Osimertinib", "Pembrolizumab"],
    "depression": ["Fluoxetine", "Sertraline", "Venlafaxine", "Bupropion"],
    "diabetes": ["Metformin", "Pioglitazone", "Sitagliptin", "Empagliflozin"],
    "epilepsy": ["Valproic acid", "Carbamazepine", "Levetiracetam", "Lamotrigine"],
    "ipf": ["Pirfenidone", "Nintedanib"],
    "multiple myeloma": ["Lenalidomide", "Thalidomide", "Bortezomib", "Dexamethasone"],
    "leukemia": ["Imatinib", "Dasatinib", "Cytarabine"],
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PUBCHEM SMILES LOOKUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PUBCHEM_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{}/property/CanonicalSMILES/JSON"


def _fetch_smiles_pubchem(drug_name: str) -> Optional[str]:
    """
    Fetch canonical SMILES from PubChem REST API.
    Uses requests (same lib that fixed ClinicalTrials.gov).
    """
    key = drug_name.strip().lower()
    if key in _smiles_cache:
        return _smiles_cache[key]

    encoded = urllib.parse.quote(drug_name.strip(), safe="")
    url = PUBCHEM_URL.format(encoded)
    try:
        import requests as _req
        resp = _req.get(url, timeout=10)
        if resp.status_code == 404:
            logger.debug("PubChem 404 for %s (not a small molecule)", drug_name)
            _smiles_cache[key] = None
            return None
        resp.raise_for_status()
        data = resp.json()
        props = data.get("PropertyTable", {}).get("Properties", [])
        if props:
            p = props[0]
            # PubChem returns different key names depending on version:
            #   CanonicalSMILES, ConnectivitySMILES, or IsomericSMILES
            smiles = (
                p.get("CanonicalSMILES")
                or p.get("ConnectivitySMILES")
                or p.get("IsomericSMILES")
            )
            if smiles:
                _smiles_cache[key] = smiles
                return smiles
            else:
                logger.warning(
                    "PubChem no SMILES key for %s. Keys: %s",
                    drug_name, list(p.keys()),
                )
    except ImportError:
        logger.warning("pip install requests (needed for PubChem)")
    except Exception as e:
        logger.warning("PubChem error for %s: %s", drug_name, e)

    _smiles_cache[key] = None
    return None


def _resolve_smiles(name_or_smiles: str) -> Optional[str]:
    """
    Resolve a string to SMILES.

    If it looks like SMILES already (contains special chars), return as-is.
    Otherwise treat as a drug name and look up via PubChem.
    """
    s = name_or_smiles.strip()
    # Heuristic: SMILES contain these chars, drug names don't
    if any(c in s for c in ("(", "=", "#", "[", "\\", "/")):
        return s
    return _fetch_smiles_pubchem(s)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  RDKIT FINGERPRINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _check_rdkit() -> bool:
    global _rdkit_available
    if _rdkit_available is None:
        try:
            from rdkit import Chem  # noqa: F401
            _rdkit_available = True
        except ImportError:
            _rdkit_available = False
    return _rdkit_available


def _compute_fp(smiles: str) -> Optional[np.ndarray]:
    """Compute Morgan/ECFP4 fingerprint (2048-bit) from SMILES."""
    if not _check_rdkit():
        return None
    from rdkit import Chem
    from rdkit.Chem import AllChem

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048)
    return np.array(fp, dtype=np.float32)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TANIMOTO MATH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _tanimoto_pair(fp_a: np.ndarray, fp_b: np.ndarray) -> float:
    """Tanimoto coefficient between two fingerprint vectors."""
    inter = float(np.dot(fp_a, fp_b))
    union = float(fp_a.sum() + fp_b.sum() - inter)
    return inter / union if union > 0 else 0.0


def _tanimoto_1_vs_all(
    query: np.ndarray,
    matrix: np.ndarray,
    bit_counts: np.ndarray,
) -> np.ndarray:
    """
    Vectorized Tanimoto: one query (2048,) vs N drugs (N, 2048).
    ~3ms for 24,000 drugs on commodity hardware.
    """
    q_bits = float(query.sum())
    intersection = matrix @ query
    union = q_bits + bit_counts - intersection
    return np.divide(
        intersection, union,
        out=np.zeros(len(intersection), dtype=np.float32),
        where=union > 0,
    )


def _interpret(sim: float) -> str:
    if sim >= 0.85:
        return "Very high — likely similar biological activity"
    elif sim >= 0.70:
        return "High — probable shared target profile"
    elif sim >= 0.50:
        return "Moderate — possible shared scaffolds"
    elif sim >= 0.30:
        return "Low — distant structural relationship"
    return "Very low — structurally unrelated"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PRE-COMPUTED FINGERPRINT DATABASE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _load_fp_database():
    """Lazy-load pre-computed fingerprint matrix if available."""
    global _fp_matrix, _bit_counts, _drug_index, _name_to_idx
    if _fp_matrix is not None:
        return

    fp_path = Path(_data_dir) / "fingerprints" / "morgan_fps.npy"
    idx_path = Path(_data_dir) / "fingerprints" / "fp_drug_index.json"

    if fp_path.exists() and idx_path.exists():
        _fp_matrix = np.load(str(fp_path)).astype(np.float32)
        _bit_counts = _fp_matrix.sum(axis=1)
        with open(idx_path) as f:
            _drug_index = json.load(f)

        # Build name → index lookup (case-insensitive)
        _name_to_idx = {}
        for i, entry in enumerate(_drug_index):
            name = entry.get("name", "").strip().lower()
            if name:
                _name_to_idx[name] = i
            # Also index by drug_id, drugbank_id, etc. if present
            for key in ("id", "drug_id", "drugbank_id", "chembl_id"):
                val = entry.get(key, "")
                if val:
                    _name_to_idx[str(val).strip().lower()] = i

        logger.info(
            "Loaded %d pre-computed fingerprints (%d unique names)",
            len(_drug_index), len(_name_to_idx),
        )
    else:
        _fp_matrix = np.empty((0, 2048), dtype=np.float32)
        _bit_counts = np.empty(0, dtype=np.float32)
        _drug_index = []
        _name_to_idx = {}


def _get_precomputed_fp(name: str) -> Optional[np.ndarray]:
    """Look up a drug's fingerprint from the precomputed database by name."""
    _load_fp_database()
    idx = _name_to_idx.get(name.strip().lower())
    if idx is not None and _fp_matrix is not None and idx < len(_fp_matrix):
        return _fp_matrix[idx]
    return None


def _get_fp(name: str, smiles: str | None = None) -> Optional[np.ndarray]:
    """
    Get fingerprint for a drug, trying multiple strategies:
    1. Precomputed database (by name) — no rdkit needed
    2. RDKit computation from SMILES — if rdkit available
    Returns None if both fail.
    """
    # Strategy 1: precomputed database
    fp = _get_precomputed_fp(name)
    if fp is not None:
        return fp

    # Strategy 2: compute from SMILES via rdkit
    if smiles and _check_rdkit():
        fp = _compute_fp(smiles)
        if fp is not None:
            return fp

    # Strategy 3: resolve SMILES from PubChem, then compute
    if not smiles and _check_rdkit():
        resolved = _fetch_smiles_pubchem(name)
        if resolved:
            return _compute_fp(resolved)

    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CORE LOGIC
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _run_similarity(
    disease: str,
    candidate_smiles: str | None,
    candidate_name: str | None,
    min_similarity: float,
    top_k: int,
) -> dict:
    """
    Core similarity screening logic. Runs in thread pool.

    Works with precomputed fingerprint database (no rdkit needed) or
    with rdkit for on-the-fly FP computation. Three modes:

    1. candidate provided → compare against approved drugs + FP database
    2. No candidate → screen approved drugs against FP database
    3. Fallback: pairwise comparison among approved drugs
    """
    _load_fp_database()

    has_rdkit = _check_rdkit()
    has_db = _fp_matrix is not None and len(_fp_matrix) > 0

    if not has_rdkit and not has_db:
        return {
            "error": "No fingerprint database found and RDKit not installed.",
            "hint": (
                "Either place morgan_fps.npy + fp_drug_index.json in "
                f"{_data_dir}/fingerprints/ or pip install rdkit-pypi"
            ),
        }

    disease_key = disease.lower().strip()
    approved_names = APPROVED_DRUGS.get(disease_key, [])

    # If disease not in our map, try substring matching
    if not approved_names:
        for k, v in APPROVED_DRUGS.items():
            if k in disease_key or disease_key in k:
                approved_names = v
                break

    # ── Mode 1: Compare candidate against approved drugs ──
    if candidate_smiles or candidate_name:
        # Get candidate fingerprint
        cand_label = candidate_name or "query"
        query_fp = None

        # Try precomputed first (by name)
        if candidate_name:
            query_fp = _get_precomputed_fp(candidate_name)

        # Then try rdkit from SMILES
        if query_fp is None and candidate_smiles and has_rdkit:
            query_fp = _compute_fp(candidate_smiles)

        if query_fp is None:
            # Check if the drug is in the database at all
            in_db = candidate_name and candidate_name.strip().lower() in _name_to_idx
            return {
                "error": f"Could not compute fingerprint for '{cand_label}'.",
                "hint": (
                    "Drug not found in precomputed database."
                    + (" RDKit not installed for on-the-fly computation."
                       if not has_rdkit else " RDKit could not parse the SMILES.")
                ),
                "in_precomputed_db": in_db,
            }

        similarities = []
        resolved_count = 0

        for name in approved_names:
            ref_fp = _get_fp(name)
            if ref_fp is None:
                similarities.append({
                    "approved_drug": name,
                    "tanimoto": None,
                    "note": "Fingerprint not available (not in DB, no rdkit)",
                })
                continue

            sim = _tanimoto_pair(query_fp, ref_fp)
            resolved_count += 1
            similarities.append({
                "approved_drug": name,
                "tanimoto": round(sim, 4),
                "interpretation": _interpret(sim),
            })

        # Sort by tanimoto (None values last)
        similarities.sort(
            key=lambda x: x.get("tanimoto") or -1.0,
            reverse=True,
        )
        max_sim = max(
            (s["tanimoto"] for s in similarities if s.get("tanimoto") is not None),
            default=0.0,
        )

        # Also check against pre-computed FP database
        db_hits = []
        if has_db:
            scores = _tanimoto_1_vs_all(query_fp, _fp_matrix, _bit_counts)
            mask = scores >= min_similarity
            if mask.any():
                valid_idx = np.where(mask)[0]
                sorted_idx = valid_idx[np.argsort(scores[valid_idx])[::-1]][:top_k]
                for idx in sorted_idx:
                    entry = _drug_index[idx]
                    db_hits.append({
                        "drug_name": entry.get("name", f"drug_{idx}"),
                        "drug_id": entry.get("id", ""),
                        "tanimoto": round(float(scores[idx]), 4),
                        "interpretation": _interpret(float(scores[idx])),
                    })

        return {
            "mode": "candidate_vs_approved",
            "candidate": cand_label,
            "candidate_smiles": candidate_smiles,
            "disease": disease,
            "approved_drugs_compared": resolved_count,
            "approved_drugs_unavailable": len(approved_names) - resolved_count,
            "max_similarity": round(max_sim, 4),
            "structurally_similar": max_sim >= 0.50,
            "similarities": similarities,
            "database_hits": db_hits[:top_k] if db_hits else [],
            "database_size": len(_drug_index) if _drug_index else 0,
            "used_precomputed_fps": not has_rdkit,
            "summary": (
                f"Compared against {resolved_count} approved drugs. "
                f"Max Tanimoto = {max_sim:.3f}"
                + (f" ({_interpret(max_sim)}). " if max_sim > 0 else ". ")
                + (f"Also found {len(db_hits)} hits in FP database "
                   f"(≥{min_similarity:.2f})."
                   if db_hits else "")
                + (" [precomputed FPs, no rdkit]" if not has_rdkit else "")
            ),
        }

    # ── Mode 2: Screen approved drugs against FP database ──
    if has_db and approved_names:
        all_hits: dict[str, dict] = {}

        for name in approved_names:
            query_fp = _get_fp(name)
            if query_fp is None:
                continue

            scores = _tanimoto_1_vs_all(query_fp, _fp_matrix, _bit_counts)
            mask = scores >= min_similarity
            if not mask.any():
                continue

            valid_idx = np.where(mask)[0]
            sorted_idx = valid_idx[np.argsort(scores[valid_idx])[::-1]][:top_k]

            for idx in sorted_idx:
                entry = _drug_index[idx]
                drug_key = entry.get("name", str(idx)).upper()
                sim = float(scores[idx])
                if drug_key not in all_hits or sim > all_hits[drug_key]["tanimoto"]:
                    all_hits[drug_key] = {
                        "drug_name": entry.get("name", f"drug_{idx}"),
                        "drug_id": entry.get("id", ""),
                        "tanimoto": round(sim, 4),
                        "interpretation": _interpret(sim),
                        "similar_to": name,
                    }

        hits = sorted(all_hits.values(), key=lambda x: x["tanimoto"], reverse=True)
        return {
            "mode": "approved_vs_database",
            "disease": disease,
            "approved_drugs_screened": len(approved_names),
            "database_size": len(_drug_index),
            "hits_found": len(hits),
            "min_similarity_threshold": min_similarity,
            "hits": hits[:top_k],
        }

    # ── Fallback: pairwise comparison among approved drugs ──
    if approved_names:
        fps: list[tuple[str, np.ndarray]] = []
        for name in approved_names:
            fp = _get_fp(name)
            if fp is not None:
                fps.append((name, fp))

        if len(fps) >= 2:
            pairs = []
            for i in range(len(fps)):
                for j in range(i + 1, len(fps)):
                    sim = _tanimoto_pair(fps[i][1], fps[j][1])
                    pairs.append({
                        "drug_a": fps[i][0],
                        "drug_b": fps[j][0],
                        "tanimoto": round(sim, 4),
                        "interpretation": _interpret(sim),
                    })
            pairs.sort(key=lambda x: x["tanimoto"], reverse=True)
            return {
                "mode": "pairwise_approved",
                "disease": disease,
                "drugs_compared": len(fps),
                "pairs": pairs,
            }

        return {
            "error": "Could not resolve fingerprints for approved drugs.",
            "disease": disease,
            "drugs_attempted": approved_names,
            "hint": "Drugs not in precomputed DB and rdkit not available."
                    if not has_rdkit else "PubChem lookup failed.",
        }

    return {
        "error": f"No approved drugs known for '{disease}' and no candidate provided.",
        "hint": "Provide candidate_smiles or candidate_name, or use a supported "
                "disease: " + ", ".join(sorted(APPROVED_DRUGS.keys())),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  @tool DEFINITION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@tool(
    "molecular_similarity",
    "Compare drug structures using Morgan/ECFP4 fingerprints (2048-bit) and "
    "Tanimoto coefficient. Works with precomputed fingerprint database (fast, "
    "no dependencies) or RDKit for on-the-fly computation. "
    "Two modes: (1) Given candidate_name or candidate_smiles, compare against "
    "approved drugs for the disease + the pre-computed FP database. (2) Given "
    "only a disease, screen approved drugs against the FP database. "
    "Tanimoto ≥ 0.85 = very high, ≥ 0.50 = moderate (our repurposing threshold). "
    "Fast: <5ms for database screening.",
    {
        "type": "object",
        "properties": {
            "disease": {
                "type": "string",
                "description": "Disease name (for approved drug reference set).",
            },
            "candidate_smiles": {
                "type": "string",
                "description": "SMILES of candidate drug to compare. Get from "
                "KG discovery results or pass a drug name (will auto-resolve "
                "via PubChem).",
            },
            "candidate_name": {
                "type": "string",
                "description": "Name of the candidate drug (for labeling).",
            },
            "min_similarity": {
                "type": "number",
                "description": "Minimum Tanimoto for database hits (default 0.40).",
                "minimum": 0.0,
                "maximum": 1.0,
            },
            "top_k": {
                "type": "integer",
                "description": "Max similar drugs to return (default 20).",
                "minimum": 1,
                "maximum": 100,
            },
        },
        "required": ["disease"],
    },
)
async def molecular_similarity_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Molecular similarity tool handler."""
    loop = asyncio.get_running_loop()

    candidate = args.get("candidate_smiles")
    candidate_name = args.get("candidate_name")

    # If candidate looks like a drug name (not SMILES), try to resolve
    if candidate and not any(c in candidate for c in ("(", "=", "#", "[", "\\", "/")):
        # It's a drug name, not SMILES
        if not candidate_name:
            candidate_name = candidate
            args["candidate_name"] = candidate

        # Check precomputed database first (instant, no PubChem needed)
        _load_fp_database()
        if candidate.strip().lower() in _name_to_idx:
            # Found in precomputed DB — don't need SMILES at all
            args.pop("candidate_smiles", None)
            logger.info("Found %s in precomputed FP database", candidate)
        else:
            # Not in DB — resolve SMILES via PubChem for rdkit
            resolved = await loop.run_in_executor(_pool, _fetch_smiles_pubchem, candidate)
            if resolved:
                args["candidate_smiles"] = resolved
            else:
                args.pop("candidate_smiles", None)
                # Don't error yet — _run_similarity will handle it

    try:
        result = await loop.run_in_executor(
            _pool,
            _run_similarity,
            args["disease"],
            args.get("candidate_smiles"),
            args.get("candidate_name"),
            args.get("min_similarity", 0.40),
            args.get("top_k", 20),
        )

        is_err = "error" in result and not any(
            k in result for k in ("similarities", "hits", "approved_drugs", "pairs")
        )
        return {
            "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
            **({"is_error": True} if is_err else {}),
        }
    except Exception as e:
        logger.exception("molecular_similarity failed")
        return {
            "content": [{"type": "text", "text": json.dumps({
                "error": str(e), "tool": "molecular_similarity",
            })}],
            "is_error": True,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EXPORTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SIM_TOOLS = [molecular_similarity_tool]

SIM_TOOL_NAMES = [
    "mcp__drugrescue__molecular_similarity",
]
