"""
Molecular Docking Tool (NVIDIA DiffDock)
=========================================
Claude Agent SDK Custom Tool — TreeHacks 2026

Takes a drug SMILES + disease → resolves disease-relevant protein targets →
calls NVIDIA NIM DiffDock API for blind molecular docking → returns
predicted binding poses with confidence scores.

API:  POST https://health.api.nvidia.com/v1/biology/mit/diffdock
Auth: Bearer token (NVIDIA_API_KEY, prefix nvapi-...)
Free: 1,000 credits at build.nvidia.com

DiffDock performs BLIND docking (no pocket specification needed).
Confidence scores reflect predicted pose geometry accuracy, NOT binding
affinity. Higher confidence = more reliable predicted pose.

SDK contract:
    @tool(name, description, input_schema)
    async def handler(args: dict) → {"content": [{"type": "text", "text": "JSON"}]}

When registered under server key "drugrescue":
    mcp__drugrescue__molecular_docking
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

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
#  PUBCHEM SMILES RESOLUTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_smiles_cache: dict[str, str | None] = {}

PUBCHEM_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{}/property/CanonicalSMILES/JSON"


def _fetch_smiles(drug_name: str) -> str | None:
    """Fetch canonical SMILES from PubChem via requests. Cached."""
    key = drug_name.strip().lower()
    if key in _smiles_cache:
        return _smiles_cache[key]
    encoded = urllib.parse.quote(drug_name.strip(), safe="")
    try:
        import requests as _req
        resp = _req.get(PUBCHEM_URL.format(encoded), timeout=10)
        if resp.status_code == 404:
            _smiles_cache[key] = None
            return None
        resp.raise_for_status()
        data = resp.json()
        props = data.get("PropertyTable", {}).get("Properties", [])
        if props:
            smiles = props[0].get("CanonicalSMILES")
            if smiles:
                _smiles_cache[key] = smiles
                return smiles
    except Exception as e:
        logger.warning("PubChem SMILES lookup failed for %s: %s", drug_name, e)
    _smiles_cache[key] = None
    return None


def _is_smiles(s: str) -> bool:
    """Heuristic: SMILES contain these chars, drug names don't."""
    return any(c in s for c in ("(", "=", "#", "[", "\\", "/"))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DISEASE → PROTEIN TARGET MAPPING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# {disease: [{protein, pdb_id, role}, ...]}
