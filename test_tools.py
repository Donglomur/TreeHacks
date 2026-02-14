#!/usr/bin/env python3
"""
DrugRescue Tool Tests
======================
Usage:
    python test_tools.py                  # run ALL tests
    python test_tools.py free             # only free tests (no API keys)
    python test_tools.py trials           # ClinicalTrials.gov
    python test_tools.py faers            # FAERS inverse signal
    python test_tools.py suggest          # FAERS event discovery
    python test_tools.py pubchem          # PubChem SMILES
    python test_tools.py kg               # KG discovery (needs data/)
    python test_tools.py similarity       # RDKit fingerprints (needs rdkit)
    python test_tools.py literature       # Perplexity (needs API key)
    python test_tools.py docking          # NVIDIA DiffDock (needs API key)
"""

import asyncio
import json
import sys
import time
import os
import logging
import shutil

# Enable logging so we see actual errors from tools
logging.basicConfig(level=logging.WARNING, format="    ⚠ %(name)s: %(message)s")

# ── Path setup: ensure we import from the right location ──
# Nicholas has drug_rescue/ at BOTH:
#   TreeHacks/drug_rescue/          (root level)
#   TreeHacks/src/drug_rescue/      (src level — often what Python finds)
# After deploy.sh, both are identical. But make sure Python finds one.
for search_dir in ["src", "."]:
    candidate = os.path.join(search_dir, "drug_rescue", "engines", "faers.py")
    if os.path.exists(candidate):
        abs_dir = os.path.abspath(search_dir)
        if abs_dir not in sys.path:
            sys.path.insert(0, abs_dir)
        break

# Clear __pycache__ everywhere to ensure fresh code
for search_root in ["drug_rescue", "src/drug_rescue"]:
    if os.path.isdir(search_root):
        for root, dirs, files in os.walk(search_root):
            for d in dirs:
                if d == "__pycache__":
                    shutil.rmtree(os.path.join(root, d), ignore_errors=True)

# ── Deployment check — confirm key fixes are present ──
print("\n🔍 Deployment check:")
_ok = True

# Check FAERS uses requests (not urllib)
import drug_rescue.engines.faers as _fm
print(f"  Loading from: {_fm.__file__}")
_src = open(_fm.__file__).read()
if "import requests" in _src and "_req.get" in _src:
    print("  ✓ engines/faers.py — HTTP via requests library")
else:
    print("  ✗ engines/faers.py — Still using urllib! Run: bash deploy.sh")
    _ok = False

# Check FAERS uses count endpoint for apostrophe terms
if "_count_exact_term" in _src and "_event_broad_filter" in _src:
    print("  ✓ engines/faers.py — Count endpoint for apostrophe terms")
else:
    print("  ✗ engines/faers.py — Missing count-endpoint fix! Run: bash deploy.sh")
    _ok = False

# Check caret normalization
if "_normalize_term" in _src and 'replace("^"' in _src:
    print("  ✓ engines/faers.py — Caret (^) ↔ apostrophe (') normalization")
else:
    print("  ✗ engines/faers.py — Missing caret normalization! Run: bash deploy.sh")
    _ok = False

# Check FAERSClient alias exists
if "FAERSClient = OpenFDAClient" in _src or "class FAERSClient" in _src:
    print("  ✓ engines/faers.py — FAERSClient alias present")
else:
    print("  ✗ engines/faers.py — Missing FAERSClient alias! Run: bash deploy.sh")
    _ok = False

# Check PubChem uses requests + ConnectivitySMILES fallback
import drug_rescue.tools.similarity as _sm
_src2 = open(_sm.__file__).read()
if "requests" in _src2 and "ConnectivitySMILES" in _src2:
    print("  ✓ tools/similarity.py — PubChem via requests + ConnectivitySMILES fallback")
elif "requests" in _src2:
    print("  ✗ tools/similarity.py — has requests but MISSING ConnectivitySMILES fallback")
    _ok = False
else:
    print("  ✗ tools/similarity.py — OLD VERSION! Still using urllib")
    _ok = False

