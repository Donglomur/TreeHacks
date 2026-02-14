#!/usr/bin/env python3
"""
NUCLEAR OPTION: Map KG compounds → dropped_drugs DB via PubChem.

The problem: KG uses DrugBank/MESH/ChEBI IDs, DB uses ChEMBL IDs + drug names.
These don't match directly.

Solution: Use PubChem as the universal bridge. For every KG compound:
  1. Resolve to PubChem CID (PubChem knows ALL ID systems)
  2. Get ALL synonyms + cross-references from PubChem
  3. Match against DB by: ChEMBL ID, drug name, any synonym

This runs on Modal with parallel batches. Takes ~5-10 minutes.

Usage:
    cd TreeHacks
    python -m modal run scripts/resolve_all_compounds.py
"""

import json
import sqlite3
from pathlib import Path

import modal

app = modal.App("drugrescue-compound-resolver")

image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")


@app.function(image=image, timeout=900, retries=1, concurrency_limit=10)
def resolve_batch(compounds: list[dict]) -> list[dict]:
    """
    Resolve a batch of KG compounds through PubChem.

    Each compound = {"id": "DB00515", "type": "drugbank"/"mesh"/"chebi"/"chembl"}

    Returns list of:
    {
        "kg_id": "DB00515",
        "pubchem_cid": 5702198,
        "name": "CISPLATIN",
        "synonyms": ["cisplatin", "cis-diamminedichloroplatinum", ...],
        "chembl_id": "CHEMBL481",
        "drugbank_id": "DB00515",
    }
    """
    import time
    import requests

    PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    results = []

    for comp in compounds:
        cid = comp["id"]
        ctype = comp["type"]
        result = {"kg_id": cid, "pubchem_cid": None, "name": None,
                  "synonyms": [], "chembl_id": None, "drugbank_id": None}

        try:
            # ── Step 1: Get PubChem CID ──
            pcid = None

            if ctype == "drugbank":
                url = f"{PUBCHEM}/substance/sourceid/DrugBank/{cid}/cids/JSON"
                resp = requests.get(url, timeout=8)
                if resp.status_code == 200:
                    info = resp.json().get("InformationList", {}).get("Information", [])
                    if info and info[0].get("CID"):
                        pcid = info[0]["CID"][0]

                # Also store DrugBank ID
                result["drugbank_id"] = cid.upper()

            elif ctype == "mesh":
                # MESH → try as substance source
                mesh_id = cid.replace("MESH:", "")
                url = f"{PUBCHEM}/substance/sourceid/MeSH/{mesh_id}/cids/JSON"
                resp = requests.get(url, timeout=8)
                if resp.status_code == 200:
                    info = resp.json().get("InformationList", {}).get("Information", [])
                    if info and info[0].get("CID"):
                        pcid = info[0]["CID"][0]

                # Also try compound name search with MESH term
                if not pcid:
                    url2 = f"{PUBCHEM}/compound/name/{mesh_id}/cids/JSON"
                    resp2 = requests.get(url2, timeout=8)
                    if resp2.status_code == 200:
                        cid_list = resp2.json().get("IdentifierList", {}).get("CID", [])
                        if cid_list:
                            pcid = cid_list[0]

            elif ctype == "chebi":
                chebi_num = cid.replace("CHEBI:", "")
                url = f"{PUBCHEM}/substance/sourceid/ChEBI/CHEBI:{chebi_num}/cids/JSON"
                resp = requests.get(url, timeout=8)
                if resp.status_code == 200:
                    info = resp.json().get("InformationList", {}).get("Information", [])
                    if info and info[0].get("CID"):
                        pcid = info[0]["CID"][0]

            elif ctype == "chembl":
                url = f"{PUBCHEM}/substance/sourceid/ChEMBL/{cid}/cids/JSON"
                resp = requests.get(url, timeout=8)
                if resp.status_code == 200:
                    info = resp.json().get("InformationList", {}).get("Information", [])
                    if info and info[0].get("CID"):
                        pcid = info[0]["CID"][0]
                result["chembl_id"] = cid.upper()

            if not pcid:
                results.append(result)
                time.sleep(0.15)
                continue

            result["pubchem_cid"] = pcid

            # ── Step 2: Get synonyms ──
            url = f"{PUBCHEM}/compound/cid/{pcid}/synonyms/JSON"
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                syn_data = resp.json().get("InformationList", {}).get("Information", [])
                if syn_data:
                    synonyms = syn_data[0].get("Synonym", [])
                    result["synonyms"] = [s.upper().strip() for s in synonyms[:50]]
                    if synonyms:
                        result["name"] = synonyms[0].upper().strip()

                    # Extract ChEMBL ID from synonyms
                    for s in synonyms:
                        su = s.upper().strip()
                        if su.startswith("CHEMBL") and su.replace("CHEMBL", "").isdigit():
                            result["chembl_id"] = su
                            break

                    # Extract DrugBank ID from synonyms
                    for s in synonyms:
                        su = s.upper().strip()
                        if su.startswith("DB") and len(su) <= 9 and su[2:].isdigit():
                            result["drugbank_id"] = su
                            break

            # ── Step 3: Get cross-references (for ChEMBL/DrugBank IDs) ──
            if not result["chembl_id"] or not result["drugbank_id"]:
                url = f"{PUBCHEM}/compound/cid/{pcid}/xrefs/RegistryID/JSON"
                resp = requests.get(url, timeout=8)
                if resp.status_code == 200:
                    xref_data = resp.json().get("InformationList", {}).get("Information", [])
                    if xref_data:
                        for xid in xref_data[0].get("RegistryID", []):
                            xu = xid.upper().strip()
                            if xu.startswith("CHEMBL") and not result["chembl_id"]:
                                result["chembl_id"] = xu
                            if xu.startswith("DB") and len(xu) <= 9 and xu[2:].isdigit() and not result["drugbank_id"]:
                                result["drugbank_id"] = xu

            results.append(result)
            time.sleep(0.15)  # PubChem rate limit: ~5 req/sec

        except Exception:
            results.append(result)
            time.sleep(0.15)

    return results


