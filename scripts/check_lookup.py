"""Check what the resolver actually produced. Run from TreeHacks/"""
import json
from pathlib import Path

# Check kg_entity_lookup.json
lookup_path = Path("data/database/kg_entity_lookup.json")
if lookup_path.exists():
    with open(lookup_path) as f:
        lookup = json.load(f)
    print(f"kg_entity_lookup.json: {len(lookup)} entries")

    # Count how many have names vs raw IDs
    has_name = sum(1 for v in lookup.values() if v.get("drug_name"))
    has_chembl = sum(1 for v in lookup.values() if v.get("chembl_id"))
    has_smiles = sum(1 for v in lookup.values() if v.get("smiles"))
    print(f"  Has drug_name: {has_name}")
    print(f"  Has chembl_id: {has_chembl}")
    print(f"  Has SMILES:    {has_smiles}")

    # Show what top KG hits look like in the lookup
    top_ids = [
        "Compound::MESH:C588336", "Compound::MESH:C033685",
        "Compound::DB00515", "Compound::DB00675", "Compound::DB00773",
        "Compound::CHEBI:7576", "Compound::DB00544",
    ]
    print(f"\nTop KG hits in lookup:")
    for eid in top_ids:
        entry = lookup.get(eid)
        if entry:
            print(f"  {eid:<35s} → {entry.get('drug_name', '?')}")
        else:
            print(f"  {eid:<35s} → NOT IN LOOKUP")
else:
    print("❌ kg_entity_lookup.json NOT FOUND")
    print("   Did resolve_all_compounds.py finish?")

# Check drugbank_to_name.json (from first Modal run)
name_path = Path("data/drugbank_to_name.json")
if name_path.exists():
    with open(name_path) as f:
        db_names = json.load(f)
    print(f"\ndrugbank_to_name.json: {len(db_names)} entries")
    for did in ["DB00515", "DB00675", "DB00773", "DB00544"]:
        print(f"  {did} → {db_names.get(did, 'NOT FOUND')}")
else:
    print(f"\ndrugbank_to_name.json NOT FOUND")

# Check compound_resolution.json
res_path = Path("data/compound_resolution.json")
if res_path.exists():
    with open(res_path) as f:
        resolutions = json.load(f)
    resolved = sum(1 for r in resolutions if r.get("pubchem_cid"))
    named = sum(1 for r in resolutions if r.get("name"))
    print(f"\ncompound_resolution.json: {len(resolutions)} entries")
    print(f"  PubChem resolved: {resolved}")
    print(f"  Has name:         {named}")
else:
    print(f"\ncompound_resolution.json NOT FOUND")