# Check similarity uses precomputed FPs
if "_get_precomputed_fp" in _src2 and "_name_to_idx" in _src2:
    print("  ✓ tools/similarity.py — Precomputed FP lookup (no rdkit needed)")
else:
    print("  ✗ tools/similarity.py — Missing precomputed FP support")
    _ok = False

# Check CT.gov uses requests
import drug_rescue.tools.clinical_trials as _ct
_src3 = open(_ct.__file__).read()
if "requests" in _src3 and "_requests.get" in _src3:
    print("  ✓ tools/clinical_trials.py — CT.gov via requests")
else:
    print("  ✗ tools/clinical_trials.py — OLD VERSION! Still using urllib")
    _ok = False

if not _ok:
    print("\n  ❌ STALE FILES DETECTED!")
    print("     Python is loading from:", _fm.__file__)
    print("")
    print("     FIX: Run the deployment script first:")
    print("       bash deploy.sh")
    print("       python test_tools.py free")
    print("")
    print("     Or manually copy all files from the download to BOTH:")
    print("       drug_rescue/engines/faers.py")
    print("       src/drug_rescue/engines/faers.py  (if src/ exists)")
    print("       (same for tools/similarity.py, tools/clinical_trials.py, etc.)")
    if "--force" not in sys.argv:
        print("\n     Add --force to run tests anyway against stale code.")
        sys.exit(1)
print()


def pp(result: dict):
    text = result["content"][0]["text"]
    data = json.loads(text)
    print(json.dumps(data, indent=2)[:3000])
    if len(text) > 3000:
        print(f"\n  ... ({len(text)} chars total, truncated)")
    if result.get("is_error"):
        print("  ⚠️  TOOL RETURNED ERROR")
    print()


def header(name: str):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}\n")


def check_certifi():
    try:
        import certifi  # noqa: F401
        return True
    except ImportError:
        return False


# ── KG Discovery ──

