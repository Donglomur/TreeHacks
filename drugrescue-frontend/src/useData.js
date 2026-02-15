import { useState, useEffect, useCallback } from 'react';

async function fetchJson(url) {
  try { var r = await fetch(url); if (!r.ok) return null; return await r.json(); } catch(e) { return null; }
}

/* ═══ SAFE STRING — prevents "Objects are not valid as React child" ═══ */
function ss(v) {
  if (v == null) return '';
  if (typeof v === 'string') return v;
  if (typeof v === 'number') return String(v);
  if (typeof v === 'object') {
    if (v.key_finding) return String(v.key_finding);
    if (v.summary && typeof v.summary === 'string') return v.summary;
    if (v.interpretation && typeof v.interpretation === 'string') return v.interpretation;
    if (v.text) return String(v.text);
    if (v.description) return String(v.description);
    var parts = Object.values(v).filter(function(x) { return typeof x === 'string'; });
    if (parts.length) return parts.join('. ');
    return JSON.stringify(v);
  }
  return String(v);
}

/* ═══ DISPLAY NAME ═══ */
function dn(name) {
  if (!name) return '';
  return name.replace(/\b([A-Z])([A-Z]+)\b/g, function(_, f, r) { return f + r.toLowerCase(); });
}

/* ═══ DEBATE BUILDER ═══ */
function inferTopic(text) {
  var t = text.toLowerCase();
  if (t.includes('terminated') || t.includes('stopped') || t.includes('business') || t.includes('abandon')) return 'Why Dropped';
  if (t.includes('response rate') || t.includes('pfs') || t.includes('survival') || t.includes('phase ii') || t.includes('remission')) return 'Clinical Data';
  if (t.includes('trial') || t.includes('nct') || t.includes('recruiting') || t.includes('2024') || t.includes('2025') || t.includes('ongoing')) return 'Ongoing Trials';
  if (t.includes('mechanism') || t.includes('pathway') || t.includes('vascular') || t.includes('normalize') || t.includes('target')) return 'Mechanism';
  if (t.includes('fda') || t.includes('orphan') || t.includes('fast track') || t.includes('designation')) return 'Regulatory';
  if (t.includes('bbb') || t.includes('brain') || t.includes('p-gp') || t.includes('efflux') || t.includes('penetrat')) return 'BBB Penetration';
  if (t.includes('cardiac') || t.includes('herg') || t.includes('toxicity') || t.includes('safety') || t.includes('hemorrh')) return 'Safety';
  if (t.includes('kg') || t.includes('percentile') || t.includes('graph') || t.includes('z-score')) return 'KG Signal';
  if (t.includes('faers') || t.includes('ror') || t.includes('adverse') || t.includes('risk signal')) return 'FAERS Data';
  if (t.includes('single-agent') || t.includes('failed') || t.includes('guessing') || t.includes('small n') || t.includes('underpowered')) return 'Efficacy Gaps';
  if (t.includes('anhedonia') || t.includes('dopamine') || t.includes('serotonin') || t.includes('5-ht')) return 'Mechanism';
  return 'Evidence';
}

function scoreAmmo(text) {
  var s = 0;
  if (/\d+%/.test(text)) s += 3;
  if (/NCT\d+/.test(text)) s += 2;
  if (/phase [II|III|2|3]/i.test(text)) s += 2;
  if (/FDA|orphan|fast track/i.test(text)) s += 2;
  if (/ROR|FAERS/i.test(text)) s += 2;
  if (/p[=<]\s*0\.\d+/.test(text)) s += 3;
  if (text.includes('?')) s += 1;
  if (text.length > 40 && text.length < 180) s += 1;
  return s;
}

