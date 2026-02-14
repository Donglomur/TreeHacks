#!/usr/bin/env python3
"""
Resolve MESH compound IDs that PubChem couldn't handle.

Uses NLM's MeSH lookup API + PubChem name search as fallback.
Updates kg_entity_lookup.json with resolved names.

Usage:
    cd TreeHacks
    python scripts/resolve_mesh_compounds.py
"""

import json
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("pip install requests")
    exit(1)

LOOKUP_PATH = Path("data/database/kg_entity_lookup.json")
ENTITY_PATH = Path("data/embeddings/entity_to_idx.json")


def resolve_mesh_id(mesh_id: str) -> str | None:
    """
    Try to resolve a MESH supplemental ID (e.g., C588336) to a drug name.

    Strategy:
      1. NLM MeSH API (Supplementary Concept Records)
      2. PubChem compound name search
    """
    # Strip prefix
    raw_id = mesh_id.replace("MESH:", "")

    # ── Strategy 1: NLM MeSH API ──
    try:
        url = f"https://id.nlm.nih.gov/mesh/{raw_id}.json"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            # MeSH returns label in rdfs:label or prefLabel
            label = data.get("label", {}).get("@value")
            if not label:
                label = data.get("prefLabel", {}).get("@value")
            if not label:
                # Try the @graph structure
                graph = data.get("@graph", [])
                for node in graph:
                    if "label" in node:
                        lbl = node["label"]
                        if isinstance(lbl, dict):
                            label = lbl.get("@value")
                        elif isinstance(lbl, str):
                            label = lbl
                        if label:
                            break
            if label:
                return label.upper().strip()
    except Exception:
        pass

    # ── Strategy 2: NLM MeSH RDF lookup ──
    try:
        url = f"https://id.nlm.nih.gov/mesh/lookup/descriptor?label={raw_id}&match=exact&limit=1"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if data and isinstance(data, list) and len(data) > 0:
                label = data[0].get("label")
                if label:
                    return label.upper().strip()
    except Exception:
        pass

    # ── Strategy 3: PubChem substance search ──
    try:
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/substance/sourceid/MeSH/{raw_id}/cids/JSON"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            info = resp.json().get("InformationList", {}).get("Information", [])
            if info and info[0].get("CID"):
                cid = info[0]["CID"][0]
                # Get name from CID
                url2 = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/Title/JSON"
                resp2 = requests.get(url2, timeout=8)
                if resp2.status_code == 200:
                    props = resp2.json().get("PropertyTable", {}).get("Properties", [])
                    if props and props[0].get("Title"):
                        return props[0]["Title"].upper().strip()
    except Exception:
        pass

    return None


def main():
    if not ENTITY_PATH.exists():
        print("Error: Run from TreeHacks/ root")
        return

    # Load entity index to find all MESH compounds
    with open(ENTITY_PATH) as f:
        entity_to_idx = json.load(f)

    mesh_compounds = [
        name.replace("Compound::", "")
        for name in entity_to_idx
        if name.startswith("Compound::MESH:")
    ]
    print(f"Total MESH compounds in KG: {len(mesh_compounds)}")

    # Load existing lookup
    lookup = {}
    if LOOKUP_PATH.exists():
        with open(LOOKUP_PATH) as f:
            lookup = json.load(f)

    # Find unresolved MESH IDs
    unresolved = []
    for mesh_id in mesh_compounds:
        entity = f"Compound::{mesh_id}"
        if entity not in lookup or not lookup[entity].get("drug_name"):
            unresolved.append(mesh_id)

    print(f"Already resolved: {len(mesh_compounds) - len(unresolved)}")
    print(f"Unresolved: {len(unresolved)}")

    if not unresolved:
        print("All MESH compounds already resolved!")
        return

    # Resolve
    resolved = 0
    for i, mesh_id in enumerate(unresolved):
        name = resolve_mesh_id(mesh_id)
        if name:
            entity = f"Compound::{mesh_id}"
            if entity not in lookup:
                lookup[entity] = {}
            lookup[entity]["drug_name"] = name
            resolved += 1

        if (i + 1) % 50 == 0 or i + 1 == len(unresolved):
            print(f"  {i+1}/{len(unresolved)} checked, {resolved} resolved")

        time.sleep(0.3)  # Rate limit

    # Save updated lookup
    with open(LOOKUP_PATH, "w") as f:
        json.dump(lookup, f, indent=2)

    print(f"\n✅ Resolved {resolved}/{len(unresolved)} MESH compounds")
    print(f"Updated {LOOKUP_PATH}")
    print(f"\nRe-run: python -m drug_rescue --disease glioblastoma --standalone")


if __name__ == "__main__":
    main()