async def test_kg():
    header("KG Discovery — discover_candidates")
    from drug_rescue.tools.kg_discovery import (
        discover_candidates_tool, score_specific_drugs_tool, kg_info_tool,
        set_data_dir,
    )
    import drug_rescue.tools.kg_discovery as _kg_mod

    # Try multiple data paths
    data_candidates = [
        "./data",
        "../data",
        "src/data",
        os.path.join(os.path.dirname(_kg_mod.__file__), "..", "..", "data"),
        os.path.join(os.path.dirname(_kg_mod.__file__), "..", "data"),
    ]
    for candidate in data_candidates:
        if os.path.isdir(candidate):
            set_data_dir(candidate)
            break
    else:
        set_data_dir("./data")

    # ── Graph info ──
    print("📊 kg_info:")
    info_r = await kg_info_tool({})
    info = json.loads(info_r["content"][0]["text"])
    print(f"   Graph: {info.get('compounds', '?')} compounds, "
          f"{info.get('diseases', '?')} diseases, "
          f"{info.get('genes', '?')} genes")
    print(f"   Method: {info.get('method', '?')}, "
          f"Dim: {info.get('embedding_shape', '?')}")
    print(f"   Relations: {', '.join(info.get('treatment_relations', []))}\n")

    # ── Discover (dropped-only, top 20 — tool defaults) ──
    print("🔬 discover_candidates (glioblastoma, dropped-only, top 20):")
    t0 = time.time()
    r = await discover_candidates_tool({
        "disease": "glioblastoma",
    })
    elapsed = time.time() - t0
    data = json.loads(r["content"][0]["text"])

    if "error" in data and "candidates" not in data:
        print(f"  ❌ {data['error']}")
        if "hint" in data:
            print(f"  💡 {data['hint']}")
        return

    print(f"  ✅ Scored {data['total_compounds_scored']:,} compounds "
          f"in {data['timing_ms']:.0f}ms ({data['method']})")
    print(f"  📊 {data['candidates_returned']} candidates: "
          f"{data['stats'].get('dropped', 0)} dropped, "
          f"{data['stats'].get('withdrawn', 0)} withdrawn, "
          f"{data['stats'].get('novel', 0)} novel")
    print(f"  ⏱  {elapsed:.2f}s total\n")

    # ── Display table ──
    candidates = data.get("candidates", [])
    if candidates:
        print(f"  {'#':<3} {'Drug':<28} {'Status':<10} {'Phase':<6} "
              f"{'Pctl':<7} {'Z':<7} {'Score':<6} {'SMILES'}")
        print(f"  {'─'*3} {'─'*28} {'─'*10} {'─'*6} {'─'*7} {'─'*7} {'─'*6} {'─'*5}")

        dropped = [c for c in candidates if c["status"] == "dropped"]
        withdrawn = [c for c in candidates if c["status"] == "withdrawn"]
        novel = [c for c in candidates if c["status"] == "novel"]

        rank = 1
        for section, label in [
            (dropped, "\n  🎯 DROPPED — Prime repurposing targets"),
            (withdrawn, "\n  ⚠️  WITHDRAWN"),
            (novel, "\n  💊 KNOWN/NOVEL DRUGS"),
        ]:
            if not section:
                continue
            print(label)
            for c in section:
                smiles = "✓" if c.get("smiles") else "—"
                phase = str(c.get("max_phase") or "—")
                name = c["drug_name"][:26]
                print(f"  {rank:<3} {name:<28} {c['status']:<10} "
                      f"{phase:<6} {c['kg_percentile']:<7.1f} "
                      f"{c['kg_z_score']:<7.2f} {c['kg_normalized']:<6.2f} "
                      f"{smiles}")
                rank += 1

        if dropped:
            print(f"\n  {'='*56}")
            print(f"  REPURPOSING CANDIDATES — Dropped Phase II/III drugs")
            print(f"  {'='*56}")
            for c in dropped:
                phase = f"Phase {c['max_phase']}" if c.get("max_phase") else "?"
                print(f"  • {c['drug_name']} ({phase}, z={c['kg_z_score']:.2f}, "
                      f"pctl={c['kg_percentile']:.1f})")
    print()

    # ── Also test include_novel=True ──
    print("🔬 discover_candidates (glioblastoma, ALL, top 5):")
    r2 = await discover_candidates_tool({
        "disease": "glioblastoma",
        "max_candidates": 5,
        "min_percentile": 90.0,
        "include_novel": True,
    })
    pp(r2)

    # ── Score specific drugs ──
    print("🎯 score_specific_drugs (metformin + aspirin vs glioblastoma):")
    pp(await score_specific_drugs_tool({
        "disease": "glioblastoma",
        "drug_names": ["metformin", "aspirin"],
    }))


# ── Clinical Trials ──

async def test_trials():
    header("Clinical Trials — clinical_trial_failure")
    from drug_rescue.tools.clinical_trials import clinical_trial_failure_tool

    print("🏥 bevacizumab + glioblastoma:")
    t0 = time.time()
    r = await clinical_trial_failure_tool({
        "drug_name": "bevacizumab",
        "disease": "glioblastoma",
        "max_results": 5,
    })
    print(f"  ⏱  {time.time()-t0:.2f}s")
    pp(r)

    print("🏥 metformin (all indications):")
    t0 = time.time()
    r = await clinical_trial_failure_tool({
        "drug_name": "metformin",
        "max_results": 5,
    })
    print(f"  ⏱  {time.time()-t0:.2f}s")
    pp(r)


# ── FAERS ──

