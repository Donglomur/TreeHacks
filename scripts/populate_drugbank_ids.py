#!/usr/bin/env python3
"""
Populate drugbank_id in dropped_drugs.db using UniChem bulk mapping file.

Downloads ONE file (~2MB), joins locally. Takes seconds.

Usage:
    cd TreeHacks
    pip install requests
    python scripts/populate_drugbank_ids.py
"""

import gzip
import json
import sqlite3
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

DB_PATH = Path("data/database/dropped_drugs.db")

# UniChem bulk mapping: source 1 (ChEMBL) → source 2 (DrugBank)
UNICHEM_URL = "https://ftp.ebi.ac.uk/pub/databases/chembl/UniChem/data/wholeSourceMapping/src_id1/src1src2.txt.gz"


def main():
    if not DB_PATH.exists():
        print(f"Error: {DB_PATH} not found. Run from TreeHacks/ root.")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))

    total = conn.execute("SELECT COUNT(*) FROM dropped_drugs").fetchone()[0]
    print(f"DB: {total} drugs\n")

    # Get our ChEMBL IDs
    rows = conn.execute(
        "SELECT DISTINCT chembl_id FROM dropped_drugs "
        "WHERE chembl_id IS NOT NULL AND chembl_id != ''"
    ).fetchall()
    our_chembl = {r[0].strip().upper() for r in rows if r[0]}
    print(f"Our ChEMBL IDs: {len(our_chembl)}\n")

    # ── Download bulk mapping ──
    print(f"Downloading UniChem bulk mapping...")
    print(f"  URL: {UNICHEM_URL}")

    resp = requests.get(UNICHEM_URL, timeout=60)
    resp.raise_for_status()

    raw = gzip.decompress(resp.content)
    text = raw.decode("utf-8")
    print(f"  ✅ Downloaded ({len(raw)/(1024*1024):.1f} MB uncompressed)")

    # Parse: each line is "chembl_numeric_id\tdrugbank_id"
    mapping = {}
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("From") or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            raw_chembl = parts[0].strip()
            drugbank_id = parts[1].strip()
            # UniChem stores bare numbers, we need "CHEMBL" prefix
            chembl_id = f"CHEMBL{raw_chembl}" if not raw_chembl.startswith("CHEMBL") else raw_chembl
            if drugbank_id.startswith("DB"):
                mapping[chembl_id.upper()] = drugbank_id.upper()

    print(f"  ✅ Parsed {len(mapping)} ChEMBL → DrugBank mappings\n")

    # Match with our drugs
    matched = {cid: mapping[cid] for cid in our_chembl if cid in mapping}
    print(f"Matched: {len(matched)}/{len(our_chembl)} of our drugs have DrugBank IDs")

    if not matched:
        # Debug: show what format our IDs are in vs the mapping
        sample_ours = list(our_chembl)[:5]
        sample_map = list(mapping.keys())[:5]
        print(f"\n  Our IDs look like: {sample_ours}")
        print(f"  Mapping IDs look like: {sample_map}")
        print(f"\n  Trying without CHEMBL prefix...")

        # Maybe our DB stores "CHEMBL1234" but mapping has just "1234"
        mapping2 = {}
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("From") or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                mapping2[parts[0].strip()] = parts[1].strip()

        # Try matching raw
        for cid in our_chembl:
            raw_num = cid.replace("CHEMBL", "")
            if raw_num in mapping2:
                matched[cid] = mapping2[raw_num].upper()
            elif cid in mapping2:
                matched[cid] = mapping2[cid].upper()

        print(f"  After fuzzy match: {len(matched)}/{len(our_chembl)}")

    # Update DB
    if matched:
        print(f"\nUpdating database...")
        for chembl_id, drugbank_id in matched.items():
            conn.execute(
                "UPDATE dropped_drugs SET drugbank_id = ? WHERE UPPER(chembl_id) = ?",
                (drugbank_id, chembl_id)
            )
        conn.commit()

        has_db = conn.execute(
            "SELECT COUNT(*) FROM dropped_drugs WHERE drugbank_id IS NOT NULL AND drugbank_id != ''"
        ).fetchone()[0]
        print(f"✅ DB now has {has_db}/{total} drugs with DrugBank IDs")

        # Check KG overlap
        ent_path = Path("data/embeddings/entity_to_idx.json")
        if ent_path.exists():
            with open(ent_path) as f:
                entity_to_idx = json.load(f)
            kg_drugbank = {
                name.replace("Compound::", "").upper()
                for name in entity_to_idx if name.startswith("Compound::DB")
            }
            db_drugbank = {matched[k] for k in matched}
            overlap = kg_drugbank & db_drugbank
            print(f"\n📊 KG DrugBank compounds: {len(kg_drugbank)}")
            print(f"📊 DB DrugBank IDs now:   {len(db_drugbank)}")
            print(f"📊 OVERLAP:               {len(overlap)} ← can now be matched!")
            print(f"\nRun:  python scripts/check_coverage.py")
    else:
        print("\nNo matches found. The mapping format may have changed.")
        print("Check https://www.ebi.ac.uk/unichem/ for current data format.")

    conn.close()


if __name__ == "__main__":
    main()
