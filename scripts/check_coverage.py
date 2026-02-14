"""Run from TreeHacks/: python scripts/check_coverage.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from drug_rescue.engines.discover import discover_candidates

print("Checking how many dropped drugs appear at different thresholds...\n")

for max_cand, min_pctl in [(20, 99.0), (50, 95.0), (100, 90.0), (200, 75.0)]:
    r = discover_candidates(
        "glioblastoma", data_dir="./data",
        max_candidates=max_cand, min_percentile=min_pctl, include_novel=True,
    )
    dropped = [c for c in r.candidates if c.status == "dropped"]
    withdrawn = [c for c in r.candidates if c.status == "withdrawn"]
    novel = [c for c in r.candidates if c.status == "novel"]
    print(f"Top {max_cand} (>={min_pctl}th pctl): "
          f"{len(dropped)} dropped, {len(withdrawn)} withdrawn, {len(novel)} novel")
    for c in dropped[:5]:
        smiles = "Y" if c.smiles else "N"
        print(f"  -> {c.drug_name:<30s} Phase {c.max_phase or '?':<3} "
              f"pctl={c.kg_percentile:.1f}  z={c.kg_z_score:.2f}  SMILES={smiles}")
    print()