async def test_faers():
    header("FAERS — faers_inverse_signal")

    from urllib.parse import quote_plus
    import requests as _req
    base = "https://api.fda.gov/drug/event.json"

    # ── Test 1: Prove the apostrophe bug exists ──
    print("  1. Proving the apostrophe bug (these should fail):")
    for label, search in [
        ("exact+quotes", 'patient.reaction.reactionmeddrapt.exact:"ALZHEIMER\'S DISEASE"'),
        ("base+quotes",  'patient.reaction.reactionmeddrapt:"ALZHEIMER\'S DISEASE"'),
    ]:
        url = f"{base}?search={quote_plus(search, safe='()*')}&count=receivedate"
        resp = _req.get(url, timeout=10)
        print(f"    {label:20s} → HTTP {resp.status_code} {'✗ (expected!)' if not resp.ok else '✓ (unexpected!)'}")

    # ── Test 2: Prove clean terms work on .exact ──
    print("  2. Clean terms on .exact (should work):")
    for term in ["NAUSEA", "DEMENTIA", "COGNITIVE DISORDER"]:
        resp = _req.get(base, params={
            "search": f'patient.reaction.reactionmeddrapt.exact:"{term}"',
            "count": "receivedate",
        }, timeout=10)
        if resp.ok:
            total = sum(r["count"] for r in resp.json().get("results", []))
            print(f"    {term:30s} → {total:>10,} reports ✓")
        else:
            print(f"    {term:30s} → HTTP {resp.status_code} ✗")

    # ── Test 3: COUNT ENDPOINT approach (our fix!) ──
    print("  3. Count endpoint — single variant terms:")
    for term, broad in [
        ("PARKINSON'S DISEASE", "PARKINSON*"),
        ("MEMORY IMPAIRMENT",   "MEMORY+AND+patient.reaction.reactionmeddrapt:IMPAIRMENT"),
    ]:
        search = f"patient.reaction.reactionmeddrapt:{broad}"
        resp = _req.get(base, params={
            "search": search,
            "count": "patient.reaction.reactionmeddrapt.exact",
            "limit": 100,
        }, timeout=10)
        if resp.ok:
            results = resp.json().get("results", [])
            found = None
            for r in results:
                if r.get("term", "").upper() == term.upper():
                    found = r["count"]
                    break
            if found is not None:
                print(f"    {term:35s} → {found:>10,} reports ✓")
            else:
                top3 = [f"{r['term']}={r['count']}" for r in results[:3]]
                print(f"    {term:35s} → ✗ not found: {top3}")
        else:
            print(f"    {term:35s} → HTTP {resp.status_code} ✗")

    # ── Test 4: Caret vs apostrophe normalization ──
    print("  4. Caret (^) vs apostrophe (') normalization — THE KEY FIX:")
    print("     FAERS has BOTH DEMENTIA ALZHEIMER'S TYPE and DEMENTIA ALZHEIMER^S TYPE")
    search = "patient.reaction.reactionmeddrapt:DEMENTIA AND patient.reaction.reactionmeddrapt:ALZHEIMER*"
    resp = _req.get(base, params={
        "search": search,
        "count": "patient.reaction.reactionmeddrapt.exact",
        "limit": 100,
    }, timeout=10)
    if resp.ok:
        results = resp.json().get("results", [])
        apost_count = 0
        caret_count = 0
        for r in results:
            t = r.get("term", "")
            if "ALZHEIMER'S" in t.upper():
                apost_count += r["count"]
                print(f"      apostrophe: {t:40s} = {r['count']:>8,}")
            elif "ALZHEIMER^S" in t.upper():
                caret_count += r["count"]
                print(f"      caret:      {t:40s} = {r['count']:>8,}")
        total = apost_count + caret_count
        print(f"      ─────────────────────────────────────────────────")
        print(f"      SUM (our engine sums both):             = {total:>8,}")
        if apost_count > 0 and caret_count > 0:
            pct = caret_count / total * 100
            print(f"      Without ^ normalization we'd lose {pct:.0f}% of data!")
    else:
        print(f"    → HTTP {resp.status_code} ✗")

    # ── Test 5: Drug AND event via count endpoint ──
    print("  5. Drug AND event (metformin + DEMENTIA ALZHEIMER'S TYPE):")
    search = ('patient.drug.openfda.generic_name.exact:"METFORMIN" AND '
              'patient.reaction.reactionmeddrapt:DEMENTIA AND '
              'patient.reaction.reactionmeddrapt:ALZHEIMER*')
    resp = _req.get(base, params={
        "search": search,
        "count": "patient.reaction.reactionmeddrapt.exact",
        "limit": 100,
    }, timeout=10)
    if resp.ok:
        results = resp.json().get("results", [])
        total = 0
        for r in results:
            t = r.get("term", "").upper()
            norm = t.replace("^", "'")
            if "ALZHEIMER'S" in norm:
                total += r["count"]
                print(f"      {r['term']:40s} = {r['count']:>6,}")
        if total > 0:
            print(f"      SUM (normalized):                      = {total:>6,} ✓")
        else:
            print(f"      ✗ no Alzheimer variants found")
    else:
        print(f"    → HTTP {resp.status_code} ✗")
    print()

    # ── Test 6: Engine verification ──
    try:
        from drug_rescue.engines.faers import OpenFDAClient
        client_cls = OpenFDAClient
    except ImportError:
        try:
            from drug_rescue.engines.faers import FAERSClient
            client_cls = FAERSClient
        except ImportError:
            client_cls = None
            print("  ⚠️  Cannot import OpenFDAClient/FAERSClient — engine class test skipped")

    if client_cls:
        print("  Engine query verification:")
        for term in ["NAUSEA", "DEMENTIA ALZHEIMER'S TYPE", "PARKINSON'S DISEASE", "COGNITIVE DISORDER"]:
            q = client_cls.event_query(term)
            is_apost = "'" in term
            print(f"    {term:35s} → {q[:70]}")
            if is_apost:
                if "'" not in q and "reactionmeddrapt:" in q:
                    print(f"      ✓ Broad filter (no apostrophe in query)")
                else:
                    print(f"      ✗ BAD: apostrophe still in query!")
            else:
                if '.exact:' in q and '"' in q:
                    print(f"      ✓ Clean term, .exact with quotes")
                else:
                    print(f"      ✗ Unexpected format")

        # Verify disease mapping
        from drug_rescue.engines.faers import DISEASE_TO_MEDDRA
        alz_terms = DISEASE_TO_MEDDRA.get("alzheimer", [])
        print(f"\n  Disease mapping verification:")
        print(f"    alzheimer → {alz_terms}")
        if "ALZHEIMER'S DISEASE" in alz_terms:
            print(f"    ✗ BAD: 'ALZHEIMER'S DISEASE' is NOT a valid FAERS term!")
        elif "DEMENTIA ALZHEIMER'S TYPE" in alz_terms:
            print(f"    ✓ Uses correct MedDRA PT: DEMENTIA ALZHEIMER'S TYPE")
        
        # Verify normalization
        if hasattr(client_cls, '_normalize_term'):
            t1 = client_cls._normalize_term("DEMENTIA ALZHEIMER^S TYPE")
            t2 = client_cls._normalize_term("DEMENTIA ALZHEIMER'S TYPE")
            print(f"    Normalize test: '{t1}' == '{t2}' → {'✓' if t1 == t2 else '✗'}")
        print()

    # ── Test 7: Full pipeline ──
    from drug_rescue.tools.faers_safety import faers_inverse_signal_tool

    print("🛡️  metformin + aspirin vs alzheimer (FDR):")
    t0 = time.time()
    r = await faers_inverse_signal_tool({
        "disease": "alzheimer",
        "candidate_drugs": ["metformin", "aspirin"],
        "correction": "fdr",
    })
    print(f"  ⏱  {time.time()-t0:.2f}s")
    pp(r)