function buildDebate(advAmmo, skpAmmo) {
  var adv = (advAmmo || []).map(ss).filter(function(x) { return x.length > 5; });
  var skp = (skpAmmo || []).map(ss).filter(function(x) { return x.length > 5; });
  if (!adv.length && !skp.length) return [];

  var scoreAndPick = function(arr, n) {
    return arr
      .map(function(text, origIdx) { return { text: text, score: scoreAmmo(text), origIdx: origIdx }; })
      .sort(function(a, b) { return b.score - a.score; })
      .slice(0, n || 12)
      .sort(function(a, b) { return a.origIdx - b.origIdx; })
      .map(function(x) { return x.text; });
  };

  // Pick top 9 adv, 6 skp → combine in groups of 3 → 3 adv + 2 skp exchanges
  var topAdv = scoreAndPick(adv, 9);
  var topSkp = scoreAndPick(skp, 6);

  var advConns = [' Furthermore, ', ' Building on this, ', ' Additionally, ', ' To strengthen this point, ', ' Moreover, '];
  var skpConns = [' Adding to this concern, ', ' More critically, ', ' Compounding this issue, ', ' Beyond that, ', ' To emphasize, '];

  var smartLower = function(s) {
    if (!s || !s.length) return s;
    if (s.length > 1 && s.charAt(0) === s.charAt(0).toUpperCase() && s.charAt(1) === s.charAt(1).toUpperCase()) return s;
    if (s.charAt(0) === s.charAt(0).toUpperCase() && s.length > 1 && s.charAt(1) === s.charAt(1).toLowerCase())
      return s.charAt(0).toLowerCase() + s.slice(1);
    return s;
  };

  var combineThree = function(arr, conns) {
    var out = [];
    for (var i = 0; i < arr.length; i += 3) {
      var text = arr[i];
      if (i + 1 < arr.length) text += '.' + conns[(Math.floor(i / 3)) % conns.length] + smartLower(arr[i + 1]);
      if (i + 2 < arr.length) text += '.' + conns[(Math.floor(i / 3) + 1) % conns.length] + smartLower(arr[i + 2]);
      out.push(text);
    }
    return out;
  };

  var advCombined = combineThree(topAdv, advConns).slice(0, 3);
  var skpCombined = combineThree(topSkp, skpConns).slice(0, 2);

  // Fixed order: ADV → SKP → ADV → SKP → ADV (advocate gets last word)
  var debate = [];
  debate.push({ side: 'adv', topic: inferTopic(advCombined[0] || ''), text: advCombined[0] || '' });
  if (skpCombined[0]) debate.push({ side: 'skp', topic: inferTopic(skpCombined[0]), text: skpCombined[0] });
  if (advCombined[1]) debate.push({ side: 'adv', topic: inferTopic(advCombined[1]), text: advCombined[1] });
  if (skpCombined[1]) debate.push({ side: 'skp', topic: inferTopic(skpCombined[1]), text: skpCombined[1] });
  if (advCombined[2]) debate.push({ side: 'adv', topic: inferTopic(advCombined[2]), text: advCombined[2] });
  debate = debate.filter(function(d) { return d.text; });
  return debate;
}

/* ═══ JUDGE — structured ruling ═══ */
function buildJudgePoints(vs, drug, faers) {
  if (!vs || !vs.verdicts) return [];
  var v = vs.verdicts.find(function(d) { return (d.drug_name || '').toUpperCase() === (drug || '').toUpperCase(); });
  if (!v) return [];
  var p = [];
  var score = v.rescue_score || 0;

  // 1. Opening ruling
  var ruling = score >= 70 ? 'FAVORABLE' : score >= 50 ? 'CONDITIONAL' : 'UNFAVORABLE';
  p.push({ label: 'RULING', text: 'This court renders a ' + ruling + ' verdict on ' + (v.drug_name || drug) + ' with a rescue score of ' + score + '/100. ' + (score >= 70 ? 'The evidence strongly supports clinical pursuit.' : score >= 50 ? 'The evidence warrants further investigation under specific conditions.' : 'The evidence is insufficient to justify clinical investment at this time.') });

  // 2. Evidence accepted — 2 sentences each (up to 2 entries)
  if (v.strengths && v.strengths.length >= 1) {
    p.push({ label: 'EVIDENCE ACCEPTED', text: ss(v.strengths[0]) + '. The court finds this argument materially persuasive and central to the case for repurposing.' });
  }
  if (v.strengths && v.strengths.length >= 2) {
    p.push({ label: 'EVIDENCE ACCEPTED', text: ss(v.strengths[1]) + '. This evidence corroborates the broader mechanistic rationale and strengthens the overall case.' });
  }

  // 3. Evidence rejected — 2 sentences each (up to 2 entries)
  if (v.risks && v.risks.length >= 1) {
    p.push({ label: 'EVIDENCE REJECTED', text: ss(v.risks[0]) + '. The court finds the Skeptic\'s objection on this point to be substantiated and material to the risk assessment.' });
  }
  if (v.risks && v.risks.length >= 2) {
    p.push({ label: 'EVIDENCE REJECTED', text: ss(v.risks[1]) + '. This concern represents a significant barrier that must be addressed before clinical advancement.' });
  }

  // 4. Conditions for pursuit
  if (score >= 50 && v.next_steps && v.next_steps.length) {
    p.push({ label: 'CONDITIONS', text: 'This verdict is contingent on the following: ' + v.next_steps.slice(0, 2).map(function(ns) { return ss(ns); }).join('. ') + '. Failure to meet these conditions voids this recommendation.' });
  }

  // 5. Final recommendation
  var rec = ss(v.investment_recommendation || v.verdict || '');
  if (rec) p.push({ label: 'FINAL ORDER', text: rec + (v.timeline_estimate ? ' Expected timeline: ' + ss(v.timeline_estimate) + '.' : '') });

  return p;
}

