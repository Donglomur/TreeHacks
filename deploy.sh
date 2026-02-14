#!/bin/bash
#
# DrugRescue Deployment Script
# ============================
# Copies all fixed files to the correct locations and clears caches.
#
# Usage: cd TreeHacks && bash deploy.sh
#

set -e

echo "🚀 DrugRescue Deployment"
echo "========================"
echo ""

# ── Detect project structure ──
# Nicholas has code at BOTH:
#   TreeHacks/drug_rescue/engines/faers.py   (root level)
#   TreeHacks/src/drug_rescue/engines/faers.py (src level — what Python imports!)
# We need to update BOTH.

ROOT_PKG=""
SRC_PKG=""

if [ -d "drug_rescue/engines" ]; then
    ROOT_PKG="drug_rescue"
    echo "✓ Found root-level package: drug_rescue/"
fi

if [ -d "src/drug_rescue/engines" ]; then
    SRC_PKG="src/drug_rescue"
    echo "✓ Found src-level package: src/drug_rescue/"
fi

if [ -z "$ROOT_PKG" ] && [ -z "$SRC_PKG" ]; then
    echo "✗ Cannot find drug_rescue package! Run from TreeHacks/ directory."
    exit 1
fi

# ── Determine source of truth ──
# The files in this script's directory are the latest versions
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo ""
echo "Source: $SCRIPT_DIR"
echo ""

# ── Copy function ──
copy_file() {
    local src="$1"
    local relpath="$2"
    
    if [ ! -f "$src" ]; then
        echo "  ✗ Source not found: $src"
        return 1
    fi
    
    local copied=0
    
    if [ -n "$ROOT_PKG" ]; then
        local dst="$ROOT_PKG/$relpath"
        mkdir -p "$(dirname "$dst")"
        cp "$src" "$dst"
        echo "  → $dst"
        copied=1
    fi
    
    if [ -n "$SRC_PKG" ]; then
        local dst="$SRC_PKG/$relpath"
        mkdir -p "$(dirname "$dst")"
        cp "$src" "$dst"
        echo "  → $dst"
        copied=1
    fi
    
    return 0
}

# ── Deploy files ──
echo "📦 Copying fixed files:"
echo ""

echo "  engines/faers.py (requests + count-endpoint apostrophe fix):"
copy_file "$SCRIPT_DIR/engines/faers.py" "engines/faers.py"

echo ""
echo "  tools/similarity.py (precomputed FPs + ConnectivitySMILES):"
copy_file "$SCRIPT_DIR/tools/similarity.py" "tools/similarity.py"

echo ""
echo "  tools/clinical_trials.py (requests migration):"
copy_file "$SCRIPT_DIR/tools/clinical_trials.py" "tools/clinical_trials.py"

echo ""
echo "  tools/_http.py (SSL helpers):"
copy_file "$SCRIPT_DIR/tools/_http.py" "tools/_http.py"

echo ""
echo "  tools/docking.py (ConnectivitySMILES fallback):"
copy_file "$SCRIPT_DIR/tools/docking.py" "tools/docking.py"

echo ""
echo "  tools/faers_safety.py (tool wrapper):"
copy_file "$SCRIPT_DIR/tools/faers_safety.py" "tools/faers_safety.py"

echo ""

# ── Copy test file to project root ──
echo "  test_tools.py → project root:"
if [ -f "$SCRIPT_DIR/test_tools.py" ]; then
    cp "$SCRIPT_DIR/test_tools.py" "./test_tools.py"
    echo "  → ./test_tools.py"
fi

# ── Clear __pycache__ ──
echo ""
echo "🧹 Clearing __pycache__:"
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo "  Done"

# ── Verify Python resolves to the right file ──
echo ""
echo "🔍 Import verification:"
python3 -c "
import sys
# Add src/ to path if it exists (matches what their project does)
import os
if os.path.isdir('src'):
    sys.path.insert(0, 'src')

import drug_rescue.engines.faers as fm
print(f'  faers.py loaded from: {fm.__file__}')
src = open(fm.__file__).read()

checks = [
    ('requests library', 'import requests' in src and '_req.get' in src),
    ('_count_exact_term', '_count_exact_term' in src),
    ('_event_broad_filter', '_event_broad_filter' in src),
    ('FAERSClient alias', 'FAERSClient = OpenFDAClient' in src),
    ('contingency apostrophe branch', \"has_apostrophe\" in src),
    ('caret normalization', '_normalize_term' in src and \"replace(\\\"^\\\"\" in src),
    ('correct alzheimer mapping', 'DEMENTIA ALZHEIMER' in src and \"ALZHEIMER\\'S DISEASE\" not in src.split('DISEASE_TO_MEDDRA')[1].split('}')[0] if 'DISEASE_TO_MEDDRA' in src else False),
]
all_ok = True
for label, ok in checks:
    print(f'  {\"✓\" if ok else \"✗\"} {label}')
    if not ok: all_ok = False

if all_ok:
    print('  ✅ All fixes verified!')
else:
    print('  ❌ Some fixes missing — check file paths')
"

echo ""
echo "═══════════════════════════════"
echo "  Ready! Run: python test_tools.py free"
echo "═══════════════════════════════"