async def test_suggest():
    header("FAERS — faers_suggest_events")
    from drug_rescue.tools.faers_safety import faers_suggest_events_tool

    print("📋 Top 10 events for metformin:")
    t0 = time.time()
    r = await faers_suggest_events_tool({"drug": "metformin", "limit": 10})
    print(f"  ⏱  {time.time()-t0:.2f}s")
    pp(r)

    print("📋 Global top 10 events:")
    pp(await faers_suggest_events_tool({"limit": 10}))


# ── PubChem ──

async def test_pubchem():
    header("PubChem SMILES Lookup")

    # Direct requests test first
    print("  Direct test via requests:")
    try:
        import requests as _req
        url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/aspirin/property/CanonicalSMILES/JSON"
        resp = _req.get(url, timeout=10)
        print(f"    HTTP {resp.status_code} | {len(resp.content)} bytes")
        if resp.ok:
            data = resp.json()
            smiles = data["PropertyTable"]["Properties"][0]["CanonicalSMILES"]
            print(f"    aspirin SMILES: {smiles}")
        else:
            print(f"    Response: {resp.text[:200]}")
    except Exception as e:
        print(f"    ✗ {type(e).__name__}: {e}")

    # Through tool code
    print("\n  Through tool code:")
    from drug_rescue.tools.similarity import _fetch_smiles_pubchem

    drugs = ["metformin", "temozolomide", "aspirin", "bevacizumab", "fake_drug_xyz"]
    for name in drugs:
        smiles = _fetch_smiles_pubchem(name)
        if smiles:
            display = f"{smiles[:50]}..." if len(smiles) > 50 else smiles
            print(f"    {name:20s} → ✓ {display}")
        else:
            print(f"    {name:20s} → ✗ Not found")
    print()