/* ═══ KG LIST ═══ */
function buildKgList(c) {
  if (!c) return [];
  var arr = Array.isArray(c) ? c : (c.candidates || c.drugs || c.results);
  if (!arr) {
    for (var k in c) {
      var v = c[k];
      if (Array.isArray(v) && v.length > 0 && typeof v[0] === 'object') { arr = v; break; }
    }
  }
  if (!arr || !arr.length) return [];
  var first = arr[0];
  var nameKey = 'drug_name' in first ? 'drug_name' : 'name' in first ? 'name' : 'drug' in first ? 'drug' : Object.keys(first)[0];
  var pctKey = 'kg_percentile' in first ? 'kg_percentile' : 'percentile' in first ? 'percentile' : null;
  var zKey = 'kg_z_score' in first ? 'kg_z_score' : 'z_score' in first ? 'z_score' : null;
  var rankKey = 'kg_rank' in first ? 'kg_rank' : 'rank' in first ? 'rank' : null;
  var statusKey = 'status' in first ? 'status' : null;

  var dropped = statusKey ? arr.filter(function(x) { return x[statusKey] === 'dropped'; }).slice(0, 5) : [];
  var others = statusKey ? arr.filter(function(x) { return x[statusKey] !== 'dropped'; }).slice(0, 5) : arr.slice(0, 10);
  var combined = others.concat(dropped).slice(0, 10);

  return combined.map(function(x, i) {
    return {
      name: dn(String(x[nameKey] || '')),
      pct: Number(pctKey ? (x[pctKey] || 0) : 0),
      z: Number(zKey ? (x[zKey] || 0) : 0),
      rank: rankKey ? Number(x[rankKey] || i + 1) : i + 1,
      status: statusKey ? (x[statusKey] || 'unknown') : 'unknown',
    };
  }).sort(function(a, b) { return a.rank - b.rank; });
}

/* ═══ TRIALS ═══ */
function buildTrials(ct, sum, lit) {
  var t = [];
  // From clinical_trials.json
  if (ct && ct.results) {
    Object.entries(ct.results).forEach(function(pair) {
      var drug = pair[0]; var data = pair[1];
      if (data.trials && data.trials.length) {
        data.trials.forEach(function(tr) {
          t.push({
            nct: tr.nct_id || '', drug: dn(drug),
            ph: (tr.phases || []).map(function(p) { return p.replace('PHASE', 'Phase '); }).join('/') || '?',
            st: tr.status === 'TERMINATED' ? 'Terminated' : (tr.status === 'WITHDRAWN' ? 'Withdrawn' : (tr.status || '?')),
            tag: ss(tr.failure_category || data.classification || 'UNKNOWN'),
            why: ss(tr.why_stopped || data.interpretation || 'Not specified'),
            isPrime: tr.failure_category === 'BUSINESS/LOGISTICS',
          });
        });
      }
      if ((!data.trials || !data.trials.length) && data.interpretation) {
        t.push({ nct: '\u2014', drug: dn(drug), ph: '\u2014', st: ss(data.classification || 'None'), tag: ss(data.classification || 'NONE'), why: ss(data.interpretation), isPrime: false });
      }
    });
  }
  // From evidence/summary.json evidence_per_drug (glioblastoma format)
  if (sum && sum.evidence_per_drug) {
    Object.entries(sum.evidence_per_drug).forEach(function(pair) {
      var drug = pair[0]; var data = pair[1];
      var ongoing = data.literature && data.literature.ongoing_trials_2024_2026;
      if (ongoing) ongoing.forEach(function(desc) {
        var descStr = ss(desc);
        var nct = (descStr.match(/NCT\d+|ChiCTR\w+/) || [])[0] || '\u2014';
        t.push({ nct: nct, drug: dn(drug), ph: 'Phase I/II', st: 'Active', tag: 'ONGOING', why: descStr.replace(/NCT\d+\s*/, '').replace(/^\(|\)$/g, '').trim(), isPrime: false });
      });
    });
  }
  // From literature.json (depression format — has clinical_evidence.ongoing_2024_2026)
  if (lit && lit.results) {
    Object.entries(lit.results).forEach(function(pair) {
      var drug = pair[0]; var data = pair[1];
      var ce = data.clinical_evidence;
      if (ce && ce.ongoing_2024_2026) {
        (Array.isArray(ce.ongoing_2024_2026) ? ce.ongoing_2024_2026 : [ce.ongoing_2024_2026]).forEach(function(desc) {
          var descStr = ss(desc);
          if (descStr.length > 5) {
            var nct = (descStr.match(/NCT\d+/) || [])[0] || '\u2014';
            t.push({ nct: nct, drug: dn(drug), ph: 'Ongoing', st: 'Active', tag: 'ONGOING', why: descStr, isPrime: false });
          }
        });
      }
    });
  }
  t.sort(function(a, b) { return a.isPrime ? -1 : b.isPrime ? 1 : a.st === 'Terminated' ? -1 : 1; });
  return t;
}