# PDB IDs are curated crystal structures with good resolution.
DISEASE_TARGETS: dict[str, list[dict]] = {
    "glioblastoma": [
        {"protein": "EGFR", "pdb_id": "1M17",
         "role": "Epidermal growth factor receptor — amplified in ~60% GBM"},
        {"protein": "IDH1", "pdb_id": "3INM",
         "role": "Isocitrate dehydrogenase 1 — mutated in secondary GBM"},
        {"protein": "PDGFRA", "pdb_id": "5GRN",
         "role": "Platelet-derived growth factor receptor alpha"},
        {"protein": "MGMT", "pdb_id": "1EH6",
         "role": "O6-methylguanine-DNA methyltransferase — TMZ resistance"},
    ],
    "alzheimer": [
        {"protein": "BACE1", "pdb_id": "6EJ2",
         "role": "Beta-secretase 1 — amyloid precursor protein cleavage"},
        {"protein": "AChE", "pdb_id": "4EY7",
         "role": "Acetylcholinesterase — cholinergic signaling"},
        {"protein": "GSK3B", "pdb_id": "1Q5K",
         "role": "Glycogen synthase kinase 3 beta — tau phosphorylation"},
        {"protein": "NMDAR", "pdb_id": "4PE5",
         "role": "NMDA receptor — excitotoxicity"},
    ],
    "parkinson": [
        {"protein": "MAO-B", "pdb_id": "2V5Z",
         "role": "Monoamine oxidase B — dopamine metabolism"},
        {"protein": "LRRK2", "pdb_id": "6VNO",
         "role": "Leucine-rich repeat kinase 2 — most common PD mutation"},
        {"protein": "COMT", "pdb_id": "3BWM",
         "role": "Catechol-O-methyltransferase — levodopa metabolism"},
    ],
    "als": [
        {"protein": "SOD1", "pdb_id": "2C9V",
         "role": "Superoxide dismutase 1 — mutated in familial ALS"},
        {"protein": "TDP-43", "pdb_id": "4BS2",
         "role": "TAR DNA-binding protein 43 — aggregation in ALS"},
    ],
    "breast cancer": [
        {"protein": "ER-alpha", "pdb_id": "1ERR",
         "role": "Estrogen receptor alpha — ER+ breast cancer"},
        {"protein": "HER2", "pdb_id": "3PP0",
         "role": "Human epidermal growth factor receptor 2"},
        {"protein": "Aromatase", "pdb_id": "3EQM",
         "role": "Cytochrome P450 19A1 — estrogen biosynthesis"},
    ],
    "depression": [
        {"protein": "SERT", "pdb_id": "5I6X",
         "role": "Serotonin transporter — SSRI target"},
        {"protein": "MAO-A", "pdb_id": "2Z5X",
         "role": "Monoamine oxidase A — serotonin/norepinephrine metabolism"},
    ],
    "diabetes": [
        {"protein": "DPP-4", "pdb_id": "1X70",
         "role": "Dipeptidyl peptidase-4 — incretin degradation"},
        {"protein": "PPARg", "pdb_id": "2PRG",
         "role": "Peroxisome proliferator-activated receptor gamma"},
    ],
    "epilepsy": [
        {"protein": "GABA-AT", "pdb_id": "1OHV",
         "role": "GABA aminotransferase — GABA metabolism"},
    ],
    "multiple myeloma": [
        {"protein": "Cereblon", "pdb_id": "4CI1",
         "role": "E3 ubiquitin ligase substrate receptor — IMiD target"},
        {"protein": "Proteasome", "pdb_id": "5LF3",
         "role": "20S proteasome — bortezomib target"},
    ],
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  API CALLS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DIFFDOCK_URL = "https://health.api.nvidia.com/v1/biology/mit/diffdock"
PDB_URL = "https://files.rcsb.org/download/{}.pdb"


def _fetch_pdb_atoms(pdb_id: str) -> str | None:
    """Download PDB from RCSB and extract ATOM lines (DiffDock requirement)."""
    url = PDB_URL.format(pdb_id)
    try:
        from ._http import _urlopen_with_ssl_retry
        with _urlopen_with_ssl_retry(url, timeout=30) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        atom_lines = [l for l in text.split("\n") if l.startswith("ATOM")]
        if not atom_lines:
            return None
        return "\n".join(atom_lines)
    except Exception as e:
        logger.warning("Failed to fetch PDB %s: %s", pdb_id, e)
        return None


def _run_diffdock(smiles: str, protein_pdb: str,
                  num_poses: int) -> dict:
    """Call NVIDIA NIM DiffDock API."""
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {"status": "error", "error": "NVIDIA_API_KEY not set"}

    payload = json.dumps({
        "ligand": smiles,
        "ligand_file_type": "txt",
        "protein": protein_pdb,
        "num_poses": num_poses,
        "time_divisions": 20,
        "steps": 18,
        "save_trajectory": False,
        "is_staged": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        DIFFDOCK_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        from ._http import _urlopen_with_ssl_retry
        with _urlopen_with_ssl_retry(req, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 402:
            return {"status": "error", "error": "NVIDIA credits exhausted"}
        body = e.read().decode("utf-8", errors="replace")[:500]
        return {"status": "error", "error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CORE LOGIC
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _run_docking_screen(drug_smiles: str, drug_name: str | None,
                        disease: str, num_poses: int,
                        max_targets: int) -> dict:
    """
    Dock a drug against disease-relevant protein targets.
    Runs synchronously (thread pool).
    """
    disease_key = disease.lower().strip()
    targets = DISEASE_TARGETS.get(disease_key, [])

    if not targets:
        return {
            "error": f"No protein targets configured for '{disease}'",
            "configured_diseases": list(DISEASE_TARGETS.keys()),
            "hint": "Provide a disease with known protein targets.",
        }

    targets = targets[:max_targets]

    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {
            "error": "NVIDIA_API_KEY not set. Get one at https://build.nvidia.com/",
            "note": "DiffDock requires NVIDIA NIM API access (free 1000 credits).",
        }

    docking_results = []
    for target in targets:
        protein_pdb = _fetch_pdb_atoms(target["pdb_id"])
        if not protein_pdb:
            docking_results.append({
                "protein": target["protein"],
                "pdb_id": target["pdb_id"],
                "role": target["role"],
                "status": "error",
                "error": f"Failed to fetch PDB {target['pdb_id']}",
            })
            continue

        result = _run_diffdock(drug_smiles, protein_pdb, num_poses)

        if result.get("status") == "error":
            docking_results.append({
                "protein": target["protein"],
                "pdb_id": target["pdb_id"],
                "role": target["role"],
                "status": "error",
                "error": result["error"],
            })
            continue

        # Parse DiffDock response
        confidences = result.get("position_confidence", [])
        if confidences:
            best = max(confidences)
            docking_results.append({
                "protein": target["protein"],
                "pdb_id": target["pdb_id"],
                "role": target["role"],
                "status": "success",
                "num_poses": len(confidences),
                "best_confidence": round(best, 4),
                "all_confidences": [round(c, 4) for c in confidences],
                "interpretation": (
                    "High confidence — likely binds this target"
                    if best > 0.0 else
                    "Low confidence — binding unlikely"
                ),
            })
        else:
            docking_results.append({
                "protein": target["protein"],
                "pdb_id": target["pdb_id"],
                "role": target["role"],
                "status": "no_poses",
                "note": "DiffDock returned no valid poses",
            })

        time.sleep(0.5)  # Rate limiting

    successful = [r for r in docking_results if r["status"] == "success"]
    best_overall = max((r["best_confidence"] for r in successful), default=None)

    return {
        "drug": drug_name or "unknown",
        "drug_smiles": drug_smiles,
        "disease": disease,
        "targets_attempted": len(targets),
        "targets_successful": len(successful),
        "best_overall_confidence": round(best_overall, 4) if best_overall else None,
        "best_target": (
            max(successful, key=lambda r: r["best_confidence"])["protein"]
            if successful else None
        ),
        "summary": (
            f"Docked against {len(targets)} targets. "
            f"{len(successful)} successful. "
            + (f"Best binding: {best_overall:.3f} confidence at "
               f"{max(successful, key=lambda r: r['best_confidence'])['protein']}"
               if successful else "No successful dockings.")
        ),
        "results": docking_results,
        "note": "Confidence scores reflect pose geometry accuracy, NOT binding "
                "affinity. Use as a filter, not a ranking metric.",
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  @tool DEFINITION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@tool(
    "molecular_docking",
    "Run molecular docking using NVIDIA DiffDock to predict how a drug binds to "
    "disease-relevant protein targets. Takes a drug's SMILES string OR name (will "
    "auto-resolve via PubChem) and a disease name, resolves the disease to protein "
    "targets (with PDB IDs), and runs blind docking against each target. Returns "
    "confidence scores per target and per pose. IMPORTANT: confidence scores are "
    "pose geometry predictions, NOT binding affinities — use as a filter (does it "
    "dock at all?) not a ranking metric. "
    "Requires NVIDIA_API_KEY env var. ~10-30 seconds per target.",
    {
        "type": "object",
        "properties": {
            "drug_smiles": {
                "type": "string",
                "description": "Drug SMILES string OR drug name. If a name is "
                "given (no special chars), SMILES will be fetched from PubChem.",
            },
            "drug_name": {
                "type": "string",
                "description": "Optional: drug name for labeling results.",
            },
            "disease": {
                "type": "string",
                "description": "Disease name for protein target lookup. Has targets "
                "for: glioblastoma, alzheimer, parkinson, als, breast cancer, "
                "depression, diabetes, epilepsy, multiple myeloma.",
            },
            "num_poses": {
                "type": "integer",
                "description": "Binding poses per target (default 3, max 10)",
                "minimum": 1,
                "maximum": 10,
            },
            "max_targets": {
                "type": "integer",
                "description": "Max protein targets to dock against (default 3). "
                "More targets = more comprehensive but slower.",
                "minimum": 1,
                "maximum": 6,
            },
        },
        "required": ["drug_smiles", "disease"],
    },
)
async def molecular_docking_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Molecular docking tool handler."""
    loop = asyncio.get_running_loop()

    # Auto-resolve drug names to SMILES via PubChem
    drug_input = args["drug_smiles"]
    if not _is_smiles(drug_input):
        resolved = await loop.run_in_executor(_pool, _fetch_smiles, drug_input)
        if resolved:
            if not args.get("drug_name"):
                args["drug_name"] = drug_input
            args["drug_smiles"] = resolved
        else:
            return {
                "content": [{"type": "text", "text": json.dumps({
                    "error": f"Could not resolve SMILES for '{drug_input}' via PubChem.",
                    "hint": "Provide a canonical SMILES string directly.",
                })}],
                "is_error": True,
            }

    try:
        result = await loop.run_in_executor(
            _pool,
            _run_docking_screen,
            args["drug_smiles"],
            args.get("drug_name"),
            args["disease"],
            args.get("num_poses", 3),
            args.get("max_targets", 3),
        )

        is_err = "error" in result and "results" not in result
        return {
            "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
            **({"is_error": True} if is_err else {}),
        }
    except Exception as e:
        logger.exception("molecular_docking failed")
        return {
            "content": [{"type": "text", "text": json.dumps({
                "error": str(e), "tool": "molecular_docking",
            })}],
            "is_error": True,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EXPORTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DOCK_TOOLS = [molecular_docking_tool]

DOCK_TOOL_NAMES = [
    "mcp__drugrescue__molecular_docking",
]