# ── Literature ──

async def test_literature():
    header("Literature — literature_search (4-query pipeline)")
    if not os.environ.get("PERPLEXITY_API_KEY"):
        print("  ⚠️  PERPLEXITY_API_KEY not set — skipping")
        return
    from drug_rescue.tools.literature import literature_search_tool

    print("📚 metformin × glioblastoma:")
    t0 = time.time()
    r = await literature_search_tool({
        "drug_name": "metformin",
        "disease": "glioblastoma",
    })
    print(f"  ⏱  {time.time()-t0:.2f}s")
    pp(r)


# ── Similarity ──

async def test_similarity():
    header("Molecular Similarity — molecular_similarity")
    from drug_rescue.tools.similarity import (
        molecular_similarity_tool, set_data_dir,
        _load_fp_database, _fp_matrix, _drug_index, _name_to_idx,
        _check_rdkit,
    )

    # Try multiple data paths (relative to cwd)
    import drug_rescue.tools.similarity as _sim_mod
    data_candidates = [
        "./data",
        "../data",
        "src/data",
        os.path.join(os.path.dirname(_sim_mod.__file__), "..", "..", "data"),
        os.path.join(os.path.dirname(_sim_mod.__file__), "..", "data"),
    ]

    data_dir = None
    for candidate in data_candidates:
        fp_path = os.path.join(candidate, "fingerprints", "morgan_fps.npy")
        if os.path.exists(fp_path):
            data_dir = candidate
            break

    if data_dir:
        print(f"  Data dir: {os.path.abspath(data_dir)}")
        set_data_dir(data_dir)
    else:
        print(f"  Data dir: not found (tried: {[os.path.abspath(c) for c in data_candidates]})")
        set_data_dir("./data")

    # Force reload
    _sim_mod._fp_matrix = None
    _sim_mod._name_to_idx = {}
    _load_fp_database()

    # Re-import after reload
    from drug_rescue.tools.similarity import _fp_matrix, _drug_index, _name_to_idx

    has_rdkit = _check_rdkit()
    has_db = _fp_matrix is not None and len(_fp_matrix) > 0

    print(f"  RDKit: {'✓' if has_rdkit else '✗ (not installed)'}")
    print(f"  Precomputed FPs: {'✓ ' + str(len(_drug_index)) + ' drugs' if has_db else '✗ not found'}")
    print(f"  Name index: {len(_name_to_idx)} entries")

    if not has_rdkit and not has_db:
        print("  ⚠️  Neither rdkit nor precomputed FPs available — skipping")
        return

    # Show sample names from the database
    if has_db and _drug_index:
        sample_names = [e.get("name", "?") for e in _drug_index[:5]]
        print(f"  Sample drug names: {sample_names}")

        # Check if our test drugs are in the database
        for drug in ["temozolomide", "metformin", "aspirin", "carmustine"]:
            found = drug.lower() in _name_to_idx
            print(f"    {drug:20s} → {'✓ in DB' if found else '✗ not in DB'}")
    print()

    print("🧬 Temozolomide (by name) vs glioblastoma approved drugs:")
    t0 = time.time()
    r = await molecular_similarity_tool({
        "disease": "glioblastoma",
        "candidate_smiles": "temozolomide",
        "candidate_name": "Temozolomide",
    })
    print(f"  ⏱  {time.time()-t0:.2f}s")
    pp(r)

    if has_rdkit:
        print("🧬 Metformin (raw SMILES) vs diabetes drugs:")
        r = await molecular_similarity_tool({
            "disease": "diabetes",
            "candidate_smiles": "CN(C)C(=N)NC(=N)N",
            "candidate_name": "Metformin",
        })
        pp(r)
    else:
        print("🧬 Metformin (by name) vs diabetes drugs:")
        r = await molecular_similarity_tool({
            "disease": "diabetes",
            "candidate_smiles": "metformin",
            "candidate_name": "Metformin",
        })
        pp(r)

    print("🧬 Screen glioblastoma approved drugs against FP database:")
    r = await molecular_similarity_tool({
        "disease": "glioblastoma",
        "min_similarity": 0.5,
        "top_k": 5,
    })
    pp(r)