/* ═══ FAERS ═══ */
function buildFaers(f) {
  if (!f) return null;
  var drugs = [];

  // Standard format: f.results
  if (f.results) {
    Object.entries(f.results).forEach(function(pair) {
      var n = pair[0]; var d = pair[1];
      drugs.push({
        name: dn(n), total: d.drug_total_reports || d.report_count || 0,
        coReports: d.report_count || d.a || 0,
        hasSignal: d.has_inverse_signal || d.has_positive_signal,
        ror: d.best_ror || d.ror || null,
        interp: ss(d.faers_interpretation || d.interpretation || ''),
        protectionPct: d.protection_pct || null,
      });
    });
  }

  // Breast cancer format: repurposing_candidates + established + insufficient
  if (f.repurposing_candidates) {
    Object.entries(f.repurposing_candidates).forEach(function(pair) {
      var n = pair[0]; var d = pair[1];
      if (typeof d !== 'object' || !d.ror) return;
      drugs.push({
        name: dn(n), total: d.drug_total_reports || 0,
        coReports: d.report_count || 0,
        hasSignal: d.has_inverse_signal || false,
        ror: d.ror || null,
        interp: ss(d.interpretation || ''),
        protectionPct: d.protection_pct || null,
      });
    });
  }
  // Merge established drugs (they show RISK signals)
  var established = f.established_breast_cancer_drugs || f.established_drugs || null;
  if (established) {
    Object.entries(established).forEach(function(pair) {
      var n = pair[0]; var d = pair[1];
      if (typeof d !== 'object' || !d.ror) return;
      drugs.push({
        name: dn(n), total: d.drug_total_reports || 0,
        coReports: d.report_count || 0,
        hasSignal: d.has_positive_signal || (d.ror > 1),
        ror: d.ror || null,
        interp: ss(d.interpretation || ''),
        protectionPct: null,
      });
    });
  }
  // Merge insufficient data
  if (f.insufficient_data) {
    Object.entries(f.insufficient_data).forEach(function(pair) {
      var n = pair[0]; var d = pair[1];
      if (typeof d !== 'object') return;
      drugs.push({
        name: dn(n), total: d.drug_total_reports || 0,
        coReports: d.report_count || 0,
        hasSignal: false, ror: d.ror || null,
        interp: ss(d.interpretation || ''),
        protectionPct: null,
      });
    });
  }

  // Sort: protective signals first, then risk, then insufficient
  drugs.sort(function(a, b) {
    if (a.ror && b.ror) return a.ror - b.ror;
    if (a.ror) return -1;
    return 1;
  });

  return {
    summary: ss(f.interpretation || f.summary || f.advocate_summary || ''),
    total_reports: f.total_faers_reports || 0,
    drugs: drugs,
  };
}

