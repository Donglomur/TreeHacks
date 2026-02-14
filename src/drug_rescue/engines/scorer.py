"""
scorer.py — DRKG Knowledge Graph Scoring Engine
================================================

Loads pre-trained RotatE (or TransE fallback) embeddings from data/embeddings/
and scores drug-disease pairs using vectorized complex-space math.

This is pure computation. No LLM. No network calls. Just numpy.

    scorer = DRKGScorer("./data/embeddings")
    result = scorer.score_disease("glioblastoma", top_k=50)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Pre-resolved DRKG entity IDs for demo diseases.
# Avoids fuzzy matching failures on stage.
DEMO_DISEASE_ENTITIES: dict[str, list[str]] = {
    "glioblastoma": ["Disease::MESH:D005909", "Disease::DOID:3068"],
    "alzheimer":    ["Disease::MESH:D000544", "Disease::DOID:10652"],
    "parkinson":    ["Disease::MESH:D010300", "Disease::DOID:14330"],
    "als":          ["Disease::MESH:D000690", "Disease::DOID:332"],
    "ipf":          ["Disease::MESH:D054990"],
    "multiple myeloma": ["Disease::MESH:D009101", "Disease::DOID:9538"],
    "breast cancer": ["Disease::MESH:D001943", "Disease::DOID:1612"],
    "lung cancer":  ["Disease::MESH:D008175"],
    "leukemia":     ["Disease::MESH:D007938"],
    "depression":   ["Disease::MESH:D003866", "Disease::DOID:1596"],
    "diabetes":     ["Disease::MESH:D003920"],
    "epilepsy":     ["Disease::MESH:D004827"],
}

# Relation name patterns that mean "drug treats disease" in DRKG.
TREATMENT_RELATION_PATTERNS = ["CtD", "T::Compound:Disease", "treats::Compound:Disease"]

# Verified DRKG entity IDs for drugs we know will appear in demos.
KNOWN_DRUGS: dict[str, str] = {
    "metformin": "Compound::DB00331",
    "riluzole": "Compound::DB00740",
    "temozolomide": "Compound::DB00853",
    "bevacizumab": "Compound::DB00112",
    "carmustine": "Compound::DB00262",
    "lomustine": "Compound::DB01206",
    "donepezil": "Compound::DB00843",
    "memantine": "Compound::DB01043",
    "levodopa": "Compound::DB01235",
    "carbidopa": "Compound::DB00190",
    "rasagiline": "Compound::DB01367",
    "selegiline": "Compound::DB01037",
    "thalidomide": "Compound::DB01041",
    "lenalidomide": "Compound::DB00480",
    "imatinib": "Compound::DB00619",
    "sorafenib": "Compound::DB00398",
    "erlotinib": "Compound::DB00530",
    "gefitinib": "Compound::DB00317",
    "tamoxifen": "Compound::DB00675",
    "doxorubicin": "Compound::DB00997",
    "cisplatin": "Compound::DB00515",
    "paclitaxel": "Compound::DB01229",
    "valproic acid": "Compound::DB00313",
    "lithium": "Compound::DB01356",
    "aspirin": "Compound::DB00945",
    "celecoxib": "Compound::DB00482",
    "simvastatin": "Compound::DB00641",
    "atorvastatin": "Compound::DB01076",
    "pioglitazone": "Compound::DB01132",
    "rosiglitazone": "Compound::DB00412",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DATA CLASSES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class KGPrediction:
    """One drug's score against a disease."""
    drug_entity: str           # "Compound::DB00945"
    drug_name: str             # "DB00945" or human-readable name
    score: float               # Raw RotatE/TransE distance (negative; higher = better)
    percentile: float          # Rank among ALL compounds (0-100)
    z_score: float             # Std devs above mean
    rank: int                  # 1 = best
    method: str                # "RotatE" or "TransE"
    relation_used: str         # "GNBR::T::Compound:Disease"
    normalized_score: float = 0.0  # 0-1 for orchestrator (20% weight)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class KGResult:
    """Complete scoring output for one disease query."""
    disease_query: str
    disease_entities_used: list[str]
    treatment_relations_used: list[str]
    method: str
    total_compounds_scored: int
    predictions: list[KGPrediction]
    timing_ms: float
    error: Optional[str] = None
    metadata: Optional[dict] = None

    def to_dict(self) -> dict:
        d = {
            "disease_query": self.disease_query,
            "disease_entities_used": self.disease_entities_used,
            "treatment_relations_used": self.treatment_relations_used,
            "method": self.method,
            "total_compounds_scored": self.total_compounds_scored,
            "predictions": [p.to_dict() for p in self.predictions],
            "timing_ms": self.timing_ms,
            "error": self.error,
        }
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    def get_drug(self, name: str) -> Optional[KGPrediction]:
        """Substring lookup by drug name or entity ID."""
        q = name.lower()
        for p in self.predictions:
            if q in p.drug_entity.lower() or q in p.drug_name.lower():
                return p
        return None

    def for_orchestrator(self) -> dict[str, dict]:
        """
        {drug_name: {kg_score, kg_percentile, kg_z_score, ...}}
        """
        return {
            p.drug_name: {
                "kg_score": p.normalized_score,
                "kg_percentile": p.percentile,
                "kg_z_score": p.z_score,
                "kg_raw_score": p.score,
                "kg_rank": p.rank,
                "kg_method": p.method,
                "kg_relation": p.relation_used,
            }
            for p in self.predictions
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NORMALIZER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def normalize_kg_score(percentile: float) -> float:
    """Percentile → 0-1. Non-linear: top 1% → 1.0, median → 0.30."""
    if percentile >= 99:   return 1.0
    elif percentile >= 95: return 0.85
    elif percentile >= 90: return 0.70
    elif percentile >= 75: return 0.50
    elif percentile >= 50: return 0.30
    else: return round(0.30 * percentile / 50.0, 4)  # 0→0.0, 50→0.30


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DRUG NAME RESOLVER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DrugNameResolver:
    """
    Maps drug names from other agents → DRKG Compound:: entity IDs.

    Resolution order:
      1. KNOWN_DRUGS hardcoded map
      2. Direct "Compound::{name}" match
      3. DrugBank ID (DB00xxx)
      4. ChEMBL ID (CHEMBLxxx)
      5. Database lookup: name → drugbank_id/chembl_id → entity
      6. Fuzzy substring match (last resort)
    """

    def __init__(self, entity_to_idx: dict[str, int], db_path: Optional[str] = None):
        self.entity_to_idx = entity_to_idx

        # Reverse index: ID → DRKG entity
        self._drugbank_to_entity: dict[str, str] = {}
        self._chembl_to_entity: dict[str, str] = {}
        for name in entity_to_idx:
            if not name.startswith("Compound::"):
                continue
            cid = name.replace("Compound::", "")
            if cid.startswith("DB"):
                self._drugbank_to_entity[cid.upper()] = name
            elif cid.startswith("CHEMBL"):
                self._chembl_to_entity[cid.upper()] = name

        # Database cross-ref
        self._db_name_to_drugbank: dict[str, str] = {}
        self._db_name_to_chembl: dict[str, str] = {}
        if db_path and Path(db_path).exists():
            try:
                conn = sqlite3.connect(db_path)
                for row in conn.execute("SELECT drug_name, chembl_id, drugbank_id FROM dropped_drugs"):
                    name, chembl, drugbank = row
                    if name:
                        key = name.lower().strip()
                        if drugbank:
                            self._db_name_to_drugbank[key] = drugbank.upper()
                        if chembl:
                            self._db_name_to_chembl[key] = chembl.upper()
                conn.close()
            except Exception as e:
                logger.warning("Could not load drug database for name resolution: %s", e)

    def resolve(self, drug_name: str) -> Optional[str]:
        """Resolve a drug name to a DRKG entity. Returns None if not found."""
        q = drug_name.strip()
        ql = q.lower()

        # 1. Hardcoded
        if ql in KNOWN_DRUGS:
            ent = KNOWN_DRUGS[ql]
            if ent in self.entity_to_idx:
                return ent

        # 2. Direct
        direct = f"Compound::{q}"
        if direct in self.entity_to_idx:
            return direct

        # 3. DrugBank ID
        if q.upper().startswith("DB"):
            ent = self._drugbank_to_entity.get(q.upper())
            if ent: return ent

        # 4. ChEMBL ID
        if q.upper().startswith("CHEMBL"):
            ent = self._chembl_to_entity.get(q.upper())
            if ent: return ent

        # 5. DB name → DrugBank → DRKG
        dbid = self._db_name_to_drugbank.get(ql)
        if dbid:
            ent = self._drugbank_to_entity.get(dbid)
            if ent: return ent

        # 6. DB name → ChEMBL → DRKG
        cid = self._db_name_to_chembl.get(ql)
        if cid:
            ent = self._chembl_to_entity.get(cid)
            if ent: return ent

        # 7. Fuzzy substring
        matches = [n for n in self.entity_to_idx if n.startswith("Compound::") and ql in n.lower()]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            return min(matches, key=len)

        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  THE SCORER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DRKGScorer:
    """
    Score drug-disease pairs using DRKG graph embeddings.

    Loads real RotatE embeddings (~97K entities, ~5.8M edges).
    Scores ALL compounds in < 1 second (vectorized numpy).
    """

    def __init__(self, embeddings_dir: str, db_path: Optional[str] = None):
        self.embeddings_dir = Path(embeddings_dir)
        self.db_path = db_path

        # Populated by _load()
        self.entity_emb: np.ndarray = np.array([])
        self.relation_emb: np.ndarray = np.array([])
        self.entity_to_idx: dict[str, int] = {}
        self.relation_to_idx: dict[str, int] = {}
        self.method: str = ""
        self.complex_dim: int = 0
        self.training_metadata: Optional[dict] = None

        # Populated by _build_indices()
        self.compound_indices: np.ndarray = np.array([], dtype=np.int64)
        self.compound_names: list[str] = []
        self.compound_embs: Optional[np.ndarray] = None
        self.resolver: Optional[DrugNameResolver] = None

        self._load()
        self._build_indices()

    # ── Loading ──

    def _load(self) -> None:
        d = self.embeddings_dir

        rotate_ent = d / "rotate_entity_embeddings.npy"
        rotate_rel = d / "rotate_relation_embeddings.npy"
        transe_ent = d / "transe_DRKG_TransE_l2_entity.npy"
        transe_rel = d / "transe_DRKG_TransE_l2_relation.npy"

        if rotate_ent.exists() and rotate_rel.exists():
            raw_ent = np.load(str(rotate_ent))
            raw_rel = np.load(str(rotate_rel))

            # RotatE embeddings are often stored as complex128.
            # Our scoring math expects [real_part | imag_part] layout (float64).
            if np.iscomplexobj(raw_ent):
                self.entity_emb = np.concatenate(
                    [raw_ent.real, raw_ent.imag], axis=1
                ).astype(np.float64)
                logger.info("Converted complex128 entity embeddings → real layout")
            else:
                self.entity_emb = raw_ent.astype(np.float64)

            if np.iscomplexobj(raw_rel):
                self.relation_emb = np.concatenate(
                    [raw_rel.real, raw_rel.imag], axis=1
                ).astype(np.float64)
                logger.info("Converted complex128 relation embeddings → real layout")
            else:
                self.relation_emb = raw_rel.astype(np.float64)

            self.method = "RotatE"
            self.complex_dim = self.entity_emb.shape[1] // 2
            logger.info("Loaded RotatE: %s (complex_dim=%d, %.0f MB)",
                        self.entity_emb.shape, self.complex_dim, self.entity_emb.nbytes / 1e6)
        elif transe_ent.exists() and transe_rel.exists():
            self.entity_emb = np.load(str(transe_ent)).astype(np.float64)
            self.relation_emb = np.load(str(transe_rel)).astype(np.float64)
            self.method = "TransE"
            self.complex_dim = 0
            logger.info("Loaded TransE: %s (%.0f MB)",
                        self.entity_emb.shape, self.entity_emb.nbytes / 1e6)
        else:
            raise FileNotFoundError(
                f"No embeddings in {d}. Expected rotate_entity_embeddings.npy "
                f"or transe_DRKG_TransE_l2_entity.npy"
            )

        # ID mappings
        json_idx = d / "entity_to_idx.json"
        tsv_ent = d / "transe_entities.tsv"

        if json_idx.exists():
            with open(json_idx) as f:
                self.entity_to_idx = json.load(f)
            with open(d / "relation_to_idx.json") as f:
                self.relation_to_idx = json.load(f)
        elif tsv_ent.exists():
            self.entity_to_idx = {}
            with open(tsv_ent) as f:
                for i, line in enumerate(f):
                    self.entity_to_idx[line.strip()] = i
            self.relation_to_idx = {}
            with open(d / "transe_relations.tsv") as f:
                for i, line in enumerate(f):
                    self.relation_to_idx[line.strip()] = i
        else:
            raise FileNotFoundError(f"No ID mappings in {d}")

        # Training metadata (optional)
        meta = d.parent / "models" / "rotate_model" / "metadata.json"
        if meta.exists():
            with open(meta) as f:
                self.training_metadata = json.load(f)

    def _build_indices(self) -> None:
        indices, names = [], []
        for name, idx in self.entity_to_idx.items():
            if name.startswith("Compound::"):
                indices.append(idx)
                names.append(name)
        self.compound_indices = np.array(indices, dtype=np.int64)
        self.compound_names = names
        self.compound_embs = self.entity_emb[self.compound_indices]

        self.resolver = DrugNameResolver(self.entity_to_idx, db_path=self.db_path)
        logger.info("Indexed %d compounds (%.0f MB pre-fetched)",
                     len(names), self.compound_embs.nbytes / 1e6)

    # ── Entity Resolution ──

    def resolve_disease(self, query: str) -> list[str]:
        """Disease name → DRKG entity IDs. Demo entities checked first."""
        q = query.lower().strip()
        for key, entities in DEMO_DISEASE_ENTITIES.items():
            if key in q or q in key:
                valid = [e for e in entities if e in self.entity_to_idx]
                if valid:
                    return valid
        if query in self.entity_to_idx:
            return [query]
        return [n for n in self.entity_to_idx if n.startswith("Disease::") and q in n.lower()][:10]

    def find_treatment_relations(self) -> list[tuple[str, int]]:
        """Find all treatment-type relations in the graph."""
        return [
            (name, idx) for name, idx in self.relation_to_idx.items()
            if any(p in name for p in TREATMENT_RELATION_PATTERNS)
        ]

    # ── Scoring (THE CRITICAL MATH) ──

    def _score_rotate(self, heads: np.ndarray, relation: np.ndarray, tail: np.ndarray) -> np.ndarray:
        """
        RotatE: h ∘ r ≈ t — element-wise COMPLEX multiplication.

        (a+bi)(c+di) = (ac-bd) + (ad+bc)i

        The cookbook had a critical bug: naive h*r (element-wise real multiply).
        That ignores the complex structure entirely. Difference: ~0.748 on real data.
        """
        d = self.complex_dim
        re_h, im_h = heads[:, :d], heads[:, d:]
        re_r, im_r = relation[:d], relation[d:]
        re_t, im_t = tail[:d], tail[d:]

        re_diff = re_h * re_r - im_h * im_r - re_t
        im_diff = re_h * im_r + im_h * re_r - im_t

        return -np.sqrt(np.sum(re_diff**2 + im_diff**2, axis=1))

    def _score_transe(self, heads: np.ndarray, relation: np.ndarray, tail: np.ndarray) -> np.ndarray:
        """TransE: h + r ≈ t."""
        return -np.linalg.norm(heads + relation - tail, axis=1)

    # ── Main Entry Points ──

    def score_disease(self, disease_query: str, top_k: int = 50) -> KGResult:
        """
        Score ALL compounds against a disease. Returns top-k ranked.

        This is the discovery function. It scores every compound in DRKG
        (~24K) across all disease entities × treatment relations, keeps
        the best score per compound, and returns percentile-ranked results.
        """
        t0 = time.perf_counter()

        disease_entities = self.resolve_disease(disease_query)
        if not disease_entities:
            return KGResult(
                disease_query=disease_query, disease_entities_used=[],
                treatment_relations_used=[], method=self.method,
                total_compounds_scored=0, predictions=[], timing_ms=0,
                error=f"Disease '{disease_query}' not found. Try: {list(DEMO_DISEASE_ENTITIES.keys())}",
            )

        treatment_rels = self.find_treatment_relations()
        if not treatment_rels:
            return KGResult(
                disease_query=disease_query, disease_entities_used=disease_entities,
                treatment_relations_used=[], method=self.method,
                total_compounds_scored=0, predictions=[], timing_ms=0,
                error="No treatment relations found.",
            )

        # Score all compounds (vectorized)
        n = len(self.compound_indices)
        best_scores = np.full(n, -np.inf, dtype=np.float64)
        best_relations = [""] * n

        for entity_id in disease_entities:
            d_idx = self.entity_to_idx.get(entity_id)
            if d_idx is None:
                continue
            tail = self.entity_emb[d_idx]

            for rel_name, rel_idx in treatment_rels:
                rel = self.relation_emb[rel_idx]
                if self.method == "RotatE":
                    scores = self._score_rotate(self.compound_embs, rel, tail)
                else:
                    scores = self._score_transe(self.compound_embs, rel, tail)

                improved = scores > best_scores
                best_scores[improved] = scores[improved]
                for i in np.where(improved)[0]:
                    best_relations[i] = rel_name

        # Stats
        valid = best_scores[~np.isinf(best_scores)]
        if len(valid) == 0:
            return KGResult(
                disease_query=disease_query, disease_entities_used=disease_entities,
                treatment_relations_used=[r[0] for r in treatment_rels], method=self.method,
                total_compounds_scored=0, predictions=[],
                timing_ms=(time.perf_counter() - t0) * 1000,
                error="No valid scores. Embeddings may be corrupted.",
            )

        mean_s, std_s = float(np.mean(valid)), float(max(np.std(valid), 1e-8))

        # Top-k
        top_idx = np.argsort(best_scores)[-top_k:][::-1]
        predictions = []
        for rank, idx in enumerate(top_idx):
            if np.isinf(best_scores[idx]):
                continue
            s = float(best_scores[idx])
            pctl = float(np.sum(valid <= s) / len(valid) * 100)
            predictions.append(KGPrediction(
                drug_entity=self.compound_names[idx],
                drug_name=self.compound_names[idx].replace("Compound::", ""),
                score=round(s, 4),
                percentile=round(pctl, 2),
                z_score=round((s - mean_s) / std_s, 3),
                rank=rank + 1,
                method=self.method,
                relation_used=best_relations[idx],
                normalized_score=round(normalize_kg_score(pctl), 2),
            ))

        elapsed = (time.perf_counter() - t0) * 1000
        return KGResult(
            disease_query=disease_query,
            disease_entities_used=disease_entities,
            treatment_relations_used=[r[0] for r in treatment_rels],
            method=self.method,
            total_compounds_scored=n,
            predictions=predictions,
            timing_ms=round(elapsed, 1),
            metadata=self.training_metadata,
        )

    def score_specific_drugs(self, drug_names: list[str], disease_query: str) -> KGResult:
        """Score specific drugs (by name) against a disease."""
        full = self.score_disease(disease_query, top_k=len(self.compound_names))
        if full.error:
            return full

        by_entity = {p.drug_entity: p for p in full.predictions}
        matched, unmatched = [], []

        for name in drug_names:
            entity = self.resolver.resolve(name) if self.resolver else None
            if entity and entity in by_entity:
                pred = by_entity[entity]
                matched.append(KGPrediction(
                    drug_entity=pred.drug_entity, drug_name=name,
                    score=pred.score, percentile=pred.percentile,
                    z_score=pred.z_score, rank=pred.rank,
                    method=pred.method, relation_used=pred.relation_used,
                    normalized_score=pred.normalized_score,
                ))
            else:
                unmatched.append(name)

        matched.sort(key=lambda p: p.score, reverse=True)
        for i, p in enumerate(matched):
            p.rank = i + 1

        return KGResult(
            disease_query=full.disease_query,
            disease_entities_used=full.disease_entities_used,
            treatment_relations_used=full.treatment_relations_used,
            method=full.method,
            total_compounds_scored=full.total_compounds_scored,
            predictions=matched,
            timing_ms=full.timing_ms,
            metadata=full.metadata,
            error=f"Not resolved: {unmatched}" if unmatched and not matched else None,
        )

    def info(self) -> dict:
        n_compounds = len(self.compound_names)
        n_diseases = sum(1 for e in self.entity_to_idx if e.startswith("Disease::"))
        n_genes = sum(1 for e in self.entity_to_idx if e.startswith("Gene::"))
        return {
            "method": self.method,
            "embedding_shape": list(self.entity_emb.shape),
            "complex_dim": self.complex_dim,
            "total_entities": len(self.entity_to_idx),
            "total_relations": len(self.relation_to_idx),
            "compounds": n_compounds,
            "diseases": n_diseases,
            "genes": n_genes,
            "treatment_relations": [r[0] for r in self.find_treatment_relations()],
        }