# ── Docking ──

async def test_docking():
    header("Molecular Docking — molecular_docking")
    if not os.environ.get("NVIDIA_API_KEY"):
        print("  ⚠️  NVIDIA_API_KEY not set — skipping")
        return
    from drug_rescue.tools.docking import molecular_docking_tool

    print("🔬 metformin vs 1 alzheimer target:")
    t0 = time.time()
    r = await molecular_docking_tool({
        "drug_smiles": "metformin",
        "drug_name": "Metformin",
        "disease": "alzheimer",
        "num_poses": 2,
        "max_targets": 1,
    })
    print(f"  ⏱  {time.time()-t0:.2f}s")
    pp(r)


# ── Runner ──

TESTS = {
    "kg":         test_kg,
    "trials":     test_trials,
    "faers":      test_faers,
    "suggest":    test_suggest,
    "pubchem":    test_pubchem,
    "literature": test_literature,
    "similarity": test_similarity,
}

FREE_TESTS = ["trials", "faers", "suggest", "pubchem", "similarity"]


async def run_all():
    print("\n" + "🚀" * 30)
    print("  DrugRescue Tool Smoke Tests")
    print("🚀" * 30)

    has_certifi = check_certifi()
    env = {
        "certifi":             "✓" if has_certifi else "✗ (pip install certifi — needed for macOS SSL)",
        "PERPLEXITY_API_KEY":  "✓" if os.environ.get("PERPLEXITY_API_KEY") else "✗ (literature skipped)",
        "OPENFDA_API_KEY":     "✓" if os.environ.get("OPENFDA_API_KEY") else "– (optional)",
    }
    print("\n  Environment:")
    for k, v in env.items():
        print(f"    {k}: {v}")
    if not has_certifi:
        print("\n  ⚠️  Install certifi first: pip install certifi")
        print("     Without it, SSL connections will fail on macOS.\n")

    passed, failed, skipped = 0, 0, 0
    for name, fn in TESTS.items():
        try:
            await fn()
            passed += 1
            print(f"  ✅ {name}\n")
        except Exception as e:
            err = str(e).lower()
            if "skip" in err or "not set" in err or "not installed" in err:
                skipped += 1
                print(f"  ⏭️  {name} skipped: {e}\n")
            else:
                failed += 1
                print(f"  ❌ {name} FAILED: {e}\n")
                import traceback; traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"  {passed} passed · {failed} failed · {skipped} skipped")
    print(f"{'='*60}\n")


async def main():
    args = sys.argv[1:]
    if not args:
        await run_all()
    elif args[0] == "free":
        for name in FREE_TESTS:
            try:
                await TESTS[name]()
                print(f"  ✅ {name}\n")
            except Exception as e:
                print(f"  ❌ {name}: {e}\n")
    elif args[0] in TESTS:
        await TESTS[args[0]]()
    else:
        print(f"Unknown: '{args[0]}'")
        print(f"Options: {', '.join(TESTS.keys())}, free")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