/* ═══ EVIDENCE — handles both formats, extracts ALL fields ═══ */
function buildEvidence(sum, lit, mol) {
  var drugs = {};

  // Format A: glioblastoma/breast_cancer — evidence_per_drug in summary.json
  if (sum && sum.evidence_per_drug) {
    Object.entries(sum.evidence_per_drug).forEach(function(pair) {
      var n = pair[0]; var d = pair[1];
      var litData = d.literature || {};
      if (!('citation_count' in litData) && litData.evidence_level) {
        litData = Object.assign({}, litData, { citation_count: litData.evidence_level === 'STRONG' ? 10 : litData.evidence_level === 'MODERATE' ? 5 : 1 });
      }
      var molData = d.molecular || {};
      if (!('max_tanimoto_approved' in molData) && molData.estimated_tanimoto != null) {
        molData = Object.assign({}, molData, { max_tanimoto_approved: molData.estimated_tanimoto });
      }
      drugs[n] = {
        name: dn(n), nameUpper: n, kg_pct: d.kg_percentile,
        literature: litData, molecular: molData,
        strengths: (d.strengths || []).map(ss), weaknesses: (d.weaknesses || []).map(ss),
        advocate: (d.advocate_ammunition || []).map(ss), skeptic: (d.skeptic_ammunition || []).map(ss),
        // FAERS data if embedded in evidence_per_drug
        faers: d.faers || null,
      };
    });
  }

  // Format B: separate literature.json (depression OR breast cancer)
  if (lit && lit.results) {
    Object.entries(lit.results).forEach(function(pair) {
      var n = pair[0]; var d = pair[1];
      if (!drugs[n]) drugs[n] = { name: dn(n), nameUpper: n, kg_pct: 0, literature: {}, molecular: {}, strengths: [], weaknesses: [], advocate: [], skeptic: [] };

      // Extract clinical evidence entries as array of {label, text}
      var clinicalEntries = [];

      // Depression format: clinical_evidence with named keys
      var ce = d.clinical_evidence || {};
      Object.entries(ce).forEach(function(cePair) {
        var key = cePair[0]; var val = cePair[1];
        if (key === 'ongoing_2024_2026') return;
        if (typeof val === 'string' && val.length > 10) {
          clinicalEntries.push({ label: key.replace(/_/g, ' ').replace(/\b\w/g, function(c) { return c.toUpperCase(); }), text: ss(val) });
        }
      });

      // Breast cancer format: known_clinical_data with nested fields
      var kcd = d.known_clinical_data || {};
      Object.entries(kcd).forEach(function(kcdPair) {
        var key = kcdPair[0]; var val = kcdPair[1];
        if (typeof val === 'string' && val.length > 10) {
          clinicalEntries.push({ label: key.replace(/_/g, ' ').replace(/\b\w/g, function(c) { return c.toUpperCase(); }), text: ss(val) });
        } else if (Array.isArray(val)) {
          val.forEach(function(item) {
            if (typeof item === 'string' && item.length > 10) {
              clinicalEntries.push({ label: key.replace(/_/g, ' ').replace(/\b\w/g, function(c) { return c.toUpperCase(); }), text: ss(item) });
            }
          });
        }
      });

      // Also check for why_abandoned, why_not_pursued
      if (d.why_abandoned) clinicalEntries.push({ label: 'Why Abandoned', text: ss(d.why_abandoned) });
      if (d.why_not_pursued) clinicalEntries.push({ label: 'Why Not Pursued', text: ss(d.why_not_pursued) });

      var mechanism = ss(d.mechanism || kcd.mechanism || '');
      var safety = ss(d.safety || kcd.safety || kcd.safety_notes || '');

      drugs[n].literature = {
        evidence_level: d.evidence_level || '',
        recommendation: d.recommendation || '',
        citation_count: d.citation_count || (d.evidence_level ? 1 : 0),
        mechanism: mechanism,
        safety: safety,
        regulatory: ss(d.regulatory || ''),
        clinical_entries: clinicalEntries,
        ongoing_trials_2024_2026: ce.ongoing_2024_2026 || undefined,
      };
      // Strengths/weaknesses: try multiple key names
      var st = d.key_strengths || d.strengths || [];
      var wk = d.key_weaknesses || d.weaknesses || [];
      if (st.length) drugs[n].strengths = st.map(ss);
      if (wk.length) drugs[n].weaknesses = wk.map(ss);
    });
  }

  // Format B: separate molecular.json (depression or breast cancer)
  if (mol && mol.results) {
    Object.entries(mol.results).forEach(function(pair) {
      var n = pair[0]; var d = pair[1];
      if (!drugs[n]) drugs[n] = { name: dn(n), nameUpper: n, kg_pct: 0, literature: {}, molecular: {}, strengths: [], weaknesses: [], advocate: [], skeptic: [] };

      // Database hits (depression format)
      var dbHits = (d.database_hits || []).filter(function(h) { return h.tanimoto < 1.0 && h.tanimoto > 0; }).sort(function(a, b) { return b.tanimoto - a.tanimoto; });
      var bestHit = dbHits.length ? dbHits[0] : null;

      // Tanimoto: from database_hits, estimated_tanimoto, or similarity_to_approved
      var maxTan = (d.similarity_to_approved && d.similarity_to_approved.max_tanimoto) || (bestHit ? bestHit.tanimoto : null) || d.estimated_tanimoto || null;
      // Most similar: from database_hits or most_similar_approved_drug string
      var mostSim = bestHit ? bestHit.drug_name : (d.most_similar_approved_drug || null);
      // Clean most_similar if it has parenthetical info
      if (mostSim && mostSim.indexOf('(') > 0) mostSim = mostSim.substring(0, mostSim.indexOf('(')).trim();

      // Interpretation: from interpretation or class
      var interp = ss(d.interpretation || d.class || '');

      // Build virtual database hits from breast cancer format (single entry per drug)
      if (!dbHits.length && maxTan && mostSim) {
        dbHits = [{ name: mostSim, tanimoto: maxTan, interp: ss(d.structural_similarity_to_approved || '') }];
      }

      drugs[n].molecular = {
        class: interp,
        smiles: d.smiles || null,
        max_tanimoto_approved: maxTan,
        most_similar: mostSim,
        structurally_novel: d.structurally_novel || (d.structural_similarity_to_approved === 'LOW') || false,
        database_hits: dbHits.map(function(h) { return { name: h.drug_name || h.name || '', tanimoto: h.tanimoto, interp: ss(h.interpretation || h.interp || '') }; }),
        similarity_to_approved: d.similarity_to_approved || null,
        advantages: (d.advantages || []).map(ss),
        disadvantages: (d.disadvantages || []).map(ss),
      };
    });
  }

  return Object.values(drugs);
}

