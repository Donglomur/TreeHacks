"""
discover.py — KG-Driven Candidate Discovery
=============================================

Input:  a disease name
Output: ranked, enriched drug candidates for all downstream agents

    from drug_rescue.engines.discover import discover_candidates
    result = discover_candidates("glioblastoma", data_dir="./data")

    for c in result.candidates:
        c.drug_name       # "Metformin"
        c.chembl_id       # "CHEMBL1431"
        c.smiles          # "CN(C)C(=N)..."
        c.kg_percentile   # 97.3
        c.status          # "dropped"
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

from .scorer import DRKGScorer, KGResult

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DATA CLASSES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class Candidate:
    """
    A drug candidate discovered by the Knowledge Graph and enriched
    from the dropped-drugs database.
    """
    # Identity
    drug_name: str                       # Human-readable or DrugBank ID
    drkg_entity: str                     # "Compound::DB00331"

    # Database cross-ref
    chembl_id: Optional[str] = None
    drugbank_id: Optional[str] = None
    smiles: Optional[str] = None
    inchikey: Optional[str] = None
    max_phase: Optional[int] = None      # 1, 2, or 3
    molecule_type: Optional[str] = None

    # KG scores
    kg_score: float = 0.0
    kg_percentile: float = 0.0
    kg_z_score: float = 0.0
    kg_normalized: float = 0.0
    kg_rank: int = 0
    kg_relation: str = ""

    # Classification
    #   "dropped"    — Phase I-III, never approved
    #   "withdrawn"  — was approved, then pulled
    #   "novel"      — in DRKG but not in our database
    status: str = "novel"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DiscoveryResult:
    """Everything the orchestrator needs from the discovery phase."""
    disease: str
    candidates: list[Candidate]
    total_compounds_scored: int
    timing_ms: float
    method: str
    disease_entities_used: list[str]
    treatment_relations_used: list[str]
    stats: dict = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "disease": self.disease,
            "candidates": [c.to_dict() for c in self.candidates],
            "total_compounds_scored": self.total_compounds_scored,
            "timing_ms": self.timing_ms,
            "method": self.method,
            "stats": self.stats,
            "error": self.error,
        }

    @property
    def drug_names(self) -> list[str]:
        return [c.drug_name for c in self.candidates]

    @property
    def smiles_map(self) -> dict[str, str]:
        return {c.drug_name: c.smiles for c in self.candidates if c.smiles}

    @property
    def dropped(self) -> list[Candidate]:
        return [c for c in self.candidates if c.status == "dropped"]

    @property
    def novel(self) -> list[Candidate]:
        return [c for c in self.candidates if c.status == "novel"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DATABASE ENRICHER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class _DBEnricher:
    """Loads dropped_drugs.db + optional kg_entity_lookup.json for cross-referencing."""

    def __init__(self, db_path: str):
        self._by_drugbank: dict[str, dict] = {}
        self._by_chembl: dict[str, dict] = {}
        self._by_name: dict[str, dict] = {}
        self._kg_lookup: dict[str, dict] = {}  # Compound::X → {drug_name, chembl_id, ...}
        self._withdrawn: set[str] = set()
        self._loaded = False

        if not Path(db_path).exists():
            logger.warning("DB not found: %s", db_path)
            return

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        for row in conn.execute(
            "SELECT drug_name, chembl_id, drugbank_id, smiles, inchikey, "
            "max_phase, molecule_type FROM dropped_drugs"
        ):
            entry = dict(row)
            entry["status"] = "dropped"
            name = (entry.get("drug_name") or "").lower().strip()
            db_id = (entry.get("drugbank_id") or "").upper().strip()
            ch_id = (entry.get("chembl_id") or "").upper().strip()
            if db_id: self._by_drugbank[db_id] = entry
            if ch_id: self._by_chembl[ch_id] = entry
            if name:  self._by_name[name] = entry

        for row in conn.execute("SELECT drug_name FROM withdrawn_drugs"):
            if row["drug_name"]:
                self._withdrawn.add(row["drug_name"].lower().strip())

        conn.close()

        # Load PubChem-resolved lookup (created by resolve_all_compounds.py)
        lookup_path = Path(db_path).parent / "kg_entity_lookup.json"
        if lookup_path.exists():
            try:
                with open(lookup_path) as f:
                    self._kg_lookup = json.load(f)
                logger.info("Loaded %d entity lookups from %s",
                            len(self._kg_lookup), lookup_path)
            except Exception as e:
                logger.warning("Could not load entity lookup: %s", e)

        self._loaded = True
        logger.info("DB enricher: %d by drugbank, %d by chembl, %d by name, %d kg_lookup",
                     len(self._by_drugbank), len(self._by_chembl),
                     len(self._by_name), len(self._kg_lookup))

    def enrich(self, drkg_entity: str) -> dict:
        """Look up a Compound:: entity. Returns {} if not found."""
        if not self._loaded:
            return {}
        cid = drkg_entity.replace("Compound::", "").strip()

        # ── Direct DB lookups ──
        entry = None
        if cid.upper().startswith("DB"):
            entry = self._by_drugbank.get(cid.upper())
        elif cid.upper().startswith("CHEMBL"):
            entry = self._by_chembl.get(cid.upper())
        if not entry:
            entry = self._by_name.get(cid.lower())

        # ── PubChem lookup fallback ──
        # If direct lookup failed, use the resolved entity lookup
        if not entry and drkg_entity in self._kg_lookup:
            lookup = self._kg_lookup[drkg_entity]
            # Try to match via the resolved ChEMBL ID
            resolved_chembl = (lookup.get("chembl_id") or "").upper().strip()
            if resolved_chembl and resolved_chembl in self._by_chembl:
                entry = self._by_chembl[resolved_chembl]
            # Try to match via the resolved drug name
            elif lookup.get("drug_name"):
                resolved_name = lookup["drug_name"].lower().strip()
                if resolved_name in self._by_name:
                    entry = self._by_name[resolved_name]

            # If still no DB match but we have a resolved name,
            # return as "novel" with the resolved name (better than raw ID)
            if not entry and lookup.get("drug_name"):
                return {
                    "drug_name": lookup["drug_name"],
                    "chembl_id": lookup.get("chembl_id"),
                    "drugbank_id": lookup.get("drugbank_id"),
                    "smiles": lookup.get("smiles"),
                    "max_phase": lookup.get("max_phase"),
                    "status": "novel",
                    "molecule_type": None,
                    "inchikey": None,
                }

        if not entry:
            return {}

        # Check withdrawn
        name = (entry.get("drug_name") or "").lower().strip()
        if name in self._withdrawn:
            entry = dict(entry)
            entry["status"] = "withdrawn"
        return entry


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN FUNCTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def discover_candidates(
    disease: str,
    data_dir: str = "./data",
    top_k: int = 100,
    max_candidates: int = 30,
    min_percentile: float = 75.0,
    include_novel: bool = True,
    require_smiles: bool = False,
) -> DiscoveryResult:
    """
    Discover drug repurposing candidates for a disease.

    1. Score ALL ~24K compounds in DRKG using RotatE embeddings
    2. Take top-k
    3. Cross-reference each against dropped_drugs.db
    4. Classify as dropped / withdrawn / novel
    5. Return enriched candidates
    """
    t0 = time.perf_counter()
    data = Path(data_dir)

    # Load scorer
    scorer = DRKGScorer(
        embeddings_dir=str(data / "embeddings"),
        db_path=str(data / "database" / "dropped_drugs.db"),
    )

    # Score ALL compounds
    kg = scorer.score_disease(disease, top_k=top_k)
    if kg.error:
        return DiscoveryResult(
            disease=disease, candidates=[],
            total_compounds_scored=0, timing_ms=0,
            method=scorer.method, disease_entities_used=[],
            treatment_relations_used=[], error=kg.error,
        )

    # Enrich from database
    enricher = _DBEnricher(str(data / "database" / "dropped_drugs.db"))

    candidates: list[Candidate] = []
    stats = {"dropped": 0, "withdrawn": 0, "novel": 0,
             "skipped_percentile": 0, "skipped_smiles": 0}

    for pred in kg.predictions:
        if pred.percentile < min_percentile:
            stats["skipped_percentile"] += 1
            continue

        db = enricher.enrich(pred.drug_entity)

        if db:
            c = Candidate(
                drug_name=db.get("drug_name") or pred.drug_name,
                drkg_entity=pred.drug_entity,
                chembl_id=db.get("chembl_id"),
                drugbank_id=db.get("drugbank_id"),
                smiles=db.get("smiles") or None,
                inchikey=db.get("inchikey"),
                max_phase=db.get("max_phase"),
                molecule_type=db.get("molecule_type"),
                kg_score=pred.score,
                kg_percentile=pred.percentile,
                kg_z_score=pred.z_score,
                kg_normalized=pred.normalized_score,
                kg_rank=pred.rank,
                kg_relation=pred.relation_used,
                status=db.get("status", "dropped"),
            )
        else:
            if not include_novel:
                continue
            cid = pred.drug_entity.replace("Compound::", "")
            c = Candidate(
                drug_name=pred.drug_name,
                drkg_entity=pred.drug_entity,
                drugbank_id=cid.upper() if cid.startswith("DB") else None,
                kg_score=pred.score,
                kg_percentile=pred.percentile,
                kg_z_score=pred.z_score,
                kg_normalized=pred.normalized_score,
                kg_rank=pred.rank,
                kg_relation=pred.relation_used,
                status="novel",
            )

        if require_smiles and not c.smiles:
            stats["skipped_smiles"] += 1
            continue

        stats[c.status] = stats.get(c.status, 0) + 1
        candidates.append(c)
        if len(candidates) >= max_candidates:
            break

    elapsed = (time.perf_counter() - t0) * 1000

    return DiscoveryResult(
        disease=disease,
        candidates=candidates,
        total_compounds_scored=kg.total_compounds_scored,
        timing_ms=round(elapsed, 1),
        method=kg.method,
        disease_entities_used=kg.disease_entities_used,
        treatment_relations_used=kg.treatment_relations_used,
        stats=stats,
    )
