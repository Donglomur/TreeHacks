"""
Diagnose why 0 dropped drugs are matching.
Run from TreeHacks/: python scripts/diagnose_matching.py
"""
import sys, os, json, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from drug_rescue.engines.scorer import DRKGScorer

# ── 1. What's in the KG? ──
print("=" * 60)
print("1. DRKG COMPOUND ID TYPES")
print("=" * 60)

scorer = DRKGScorer(
    embeddings_dir="./data/embeddings",
    db_path="./data/database/dropped_drugs.db",
)

# Count ID prefixes
prefixes = {}
for name in scorer.compound_names:
    cid = name.replace("Compound::", "")
    if cid.startswith("DB"):
        prefixes["DrugBank (DB...)"] = prefixes.get("DrugBank (DB...)", 0) + 1
    elif cid.startswith("CHEMBL"):
        prefixes["ChEMBL"] = prefixes.get("ChEMBL", 0) + 1
    elif cid.startswith("MESH:"):
        prefixes["MESH"] = prefixes.get("MESH", 0) + 1
    elif cid.startswith("CHEBI:"):
        prefixes["ChEBI"] = prefixes.get("ChEBI", 0) + 1
    else:
        prefixes["Other"] = prefixes.get("Other", 0) + 1

print(f"Total compounds in KG: {len(scorer.compound_names)}")
for k, v in sorted(prefixes.items(), key=lambda x: -x[1]):
    print(f"  {k:<25s} {v:>6d}  ({100*v/len(scorer.compound_names):.1f}%)")

# ── 2. What's in the DB? ──
print(f"\n{'=' * 60}")
print("2. DROPPED_DRUGS DB ID FORMATS")
print("=" * 60)

conn = sqlite3.connect("./data/database/dropped_drugs.db")
rows = conn.execute(
    "SELECT drug_name, chembl_id, drugbank_id FROM dropped_drugs LIMIT 10"
).fetchall()
total = conn.execute("SELECT COUNT(*) FROM dropped_drugs").fetchone()[0]

print(f"Total rows: {total}")
print(f"\nSample rows (first 10):")
print(f"  {'drug_name':<30s} {'chembl_id':<20s} {'drugbank_id':<15s}")
print(f"  {'─'*30} {'─'*20} {'─'*15}")
for name, chembl, drugbank in rows:
    print(f"  {str(name)[:29]:<30s} {str(chembl)[:19]:<20s} {str(drugbank)[:14]:<15s}")

# Count what ID types the DB has
has_drugbank = conn.execute(
    "SELECT COUNT(*) FROM dropped_drugs WHERE drugbank_id IS NOT NULL AND drugbank_id != ''"
).fetchone()[0]
has_chembl = conn.execute(
    "SELECT COUNT(*) FROM dropped_drugs WHERE chembl_id IS NOT NULL AND chembl_id != ''"
).fetchone()[0]
has_name = conn.execute(
    "SELECT COUNT(*) FROM dropped_drugs WHERE drug_name IS NOT NULL AND drug_name != ''"
).fetchone()[0]

print(f"\nDB has DrugBank IDs: {has_drugbank}/{total}")
print(f"DB has ChEMBL IDs:  {has_chembl}/{total}")
print(f"DB has drug names:  {has_name}/{total}")

# ── 3. Check overlap ──
print(f"\n{'=' * 60}")
print("3. OVERLAP CHECK")
print("=" * 60)

# Get all DrugBank IDs from DB
db_drugbank = set()
db_chembl = set()
for row in conn.execute("SELECT chembl_id, drugbank_id FROM dropped_drugs"):
    chembl, drugbank = row
    if drugbank:
        db_drugbank.add(drugbank.strip().upper())
    if chembl:
        db_chembl.add(chembl.strip().upper())

# Get all compound IDs from KG
kg_drugbank = set()
kg_chembl = set()
kg_all = set()
for name in scorer.compound_names:
    cid = name.replace("Compound::", "")
    kg_all.add(cid)
    if cid.startswith("DB"):
        kg_drugbank.add(cid.upper())
    elif cid.startswith("CHEMBL"):
        kg_chembl.add(cid.upper())

overlap_db = kg_drugbank & db_drugbank
overlap_ch = kg_chembl & db_chembl

print(f"KG DrugBank IDs: {len(kg_drugbank)}")
print(f"DB DrugBank IDs: {len(db_drugbank)}")
print(f"OVERLAP (DrugBank): {len(overlap_db)}")
print()
print(f"KG ChEMBL IDs: {len(kg_chembl)}")
print(f"DB ChEMBL IDs: {len(db_chembl)}")
print(f"OVERLAP (ChEMBL): {len(overlap_ch)}")

# ── 4. Score some known dropped drugs ──
print(f"\n{'=' * 60}")
print("4. SPOT CHECK — SCORING KNOWN DROPPED DRUGS")
print("=" * 60)

# Grab 10 dropped drugs that DO have DrugBank IDs in the KG
found_in_kg = []
for dbid in list(overlap_db)[:20]:
    entity = f"Compound::{dbid}"
    if entity in scorer.entity_to_idx:
        # Get the drug name from the DB
        row = conn.execute(
            "SELECT drug_name, max_phase FROM dropped_drugs WHERE UPPER(drugbank_id) = ?",
            (dbid,)
        ).fetchone()
        if row:
            found_in_kg.append((dbid, row[0], row[1]))

if found_in_kg:
    # Score glioblastoma with ALL compounds
    kg = scorer.score_disease("glioblastoma", top_k=len(scorer.compound_names))
    by_entity = {p.drug_entity: p for p in kg.predictions}

    print(f"Dropped drugs found in KG (showing up to 10):\n")
    print(f"  {'DrugBank':<12s} {'Name':<25s} {'Phase':<6s} {'Pctl':<8s} {'Z':<8s} {'Rank'}")
    print(f"  {'─'*12} {'─'*25} {'─'*6} {'─'*8} {'─'*8} {'─'*6}")
    for dbid, name, phase in found_in_kg[:10]:
        entity = f"Compound::{dbid}"
        pred = by_entity.get(entity)
        if pred:
            print(f"  {dbid:<12s} {str(name)[:24]:<25s} {str(phase):<6s} "
                  f"{pred.percentile:<8.1f} {pred.z_score:<8.2f} {pred.rank}")
        else:
            print(f"  {dbid:<12s} {str(name)[:24]:<25s} {str(phase):<6s} NOT SCORED")
else:
    print("No dropped drugs found in KG overlap!")

# ── 5. The actual problem ──
print(f"\n{'=' * 60}")
print("5. WHY THE ENRICHER MISSES")
print("=" * 60)

# Score top 20 and show what the enricher sees
kg_top = scorer.score_disease("glioblastoma", top_k=20)
from drug_rescue.engines.discover import _DBEnricher
enricher = _DBEnricher("./data/database/dropped_drugs.db")

print(f"\nTop 20 KG hits — enricher lookup results:\n")
print(f"  {'Entity':<30s} {'ID stripped':<20s} {'DB match?'}")
print(f"  {'─'*30} {'─'*20} {'─'*10}")
for p in kg_top.predictions:
    cid = p.drug_entity.replace("Compound::", "")
    db = enricher.enrich(p.drug_entity)
    match = f"YES: {db.get('drug_name', '?')}" if db else "NO"
    print(f"  {p.drug_entity[:29]:<30s} {cid[:19]:<20s} {match}")

conn.close()