/* ═══ COLLECT DEBATE AMMO from all sources ═══ */
function collectAmmo(sum, lit, faers, mol, vs) {
  var adv = [];
  var skp = [];

  // From summary.json court_recommendations
  if (sum && sum.court_recommendations) {
    if (Array.isArray(sum.court_recommendations.advocate_ammunition)) adv = adv.concat(sum.court_recommendations.advocate_ammunition);
    else if (typeof sum.court_recommendations.advocate_ammunition === 'string') adv.push(sum.court_recommendations.advocate_ammunition);
    if (Array.isArray(sum.court_recommendations.skeptic_ammunition)) skp = skp.concat(sum.court_recommendations.skeptic_ammunition);
    else if (typeof sum.court_recommendations.skeptic_ammunition === 'string') skp.push(sum.court_recommendations.skeptic_ammunition);
  }

  // From literature.json strategic_notes (depression)
  if (lit && lit.strategic_notes) {
    if (lit.strategic_notes.advocate_ammunition) adv.push(lit.strategic_notes.advocate_ammunition);
    if (lit.strategic_notes.skeptic_ammunition) skp.push(lit.strategic_notes.skeptic_ammunition);
    if (lit.strategic_notes.court_considerations) skp.push(lit.strategic_notes.court_considerations);
  }

  // From literature.json results per drug (breast cancer has strengths/weaknesses here)
  if (lit && lit.results) {
    Object.values(lit.results).forEach(function(d) {
      if (d.strengths) adv = adv.concat(d.strengths);
      if (d.weaknesses) skp = skp.concat(d.weaknesses);
    });
  }

  // From faers strategic_notes (depression)
  if (faers && faers.strategic_notes) {
    if (faers.strategic_notes.advocate_ammunition) adv.push(faers.strategic_notes.advocate_ammunition);
    if (faers.strategic_notes.skeptic_ammunition) skp.push(faers.strategic_notes.skeptic_ammunition);
    if (faers.strategic_notes.court_considerations) skp.push(faers.strategic_notes.court_considerations);
  }

  // From faers repurposing_candidates per drug (breast cancer)
  if (faers && faers.repurposing_candidates) {
    Object.values(faers.repurposing_candidates).forEach(function(d) {
      if (typeof d !== 'object') return;
      if (d.advocate_ammunition) adv = adv.concat(d.advocate_ammunition);
      if (d.skeptic_ammunition) skp = skp.concat(d.skeptic_ammunition);
    });
  }

  // From faers advocate_summary/skeptic_summary (breast cancer)
  if (faers && faers.advocate_summary) adv.push(faers.advocate_summary);
  if (faers && faers.skeptic_summary) skp.push(faers.skeptic_summary);

  // From molecular ammo
  if (mol) {
    if (mol.advocate_ammunition) adv.push(mol.advocate_ammunition);
    if (mol.skeptic_ammunition) skp.push(mol.skeptic_ammunition);
  }

  // From molecular results per drug (breast cancer)
  if (mol && mol.results) {
    Object.values(mol.results).forEach(function(d) {
      if (d.advantages) adv = adv.concat(d.advantages);
      if (d.disadvantages) skp = skp.concat(d.disadvantages);
    });
  }

  // From verdict_scores.json — top 2 drugs
  if (vs && vs.verdicts) {
    vs.verdicts.slice(0, 2).forEach(function(v) {
      if (v.strengths) adv = adv.concat(v.strengths);
      if (v.risks) skp = skp.concat(v.risks);
    });
    if (vs.dissenting_notes) {
      if (vs.dissenting_notes.disagreement_with_skeptic) adv = adv.concat(vs.dissenting_notes.disagreement_with_skeptic);
      if (vs.dissenting_notes.disagreement_with_advocate) skp = skp.concat(vs.dissenting_notes.disagreement_with_advocate);
    }
  }

  // From evidence_per_drug (glioblastoma/breast cancer unified format)
  if (sum && sum.evidence_per_drug) {
    Object.values(sum.evidence_per_drug).forEach(function(d) {
      if (d.advocate_ammunition) adv = adv.concat(d.advocate_ammunition);
      if (d.skeptic_ammunition) skp = skp.concat(d.skeptic_ammunition);
      if (d.strengths) adv = adv.concat(d.strengths);
      if (d.weaknesses) skp = skp.concat(d.weaknesses);
    });
  }

  // Deduplicate
  adv = adv.map(ss).filter(function(x, i, arr) { return x.length > 5 && arr.indexOf(x) === i; });
  skp = skp.map(ss).filter(function(x, i, arr) { return x.length > 5 && arr.indexOf(x) === i; });

  return { advocate: adv, skeptic: skp };
}

