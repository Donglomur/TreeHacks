import { readdirSync, existsSync, mkdirSync, copyFileSync, writeFileSync, statSync, rmSync } from 'fs';
import { join, resolve, dirname } from 'path';

const outputsDir = resolve(process.argv[2] || '../Outputs');
const treeHacksDir = dirname(outputsDir);
const publicData = resolve('public/data');

console.log(`\n💊 RescueRx Data Sync (Dynamic Discovery)`);
console.log(`   Source: ${outputsDir}`);
console.log(`   Target: ${publicData}\n`);

if (!existsSync(outputsDir)) {
  console.error(`❌ Not found: ${outputsDir}\n   Usage: node sync-data.js /path/to/Outputs`);
  process.exit(1);
}

// Copy logo
const logoExts = ['.png', '.jpg', '.jpeg', '.svg', '.webp'];
for (const ext of logoExts) {
  const logoPath = join(treeHacksDir, `logo${ext}`);
  if (existsSync(logoPath)) {
    copyFileSync(logoPath, resolve(`public/logo${ext}`));
    console.log(`   🖼  Copied logo${ext}`);
    break;
  }
}

// Recursively find all .json and .md files
function findFiles(dir, base) {
  const results = [];
  if (!existsSync(dir)) return results;
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const rel = base ? join(base, entry) : entry;
    const st = statSync(full);
    if (st.isDirectory()) {
      results.push(...findFiles(full, rel));
    } else if (/\.(json|md)$/i.test(entry)) {
      results.push({ full, rel });
    }
  }
  return results;
}

// Known file→subfolder routing for flat layouts
const EVIDENCE_FILES = ['summary.json', 'clinical_trials.json', 'faers_signals.json', 'literature.json', 'molecular.json', 'summary.md'];
const COURT_FILES = ['advocate_brief.md', 'skeptic_brief.md', 'verdict.md', 'verdict_scores.json'];

// Folder aliases: trial/ → court/
const FOLDER_ALIASES = { 'trial': 'court' };

const diseases = [];

for (const entry of readdirSync(outputsDir)) {
  const ep = join(outputsDir, entry);
  if (!statSync(ep).isDirectory()) continue;

  const allFiles = findFiles(ep, '');
  const hasCand = allFiles.some(f => f.rel === 'candidates.json' || f.rel.endsWith('_candidates.json'));
  const hasAnyJson = allFiles.some(f => f.rel.endsWith('.json'));
  if (!hasCand && !hasAnyJson) { console.log(`   ⏭  Skipping ${entry}/`); continue; }

  const id = entry.toLowerCase().replace(/[^a-z0-9_-]/g, '_');
  const td = join(publicData, id);
  if (existsSync(td)) rmSync(td, { recursive: true, force: true });

  let n = 0;
  const copiedRels = new Set();

  for (const f of allFiles) {
    let destRel = f.rel;

    // Apply folder aliases (trial/ → court/)
    for (const [from, to] of Object.entries(FOLDER_ALIASES)) {
      if (destRel.startsWith(from + '/') || destRel.startsWith(from + '\\')) {
        destRel = to + destRel.substring(from.length);
      }
    }

    // Route flat files to correct subfolders
    const fileName = destRel.split('/').pop().split('\\').pop();
    if (!destRel.includes('/') && !destRel.includes('\\')) {
      if (EVIDENCE_FILES.includes(fileName)) destRel = join('evidence', fileName);
      else if (COURT_FILES.includes(fileName)) destRel = join('court', fileName);
    }

    const dest = join(td, destRel);
    const destDir = dirname(dest);
    if (!existsSync(destDir)) mkdirSync(destDir, { recursive: true });
    copyFileSync(f.full, dest);
    copiedRels.add(destRel);
    n++;
  }

  // Alias _candidates.json → candidates.json
  if (!copiedRels.has('candidates.json')) {
    const candFile = allFiles.find(f => f.rel.endsWith('_candidates.json'));
    if (candFile) {
      const dest = join(td, 'candidates.json');
      if (!existsSync(dirname(dest))) mkdirSync(dirname(dest), { recursive: true });
      copyFileSync(candFile.full, dest);
      n++;
    }
  }

  // Also copy molecular.json from trial/ into evidence/ if it's there but not in evidence/
  const molInEvidence = join(td, 'evidence/molecular.json');
  const molInCourt = join(td, 'court/molecular.json');
  if (!existsSync(molInEvidence) && existsSync(molInCourt)) {
    mkdirSync(dirname(molInEvidence), { recursive: true });
    copyFileSync(molInCourt, molInEvidence);
    console.log(`      ↳ Copied court/molecular.json → evidence/molecular.json`);
  }

  const hasEv = existsSync(join(td, 'evidence/summary.json')) || existsSync(join(td, 'evidence/literature.json'));
  const hasCo = existsSync(join(td, 'court/verdict_scores.json'));
  const hasTr = existsSync(join(td, 'evidence/clinical_trials.json'));
  const hasLit = existsSync(join(td, 'evidence/literature.json'));
  const hasMol = existsSync(join(td, 'evidence/molecular.json'));
  const hasFaers = existsSync(join(td, 'evidence/faers_signals.json'));

  diseases.push({
    id,
    label: entry.charAt(0).toUpperCase() + entry.slice(1).replace(/_/g, ' '),
    hasEvidence: hasEv, hasCourt: hasCo, hasTrials: hasTr,
  });
  console.log(`   ✅ ${entry} → ${n} files (ev:${hasEv?'✓':'✗'} lit:${hasLit?'✓':'✗'} mol:${hasMol?'✓':'✗'} faers:${hasFaers?'✓':'✗'} court:${hasCo?'✓':'✗'})`);
}

writeFileSync(join(publicData, 'manifest.json'), JSON.stringify({ generated: new Date().toISOString(), diseases }, null, 2));
console.log(`\n✅ Synced ${diseases.length} diseases\n`);