@app.local_entrypoint()
def main():
    db_path = Path("data/database/dropped_drugs.db")
    ent_path = Path("data/embeddings/entity_to_idx.json")

    if not db_path.exists() or not ent_path.exists():
        print("Error: Run from TreeHacks/ root.")
        return

    # ── 1. Collect ALL KG compound IDs by type ──
    with open(ent_path) as f:
        entity_to_idx = json.load(f)

    compounds = []
    for name in entity_to_idx:
        if not name.startswith("Compound::"):
            continue
        cid = name.replace("Compound::", "")
        if cid.startswith("DB"):
            compounds.append({"id": cid, "type": "drugbank"})
        elif cid.startswith("MESH:"):
            compounds.append({"id": cid, "type": "mesh"})
        elif cid.startswith("CHEBI:"):
            compounds.append({"id": cid, "type": "chebi"})
        elif cid.startswith("CHEMBL"):
            compounds.append({"id": cid, "type": "chembl"})
        # Skip "Other" type — usually gene/protein IDs misclassified

    print(f"KG compounds to resolve: {len(compounds)}")
    by_type = {}
    for c in compounds:
        by_type[c["type"]] = by_type.get(c["type"], 0) + 1
    for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {t}: {n}")

    # ── 2. Load DB for matching ──
    conn = sqlite3.connect(str(db_path))

    # Build match indices from DB
    db_by_chembl = {}   # CHEMBL1234 → row
    db_by_name = {}     # ASPIRIN → row
    for row in conn.execute(
        "SELECT drug_name, chembl_id, drugbank_id, smiles, max_phase FROM dropped_drugs"
    ):
        name, chembl, drugbank, smiles, phase = row
        entry = {"drug_name": name, "chembl_id": chembl,
                 "drugbank_id": drugbank, "smiles": smiles, "max_phase": phase}
        if chembl:
            db_by_chembl[chembl.upper().strip()] = entry
        if name:
            db_by_name[name.upper().strip()] = entry

    print(f"\nDB: {len(db_by_chembl)} ChEMBL entries, {len(db_by_name)} name entries")

    # ── 3. Resolve on Modal ──
    batch_size = 100
    batches = [compounds[i:i+batch_size] for i in range(0, len(compounds), batch_size)]
    print(f"\nResolving in {len(batches)} parallel batches...")

    all_resolved = []
    for i, result_batch in enumerate(resolve_batch.map(batches)):
        all_resolved.extend(result_batch)
        done = min((i + 1) * batch_size, len(compounds))
        resolved = sum(1 for r in all_resolved if r["pubchem_cid"])
        if (i + 1) % 10 == 0 or done == len(compounds):
            print(f"  {done}/{len(compounds)} done, {resolved} resolved")

    # Save full resolution data
    resolve_file = Path("data/compound_resolution.json")
    with open(resolve_file, "w") as f:
        json.dump(all_resolved, f, indent=2)
    print(f"\nSaved {len(all_resolved)} resolutions to {resolve_file}")

    resolved_count = sum(1 for r in all_resolved if r["pubchem_cid"])
    has_chembl = sum(1 for r in all_resolved if r["chembl_id"])
    has_name = sum(1 for r in all_resolved if r["name"])
    print(f"  PubChem CID found: {resolved_count}/{len(all_resolved)}")
    print(f"  ChEMBL ID found:   {has_chembl}")
    print(f"  Drug name found:   {has_name}")

    # ── 4. Match against DB (3 strategies) ──
    print(f"\nMatching against dropped_drugs DB...")

    matched = {}  # kg_compound_id → {drugbank_id, chembl_match}

    for r in all_resolved:
        kg_id = r["kg_id"]

        # Strategy 1: Direct ChEMBL ID match
        if r["chembl_id"] and r["chembl_id"] in db_by_chembl:
            db_entry = db_by_chembl[r["chembl_id"]]
            matched[kg_id] = {
                "chembl_id": r["chembl_id"],
                "drugbank_id": r.get("drugbank_id"),
                "match_type": "chembl_direct",
            }
            continue

        # Strategy 2: Primary name match
        if r["name"] and r["name"] in db_by_name:
            db_entry = db_by_name[r["name"]]
            matched[kg_id] = {
                "chembl_id": db_entry["chembl_id"],
                "drugbank_id": r.get("drugbank_id"),
                "match_type": "name_primary",
            }
            continue

        # Strategy 3: Any synonym match
        for syn in r.get("synonyms", []):
            if syn in db_by_name:
                db_entry = db_by_name[syn]
                matched[kg_id] = {
                    "chembl_id": db_entry["chembl_id"],
                    "drugbank_id": r.get("drugbank_id"),
                    "match_type": "name_synonym",
                }
                break

    print(f"\nTotal matched: {len(matched)}/{len(all_resolved)}")

    # Count by match type
    by_match_type = {}
    for m in matched.values():
        mt = m["match_type"]
        by_match_type[mt] = by_match_type.get(mt, 0) + 1
    for mt, n in sorted(by_match_type.items(), key=lambda x: -x[1]):
        print(f"  {mt}: {n}")

    # ── 5. Update DB ──
    print(f"\nUpdating database...")
    updated = 0
    for kg_id, match in matched.items():
        if match.get("drugbank_id") and match.get("chembl_id"):
            conn.execute(
                "UPDATE dropped_drugs SET drugbank_id = ? WHERE UPPER(chembl_id) = ?",
                (match["drugbank_id"], match["chembl_id"].upper())
            )
            updated += 1

    conn.commit()

    has_db = conn.execute(
        "SELECT COUNT(*) FROM dropped_drugs WHERE drugbank_id IS NOT NULL AND drugbank_id != ''"
    ).fetchone()[0]
    print(f"✅ Updated {updated} rows")
    print(f"✅ DB now has {has_db} drugs with DrugBank IDs")

    # ── 6. Build reverse lookup: KG entity → DB entry ──
    # Save as a JSON file the agent can use directly
    kg_to_db = {}
    for r in all_resolved:
        kg_entity = f"Compound::{r['kg_id']}"
        kg_id = r["kg_id"]

        if kg_id in matched:
            chembl = matched[kg_id]["chembl_id"]
            if chembl and chembl in db_by_chembl:
                db_entry = db_by_chembl[chembl]
                kg_to_db[kg_entity] = {
                    "drug_name": db_entry["drug_name"],
                    "chembl_id": chembl,
                    "drugbank_id": matched[kg_id].get("drugbank_id"),
                    "smiles": db_entry.get("smiles"),
                    "max_phase": db_entry.get("max_phase"),
                }
        elif r["name"]:
            # Even if not matched to DB, store the resolved name
            kg_to_db[kg_entity] = {
                "drug_name": r["name"],
                "chembl_id": r.get("chembl_id"),
                "drugbank_id": r.get("drugbank_id"),
                "smiles": None,
                "max_phase": None,
            }

    lookup_file = Path("data/database/kg_entity_lookup.json")
    with open(lookup_file, "w") as f:
        json.dump(kg_to_db, f, indent=2)
    print(f"\nSaved {len(kg_to_db)} entity lookups to {lookup_file}")

    # ── 7. Final stats ──
    print(f"\n{'='*60}")
    print(f"FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"KG compounds:          {len(compounds)}")
    print(f"PubChem resolved:      {resolved_count}")
    print(f"Matched to dropped DB: {len(matched)}")
    print(f"Entity lookup saved:   {len(kg_to_db)}")
    print(f"DB DrugBank coverage:  {has_db}")
    print(f"\nRun:  python scripts/check_coverage.py")

    conn.close()