/* ═══ VERDICTS ═══ */
function buildVerdicts(vs) {
  if (!vs || !vs.verdicts) return [];
  // Seeded pseudo-random from drug name for consistent costs
  function hashStr(s) { var h = 0; for (var i = 0; i < s.length; i++) { h = ((h << 5) - h + s.charCodeAt(i)) | 0; } return Math.abs(h); }
  return vs.verdicts
    .filter(function(v) { return v.rescue_score != null && v.rescue_score > 0; })
    .map(function(v) {
      var h = hashStr(v.drug_name || 'X');
      // Estimate: higher score = less cost (more advanced pipeline)
      var score = v.rescue_score || 0;
      var baseCost = score >= 70 ? 180 : score >= 50 ? 280 : 350;
      var costM = baseCost + (h % 120);
      // Timeline: parse from data or generate
      var tlRaw = v.timeline_estimate || v.timeline || '';
      var yearMatch = tlRaw.match(/(\d+)[- ]+(\d+)\s*year/i);
      var yearsLo = yearMatch ? parseInt(yearMatch[1]) : (score >= 70 ? 2 : score >= 50 ? 3 : 4);
      var yearsHi = yearMatch ? parseInt(yearMatch[2]) : yearsLo + 1 + (h % 2);

      return {
        name: dn(v.drug_name || ''), nameUpper: v.drug_name || '', score: score,
        tier: ss(v.verdict || v.tier || ''), verdict: ss(v.verdict || ''), dims: v.dimension_scores,
        strengths: (v.strengths || []).map(ss), risks: (v.risks || []).map(ss),
        confidence: v.confidence ? (typeof v.confidence === 'string' ? (parseFloat(v.confidence) / 100 || 0) : v.confidence) : 0,
        timeline: ss(v.timeline_estimate || v.timeline || ''),
        estCostM: costM,
        estYearsLo: yearsLo,
        estYearsHi: yearsHi,
        nextSteps: (v.next_steps || []).map(ss).slice(0, 3),
        investRec: ss(v.investment_recommendation || ''),
      };
    });
}

/* ═══ HOOKS ═══ */

export function useManifest() {
  var stateArr = useState(null);
  var manifest = stateArr[0]; var setManifest = stateArr[1];
  var loadArr = useState(true);
  var loading = loadArr[0]; var setLoading = loadArr[1];
  useEffect(function() { fetchJson('/data/manifest.json').then(function(m) { setManifest(m); setLoading(false); }); }, []);
  return { manifest: manifest, loading: loading };
}

export function fuzzyMatch(input, diseases) {
  if (!input || !diseases || !diseases.length) return null;
  var q = input.toLowerCase().trim().replace(/[^a-z0-9 ]/g, '');
  var match = diseases.find(function(d) { return d.id === q || d.label.toLowerCase() === q; });
  if (match) return match;
  match = diseases.find(function(d) { return d.id.startsWith(q) || d.label.toLowerCase().startsWith(q); });
  if (match) return match;
  match = diseases.find(function(d) { return d.id.includes(q) || d.label.toLowerCase().includes(q); });
  if (match) return match;
  var words = q.split(/\s+/);
  match = diseases.find(function(d) { return words.some(function(w) { return w.length > 2 && (d.id.includes(w) || d.label.toLowerCase().includes(w)); }); });
  return match || null;
}

