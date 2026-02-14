#!/usr/bin/env python3
"""
DrugRescue Deep Diagnostic
===========================
Run this on your Mac to find EXACTLY what's broken.

    python diagnose.py

Tests SSL, PubChem, ClinicalTrials.gov, and FAERS event queries
with full error output — no silent swallowing.
"""
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
import sys

# ── Colors ──
G = "\033[92m"  # green
R = "\033[91m"  # red
Y = "\033[93m"  # yellow
B = "\033[1m"   # bold
E = "\033[0m"   # reset


def section(title):
    print(f"\n{B}{'='*60}{E}")
    print(f"  {B}{title}{E}")
    print(f"{B}{'='*60}{E}\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SSL CONTEXT TESTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

section("1. SSL CONTEXT")

# Try default
try:
    ctx = ssl.create_default_context()
    print(f"  ssl.create_default_context() → {G}created{E}")
except Exception as e:
    print(f"  ssl.create_default_context() → {R}FAILED: {e}{E}")

# Try certifi
try:
    import certifi
    ctx_cert = ssl.create_default_context(cafile=certifi.where())
    print(f"  certifi → {G}found: {certifi.where()}{E}")
except ImportError:
    print(f"  certifi → {Y}NOT INSTALLED (pip install certifi){E}")

# Try macOS cert
import os
for path in ["/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"]:
    exists = os.path.exists(path)
    print(f"  {path} → {'exists' if exists else 'not found'}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  HELPER: fetch with full error reporting
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Unverified context for all tests (since we know macOS has SSL issues)
_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE


def fetch(label, url, headers=None):
    """Fetch URL with FULL error reporting."""
    print(f"  {B}{label}{E}")
    print(f"    URL: {url[:120]}{'...' if len(url) > 120 else ''}")
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15, context=_ctx) as resp:
            body = resp.read().decode()
            data = json.loads(body) if body.startswith("{") or body.startswith("[") else body
            status = resp.status
            print(f"    {G}HTTP {status}{E}")
            return data, status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        print(f"    {R}HTTP {e.code}{E}: {body[:200]}")
        return None, e.code
    except urllib.error.URLError as e:
        print(f"    {R}URLError{E}: {e.reason}")
        return None, 0
    except Exception as e:
        print(f"    {R}Exception{E}: {type(e).__name__}: {e}")
        return None, 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. PUBCHEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

section("2. PUBCHEM SMILES")

PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{}/property/CanonicalSMILES/JSON"
for drug in ["aspirin", "metformin", "temozolomide"]:
    encoded = urllib.parse.quote(drug, safe="")
    url = PUBCHEM.format(encoded)
    data, code = fetch(drug, url)
    if data and isinstance(data, dict):
        props = data.get("PropertyTable", {}).get("Properties", [])
        if props:
            smiles = props[0].get("CanonicalSMILES", "?")
            print(f"    → {G}SMILES: {smiles[:60]}{E}")
        else:
            print(f"    → {R}No properties in response{E}")
            print(f"    → Response: {json.dumps(data)[:200]}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. CLINICALTRIALS.GOV
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

section("3. CLINICALTRIALS.GOV")

CT_BASE = "https://clinicaltrials.gov/api/v2/studies"

# Test without User-Agent
params = {"query.intr": "metformin", "filter.overallStatus": "TERMINATED", "pageSize": 1}
qs = urllib.parse.urlencode(params)
data, code = fetch("Without User-Agent", f"{CT_BASE}?{qs}")

# Test WITH User-Agent
data2, code2 = fetch(
    "With User-Agent",
    f"{CT_BASE}?{qs}",
    headers={"User-Agent": "DrugRescue/1.0 (academic research; TreeHacks 2026)"},
)
if data2 and isinstance(data2, dict):
    total = data2.get("totalCount", "?")
    studies = data2.get("studies", [])
    print(f"    → {G}totalCount={total}, returned {len(studies)} studies{E}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. FAERS — Drug vs Event queries
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

section("4. FAERS — Comparing Drug vs Event Queries")

FAERS = "https://api.fda.gov/drug/event.json"

def faers_count(label, search):
    """Count FAERS reports for a search term."""
    params = {"search": search, "count": "receivedate"}
    qs = urllib.parse.urlencode(params)
    url = f"{FAERS}?{qs}"
    data, code = fetch(label, url)
    if data and isinstance(data, dict) and "results" in data:
        total = sum(r.get("count", 0) for r in data["results"])
        print(f"    → {G}{total:,} reports{E}")
        return total
    print(f"    → {R}0 reports (code={code}){E}")
    return 0


# Drug queries (these work)
print(f"  {Y}--- Drug queries (should work) ---{E}")
faers_count("metformin (generic_name.exact)",
    'patient.drug.openfda.generic_name.exact:"METFORMIN"')
faers_count("aspirin (generic_name.exact)",
    'patient.drug.openfda.generic_name.exact:"ASPIRIN"')

# Event queries — test ALL variants
print(f"\n  {Y}--- Event queries: SINGLE WORD ---{E}")
faers_count("DEMENTIA (no .exact, uppercase)",
    'patient.reaction.reactionmeddrapt:"DEMENTIA"')
faers_count("DEMENTIA (.exact, uppercase)",
    'patient.reaction.reactionmeddrapt.exact:"DEMENTIA"')
faers_count("dementia (no .exact, lowercase)",
    'patient.reaction.reactionmeddrapt:"dementia"')
faers_count("Dementia (no .exact, titlecase)",
    'patient.reaction.reactionmeddrapt:"Dementia"')

print(f"\n  {Y}--- Event queries: MULTI-WORD ---{E}")
faers_count("DRUG INEFFECTIVE (no .exact)",
    'patient.reaction.reactionmeddrapt:"DRUG INEFFECTIVE"')
faers_count("DRUG INEFFECTIVE (.exact)",
    'patient.reaction.reactionmeddrapt.exact:"DRUG INEFFECTIVE"')
faers_count("MEMORY IMPAIRMENT (.exact)",
    'patient.reaction.reactionmeddrapt.exact:"MEMORY IMPAIRMENT"')
faers_count("NAUSEA (.exact)",
    'patient.reaction.reactionmeddrapt.exact:"NAUSEA"')

print(f"\n  {Y}--- Event queries: WITH APOSTROPHE ---{E}")
faers_count("Alzheimer's disease (.exact)",
    "patient.reaction.reactionmeddrapt.exact:\"Alzheimer's disease\"")
faers_count("ALZHEIMER'S DISEASE (.exact)",
    "patient.reaction.reactionmeddrapt.exact:\"ALZHEIMER'S DISEASE\"")

print(f"\n  {Y}--- Combined drug+event (contingency 'a' cell) ---{E}")
faers_count("metformin AND nausea",
    'patient.drug.openfda.generic_name.exact:"METFORMIN"+AND+patient.reaction.reactionmeddrapt.exact:"NAUSEA"')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  5. URL ENCODING COMPARISON
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

section("5. URL ENCODING DEEP DIVE")

print("  What urllib.parse.urlencode produces:")
tests = [
    ("Drug (no spaces)", 'patient.drug.openfda.generic_name.exact:"METFORMIN"'),
    ("Event single word", 'patient.reaction.reactionmeddrapt:"DEMENTIA"'),
    ("Event multi-word", 'patient.reaction.reactionmeddrapt:"DRUG INEFFECTIVE"'),
    ("Event apostrophe", "patient.reaction.reactionmeddrapt:\"ALZHEIMER'S DISEASE\""),
    ("Event .exact", 'patient.reaction.reactionmeddrapt.exact:"NAUSEA"'),
]
for label, search in tests:
    encoded = urllib.parse.urlencode({"search": search, "count": "receivedate"})
    print(f"    {label}:")
    print(f"      raw:     search={search}")
    print(f"      encoded: {encoded}")
    print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SUMMARY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

section("DONE — Copy/paste ALL output above and share it!")
print("  This tells us exactly which URL format works for each API.")
