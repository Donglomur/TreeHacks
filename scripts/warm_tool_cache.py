#!/usr/bin/env python3
"""Backfill tool cache entries from existing files/ artifacts.

Usage:
  PYTHONPATH=src python3 scripts/warm_tool_cache.py
  PYTHONPATH=src python3 scripts/warm_tool_cache.py --disease glioblastoma
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from drug_rescue.tools._cache import save_cached_output


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _upper(s: str | None) -> str:
    return (s or "").strip().upper()


def _lower(s: str | None) -> str:
    return (s or "").strip().lower()


def _warm_discovery(root: Path, disease: str) -> int:
    count = 0
    candidates = _read_json(root / "files" / "candidates.json")
    if not candidates:
        return count
    if _lower(str(candidates.get("disease", ""))) != disease:
        return count

    candidates_list = candidates.get("candidates", [])
    max_candidates = int(candidates.get("candidates_returned", len(candidates_list) or 30))

    # Save the common orchestrator defaults first.
    for include_novel in (True, False):
        args = {
            "disease": disease,
            "max_candidates": max_candidates,
            "min_percentile": 75.0,
            "include_novel": include_novel,
        }
        save_cached_output("discover_candidates", args, candidates)
        count += 1
    return count


def _warm_faers(root: Path, disease: str) -> int:
    count = 0
    faers = _read_json(root / "files" / "evidence" / "faers_signals.json")
    if not faers:
        return count
    if _lower(str(faers.get("disease", ""))) != disease:
        return count

    drugs = sorted(_upper(x) for x in faers.get("drugs_screened", []) if _upper(x))
    events = sorted(_upper(x) for x in faers.get("events_used", []) if _upper(x))
    if drugs:
        args = {
            "disease": disease,
            "candidate_drugs": drugs,
            "disease_events": events,
            "alpha": float(faers.get("alpha", 0.05)),
            "correction": _lower(str(faers.get("correction_method", "fdr") or "fdr")),
        }
        save_cached_output("faers_inverse_signal", args, faers)
        count += 1
    return count


def _warm_clinical_trials(root: Path, disease: str) -> int:
    count = 0
    ct = _read_json(root / "files" / "evidence" / "clinical_trials.json")
    if not ct:
        return count
    if _lower(str(ct.get("disease", ""))) != disease:
        return count

    results = ct.get("results", {})
    if not isinstance(results, dict):
        return count

    for drug_name, row in results.items():
        if not isinstance(row, dict):
            continue
        trials = row.get("trials", []) if isinstance(row.get("trials"), list) else []
        by_cat: dict[str, int] = {}
        for t in trials:
            if not isinstance(t, dict):
                continue
            cat = str(t.get("failure_category", "UNKNOWN"))
            by_cat[cat] = by_cat.get(cat, 0) + 1
        output = {
            "drug": drug_name,
            "disease_filter": ct.get("disease"),
            "total_failed_trials": int(row.get("total_failed_trials", len(trials))),
            "by_category": by_cat,
            "repurposing_viable": bool(row.get("repurposing_viable", True)),
            "repurposable_count": sum(
                1 for t in trials if isinstance(t, dict) and t.get("is_repurposing_candidate")
            ),
            "safety_flags": int(row.get("safety_flags", 0)),
            "summary": str(row.get("interpretation", ct.get("summary", ""))),
            "trials": trials,
            "_cache_seeded_from": "files/evidence/clinical_trials.json",
        }
        args = {
            "drug_name": _upper(drug_name),
            "disease": disease,
            "max_results": 15,
        }
        save_cached_output("clinical_trial_failure", args, output)
        count += 1
    return count


def _warm_literature(root: Path, disease: str) -> int:
    count = 0
    lit = _read_json(root / "files" / "evidence" / "literature.json")
    if not lit:
        return count
    if _lower(str(lit.get("disease", ""))) != disease:
        return count

    results = lit.get("results", {})
    if not isinstance(results, dict):
        return count

    for drug_name, row in results.items():
        if not isinstance(row, dict):
            continue
        output = dict(row)
        output.setdefault("drug_name", drug_name)
        output.setdefault("disease", lit.get("disease"))
        output.setdefault("_cache_seeded_from", "files/evidence/literature.json")
        args = {
            "drug_name": _upper(drug_name),
            "disease": disease,
        }
        save_cached_output("literature_search", args, output)
        count += 1
    return count


def _warm_molecular(root: Path, disease: str) -> int:
    count = 0
    mol = _read_json(root / "files" / "evidence" / "molecular.json")
    cands = _read_json(root / "files" / "candidates.json")
    if not mol or not cands:
        return count
    if _lower(str(mol.get("disease", ""))) != disease:
        return count

    candidates = cands.get("candidates", [])
    by_drug: dict[str, dict[str, Any]] = {}
    if isinstance(candidates, list):
        for c in candidates:
            if not isinstance(c, dict):
                continue
            nm = _upper(str(c.get("drug_name", "")))
            if nm:
                by_drug[nm] = c

    results = mol.get("results", {})
    if not isinstance(results, dict):
        return count

    for drug_name, row in results.items():
        if not isinstance(row, dict):
            continue
        upper_name = _upper(drug_name)
        cand = by_drug.get(upper_name, {})
        smiles = str(cand.get("smiles") or row.get("smiles") or "").strip()

        sim_output = {
            "disease": mol.get("disease"),
            "candidate": drug_name,
            **row,
            "_cache_seeded_from": "files/evidence/molecular.json",
        }
        sim_args = {
            "disease": disease,
            "candidate_smiles": smiles,
            "candidate_name": upper_name,
            "min_similarity": 0.40,
            "top_k": 20,
        }
        save_cached_output("molecular_similarity", sim_args, sim_output)
        count += 1

        if smiles:
            dock_output = {
                "drug": drug_name,
                "drug_smiles": smiles,
                "disease": mol.get("disease"),
                "summary": row.get("interpretation", "Seeded from precomputed molecular file."),
                "results": [],
                "targets_attempted": 0,
                "targets_successful": 0,
                "_cache_seeded_from": "files/evidence/molecular.json",
            }
            dock_args = {
                "drug_smiles": smiles,
                "drug_name": upper_name,
                "disease": disease,
                "num_poses": 3,
                "max_targets": 3,
            }
            save_cached_output("molecular_docking", dock_args, dock_output)
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Warm tool cache from files/evidence artifacts.")
    parser.add_argument("--disease", default=None, help="Disease name (defaults from files/candidates.json)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    candidates = _read_json(root / "files" / "candidates.json")
    disease = _lower(args.disease or str((candidates or {}).get("disease", "")))
    if not disease:
        raise SystemExit("Could not infer disease. Pass --disease explicitly.")

    total = 0
    total += _warm_discovery(root, disease)
    total += _warm_faers(root, disease)
    total += _warm_clinical_trials(root, disease)
    total += _warm_literature(root, disease)
    total += _warm_molecular(root, disease)

    print(f"Warmed {total} cache entries for disease='{disease}'.")
    print("Cache root: files/tool_cache/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