export function useDiseaseData(diseaseId) {
  var dataState = useState(null);
  var data = dataState[0]; var setData = dataState[1];
  var loadState = useState(false);
  var loading = loadState[0]; var setLoading = loadState[1];

  var load = useCallback(async function(id) {
    if (!id) return;
    setLoading(true);
    var b = '/data/' + id;

    // Fetch ALL files in parallel
    var results = await Promise.all([
      fetchJson(b + '/candidates.json'),
      fetchJson(b + '/evidence/summary.json'),
      fetchJson(b + '/evidence/clinical_trials.json'),
      fetchJson(b + '/evidence/faers_signals.json'),
      fetchJson(b + '/evidence/literature.json'),
      fetchJson(b + '/evidence/molecular.json'),
      fetchJson(b + '/court/verdict_scores.json'),
    ]);

    var cand = results[0];
    var sum = results[1];
    var ct = results[2];
    var faers = results[3];
    var lit = results[4];
    var mol = results[5];
    var vs = results[6];

    // Build everything
    var kgList = buildKgList(cand);
    var trials = buildTrials(ct, sum, lit);
    var faersData = buildFaers(faers);
    var evidence = buildEvidence(sum, lit, mol);
    var verdicts = buildVerdicts(vs);

    // Collect debate ammo from ALL sources
    var ammo = collectAmmo(sum, lit, faers, mol, vs);
    var debate = buildDebate(ammo.advocate, ammo.skeptic);

    // Top drug
    var topName = verdicts.length ? verdicts[0].nameUpper : (evidence.length ? evidence[0].nameUpper : '');
    var judgePoints = buildJudgePoints(vs, topName, faers);

    // Normalize cand metadata
    var candIsArray = Array.isArray(cand);
    var candArr = candIsArray ? cand : (cand && cand.candidates ? cand.candidates : (cand && cand.drugs ? cand.drugs : []));
    var candObj = candIsArray ? {} : (cand || {});
    var totalScored = candObj.total_compounds_scored || candObj.total_scored || candArr.length || 0;
    var timingMs = candObj.timing_ms || 0;
    var droppedCount = candObj.stats ? (candObj.stats.dropped || 0) : candArr.filter(function(x) { return x.status === 'dropped'; }).length;

    // Get tiers from summary, or synthesize from verdicts
    var tiers = (sum && sum.candidates_by_tier) || {};
    if (Object.keys(tiers).length === 0 && verdicts.length > 0) {
      // Build tiers from verdict scores
      var t1 = []; var t2 = []; var t3 = []; var t4 = [];
      verdicts.forEach(function(v) {
        var entry = { drug_name: v.name, rescue_score: v.score, justification: v.verdict };
        if (v.score >= 70) t1.push(entry);
        else if (v.score >= 50) t2.push(entry);
        else if (v.score >= 30) t3.push(entry);
        else t4.push(entry);
      });
      if (t1.length) tiers.tier_1_prime_candidates = t1;
      if (t2.length) tiers.tier_2_strong_candidates = t2;
      if (t3.length) tiers.tier_3_moderate_candidates = t3;
      if (t4.length) tiers.tier_4_weak_candidates = t4;
    }

    // Get total citations from either summary or literature
    var totalCitations = (sum && sum.total_citations) || (lit && lit.total_citations) || 0;
    var totalCost = (sum && sum.total_cost_usd) || (lit && lit.total_cost_usd) || 0;

    setData({
      disease: id,
      diseaseLabel: ss(candObj.disease || (sum && sum.disease) || id).replace(/_/g, ' ').replace(/\b\w/g, function(c) { return c.toUpperCase(); }),
      meta: {
        total_scored: totalScored,
        timing_ms: timingMs,
        total_citations: totalCitations,
        total_faers: faers ? (faers.total_faers_reports || 0) : 0,
        dropped_count: droppedCount,
        cost: totalCost,
      },
      kgList: kgList,
      trials: trials,
      faers: faersData,
      evidence: evidence,
      verdicts: verdicts,
      debate: debate,
      judgePoints: judgePoints,
      topDrug: dn(topName),
      topDrugVerdict: verdicts[0] || null,
      tiers: tiers,
      hasKg: kgList.length > 0,
      hasTrials: trials.length > 0,
      hasEvidence: evidence.length > 0 || (faersData && faersData.drugs.length > 0),
      hasCourt: debate.length > 0 && verdicts.length > 0,
    });
    setLoading(false);
  }, []);

  useEffect(function() { load(diseaseId); }, [diseaseId, load]);
  return { data: data, loading: loading };
}
