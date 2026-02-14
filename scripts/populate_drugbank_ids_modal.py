#!/usr/bin/env python3
"""
Map DrugBank IDs (from KG) → drug names (via PubChem) → match to dropped_drugs DB.

Strategy:
  1. Read all DrugBank IDs from entity_to_idx.json (10,551 IDs)
  2. Batch-query PubChem: DrugBank ID → CID → drug name
  3. Match names against drug_name in dropped_drugs.db
  4. Write drugbank_id back to DB for matches

Usage:
    cd TreeHacks
    python -m modal run scripts/populate_drugbank_ids_modal.py
"""

import json
import sqlite3
from pathlib import Path

import modal

app = modal.App("drugrescue-drugbank-mapper")

image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")


@app.function(image=image, timeout=900, retries=1)
def resolve_drugbank_batch(db_ids: list[str]) -> dict[str, str]:
    """
    For a batch of DrugBank IDs, query PubChem to get drug names.
    Returns {drugbank_id: drug_name}.
    """
    import time
    import requests

    results = {}

    for db_id in db_ids:
        try:
            # Step 1: DrugBank ID → PubChem CID
            url = (
                f"https://pubchem.ncbi.nlm.nih.gov/rest/pug"
                f"/substance/sourceid/DrugBank/{db_id}/cids/JSON"
            )
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                continue

            data = resp.json()
            info_list = data.get("InformationList", {}).get("Information", [])
            if not info_list:
                continue

            cids = info_list[0].get("CID", [])
            if not cids:
                continue

            cid = cids[0]

            # Step 2: CID → drug name (Title)
            url2 = (
                f"https://pubchem.ncbi.nlm.nih.gov/rest/pug"
                f"/compound/cid/{cid}/property/Title/JSON"
            )
            resp2 = requests.get(url2, timeout=10)
            if resp2.status_code != 200:
                continue

            props = resp2.json().get("PropertyTable", {}).get("Properties", [])
            if props:
                title = props[0].get("Title", "")
                if title:
                    results[db_id.upper()] = title.upper().strip()

            # PubChem rate limit: 5 req/sec (we do 2 per drug = 2.5 drugs/sec)
            time.sleep(0.2)

        except Exception:
            continue

    return results


@app.local_entrypoint()
def main():
    db_path = Path("data/database/dropped_drugs.db")
    ent_path = Path("data/embeddings/entity_to_idx.json")

    if not db_path.exists() or not ent_path.exists():
        print("Error: Run from TreeHacks/ root (need data/ folder)")
        return

    # ── 1. Get DrugBank IDs from KG ──
    with open(ent_path) as f:
        entity_to_idx = json.load(f)

    kg_drugbank_ids = sorted({
        name.replace("Compound::", "")
        for name in entity_to_idx
        if name.startswith("Compound::DB")
    })
    print(f"KG has {len(kg_drugbank_ids)} DrugBank compounds\n")

    # ── 2. Get drug names from DB ──
    conn = sqlite3.connect(str(db_path))
    db_name_to_chembl = {}
    for row in conn.execute("SELECT drug_name, chembl_id FROM dropped_drugs"):
        if row[0] and row[1]:
            db_name_to_chembl[row[0].upper().strip()] = row[1].strip()
    print(f"DB has {len(db_name_to_chembl)} drugs with names\n")

    # ── 3. Batch-resolve on Modal ──
    # Split into batches of 200 for parallel processing
    batch_size = 200
    batches = []
    for i in range(0, len(kg_drugbank_ids), batch_size):
        batches.append(kg_drugbank_ids[i:i + batch_size])

    print(f"Resolving via PubChem in {len(batches)} parallel batches...")

    # Run all batches in parallel on Modal
    all_mappings = {}
    for i, result in enumerate(resolve_drugbank_batch.map(batches)):
        all_mappings.update(result)
        done = min((i + 1) * batch_size, len(kg_drugbank_ids))
        print(f"  Batch {i+1}/{len(batches)}: {done}/{len(kg_drugbank_ids)} done, "
              f"{len(all_mappings)} names resolved")

    print(f"\n✅ Resolved {len(all_mappings)} DrugBank IDs → drug names")

    # ── 4. Save the raw mapping ──
    mapping_file = Path("data/drugbank_to_name.json")
    with open(mapping_file, "w") as f:
        json.dump(all_mappings, f, indent=2)
    print(f"Saved mapping to {mapping_file}")

    # ── 5. Match against DB by name ──
    matched = 0
    for db_id, drug_name in all_mappings.items():
        if drug_name in db_name_to_chembl:
            chembl_id = db_name_to_chembl[drug_name]
            conn.execute(
                "UPDATE dropped_drugs SET drugbank_id = ? WHERE UPPER(chembl_id) = ?",
                (db_id, chembl_id.upper())
            )
            matched += 1

    conn.commit()

    has_db = conn.execute(
        "SELECT COUNT(*) FROM dropped_drugs WHERE drugbank_id IS NOT NULL AND drugbank_id != ''"
    ).fetchone()[0]
    print(f"\n✅ Matched {matched} drugs by name")
    print(f"✅ DB now has {has_db}/{len(db_name_to_chembl)} drugs with DrugBank IDs")

    # ── 6. Check KG overlap ──
    kg_drugbank_set = {did.upper() for did in kg_drugbank_ids}
    db_drugbank_set = set()
    for row in conn.execute(
        "SELECT drugbank_id FROM dropped_drugs WHERE drugbank_id IS NOT NULL AND drugbank_id != ''"
    ):
        db_drugbank_set.add(row[0].strip().upper())

    overlap = kg_drugbank_set & db_drugbank_set
    print(f"\n📊 OVERLAP with KG: {len(overlap)} drugs can now be matched!")
    print(f"\nRun:  python scripts/check_coverage.py")

    conn.close()
