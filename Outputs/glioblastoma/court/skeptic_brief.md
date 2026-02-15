# Skeptic Brief: Drug Repurposing for Glioblastoma

## Opening Statement

Glioblastoma patients deserve more than computational promises and preclinical hope. The blood-brain barrier stands as an impenetrable fortress that has defeated countless drug candidates. Every year, dozens of repurposing proposals emerge from knowledge graphs and mouse models, yet median survival remains stubbornly fixed at 15 months. Before we invest millions and risk patient lives, we must demand extraordinary evidence—not graph topology scores, not underpowered Phase II trials, and certainly not corporate "business decisions" that conveniently mask underlying failures.

---

## Candidate 1: CEDIRANIB
**Risk Assessment: MODERATE-HIGH**

### Why This Drug Was Really Dropped

The narrative claims AstraZeneca abandoned cediranib due to "business decision" and "corporate portfolio restructuring." Let me translate: a pharmaceutical giant with billions invested in a Phase III asset doesn't walk away unless the numbers don't work.

**The inconvenient truth:**
- AstraZeneca stopped ALL cediranib development globally—not just GBM, but ovarian cancer, colorectal cancer, and every other indication
- If Phase II data in GBM were truly promising (27-57% response rate claimed), why didn't they out-license it? Why didn't academic centers continue trials?
- Companies don't abandon drugs worth developing—they sell them, partner them, or spin them out
- **Most likely reality:** The Phase III trials in other indications failed, and the GBM program died as collateral damage

### Safety Concerns

**FAERS Risk Signals** (Severity: 6/10)
- 119 total adverse event reports (more than any other candidate)
- Only 1 co-report with glioblastoma, but insufficient power doesn't mean safe—it means we're blind
- Literature notes: **weak-moderate hERG inhibition** = cardiac arrhythmia risk requiring continuous EKG monitoring
- **High CYP inhibition** = dangerous drug-drug interactions with anticonvulsants (phenytoin, carbamazepine) that GBM patients commonly take

**Known Side Effects in Target Population**
- Glioblastoma patients are often elderly (median age 64), on polypharmacy, with compromised cardiovascular reserve
- Cerebral edema is claimed as a benefit, but VEGF inhibition can also cause **microhemorrhages, posterior reversible encephalopathy syndrome (PRES), and thrombotic events**
- Hypertension, diarrhea, fatigue—all manageable in healthy populations, potentially life-threatening in frail brain tumor patients

**Drug Interactions**
- **P-glycoprotein (P-gp) efflux substrate** = most drug pumped OUT of brain before reaching tumor
- This isn't a minor concern—it's a fundamental flaw for a brain tumor drug
- Standard anticonvulsants induce P-gp further, creating a pharmacokinetic death spiral

### Evidence Weaknesses

**KG Score Limitations** (Reliability: 30%)
- KG rank 25/30 with score -11.8879 sounds impressive until you realize it's measuring **graph distance, not clinical efficacy**
- The knowledge graph connects "treatment" relations, which include failed trials, preclinical studies, and speculative hypotheses
- Z-score 5.436 means this drug is a "statistical outlier"—but so are many failed drugs
- **Critical flaw:** The KG cannot distinguish between "studied extensively and failed" vs. "studied and succeeded"

**FAERS Inverse Signal Caveats** (Reliability: 0%)
- NO inverse signal detected (ROR = null, insufficient data)
- The advocate will claim "no adverse signals" is good news
- **Reality:** With only 1 co-report, we have zero visibility into real-world safety
- Glioblastoma's rarity (1,574 reports in 20M+ database) makes FAERS completely uninformative

**Literature Gaps** (Reliability: 45%)
- The "27-57% response rate" comes from **small Phase II studies without control arms**
- Response rate ≠ survival benefit
- **6-month PFS of 26%** is barely better than historical controls (20-25%)
- "Long-term remission case reports (>5 years)" = cherry-picked anecdotes, not systematic evidence
- The ongoing 2024-2026 trials cited are **Phase I/II with n<50 patients**—not definitive

**Molecular Analysis Caveats** (Reliability: 20%)
- Tanimoto similarity 0.0833 to temozolomide (the standard) = essentially unrelated structures
- "Moderate similarity to veonetinib/catequentinib" means similarity to other FAILED TKIs
- **P-gp efflux is mentioned but not quantified**—likely >90% of drug excluded from brain
- No docking data (NVIDIA API unavailable) = we're guessing about target engagement

### Missing Evidence

**What I would need to see before recommending this drug:**
1. **Pharmacokinetic study** measuring actual brain tissue concentrations in GBM patients (not just plasma levels)
2. **Phase III randomized controlled trial** with OS as primary endpoint—response rates and PFS6 are surrogate endpoints that don't predict survival
3. **Cardiac safety study** in elderly patients with pre-existing cardiovascular disease
4. **Explanation** for why AstraZeneca abandoned it if data were compelling
5. **Biomarker analysis** showing which patients might benefit—not all GBMs are VEGF-driven

### Bottom Line

If a multi-billion dollar pharmaceutical company walked away from a Phase III asset in multiple indications, we should demand extraordinary evidence before resurrecting it. P-gp efflux alone may doom this drug—you can't treat a brain tumor with a drug that can't enter the brain.

---

## Candidate 2: PERIFOSINE
**Risk Assessment: HIGH**

### Why This Drug Was Really Dropped

Perifosine has been in clinical development since the 1990s. Let that sink in—**30+ years and no approval**. The literature claims it's in "Phase III planning" for GBM, but Phase III planning is not Phase III success.

**The damning evidence:**
- **0/12 single-agent responses** in Phase I/II GBM trial (NCT01051557)
- That's not "minimal activity"—that's **zero activity**
- Only shows effects in combinations, suggesting it's not hitting the intended target
- If Akt inhibition worked for GBM, why did ipatasertib, capivasertib, and uprosertib all fail in brain tumors?

### Safety Concerns

**FAERS Risk Signals** (Severity: 5/10)
- 29 total reports, 1 GBM co-report (insufficient data for signal detection)
- Literature buries the critical finding: **preclinical intracranial hemorrhages** in mouse models
- In elderly GBM patients on anticoagulants (DVT prophylaxis), this could be catastrophic

**Known Side Effects in Target Population**
- **GI toxicity is dose-limiting**: nausea, vomiting, diarrhea in >50% of patients
- Can't give effective doses due to tolerability—this is why it failed in other cancers
- "Poor tolerability in pediatric combinations" suggests toxicity worse than advertised
- Hemorrhage risk in brain tumor patients is unacceptable

**Drug Interactions**
- Alkylphospholipid class affects membrane function broadly—unpredictable interactions with other lipophilic drugs
- May interfere with corticosteroids (standard GBM supportive care)
- No systematic drug-drug interaction studies in GBM population

### Evidence Weaknesses

**KG Score Limitations** (Reliability: 25%)
- KG rank 30/30, score -11.9366, Z-score 5.334
- Dead last in the candidate list—the advocate will spin this as "high score," but it's literally the 30th choice
- Knowledge graph cannot capture "tried for 30 years and failed everywhere"

**FAERS Inverse Signal Caveats** (Reliability: 0%)
- No signal detected (ROR = null)
- With only 29 total reports, this drug has barely been used clinically
- **Absence of data is not evidence of safety**

**Literature Gaps** (Reliability: 35%)
- The "75% PFS6 in 2024-2026 trials" comes from **ongoing, uncontrolled Phase II studies**
- Historical control comparisons are notoriously unreliable (selection bias, lead-time bias, stage migration)
- "FDA Fast Track granted May 2024" ≠ FDA believes it works—just that there's unmet need
- **Critical omission:** The literature doesn't explain WHY single-agent activity is zero
- "Phase III planning" has been mentioned for years—still waiting

**Molecular Analysis Caveats** (Reliability: 15%)
- Tanimoto similarity 0.0833 to lomustine = structurally unrelated to anything that works
- Long aliphatic chain suggests membrane incorporation, but we don't know if it reaches brain membranes
- No docking data = we're guessing about Akt PH domain binding
- Similarity to oleylphosphocholine and edelfosine (both failed drugs) is not encouraging

### Missing Evidence

**What I would need to see:**
1. **Explanation** for why single-agent activity is zero—is this even hitting Akt in tumors?
2. **Hemorrhage incidence data** from human trials—preclinical findings demand urgent investigation
3. **Phase III data**—not "planning," actual results with statistical power
4. **Dose-finding study** showing therapeutic doses are tolerable in GBM patients
5. **Mechanism validation**: prove Akt phosphorylation is actually inhibited in resected tumor tissue post-treatment

### Bottom Line

Zero single-agent activity in 12 patients is not "minimal"—it's a failed drug. The only response seen is in combinations, suggesting perifosine may be an expensive placebo that adds toxicity while other agents do the work. Preclinical brain hemorrhages should halt development until human safety is proven.

---

## Candidate 3: TALAMPANEL
**Risk Assessment: MODERATE**

### Why This Drug Was Really Dropped

The Phase II trial (NCT00062504) was "TERMINATED" with reason "Not specified." In clinical research, when a trial stops without explanation, it's usually bad news.

**Plausible scenarios:**
1. **Efficacy failure** (most likely)—the trial hit futility boundary on interim analysis
2. **Safety signal** they don't want to publicize
3. **Recruitment failure** due to lack of investigator enthusiasm (itself a red flag)

The literature admits: **"Phase 2 recurrent GBM trial: Single agent, well-tolerated, no significant antitumor activity, trial stopped for futility."** This is the real story buried in the citation count.

### Safety Concerns

**FAERS Risk Signals** (Severity: UNKNOWN/10)
- **Zero FAERS reports**—this drug has essentially never been used clinically
- Cannot assess real-world safety
- "Mild dizziness and ataxia" may be "manageable" in trial patients but intolerable in daily life
- "No discontinuations for toxicity" in tiny Phase II ≠ safe in general population

**Known Side Effects in Target Population**
- AMPA receptor antagonism affects normal brain glutamate signaling—not just tumor cells
- Cognitive effects (dizziness, ataxia, confusion) in patients already suffering from tumor-related deficits
- Seizure control benefit is theoretical—no systematic epilepsy endpoint data
- Drug penetrates BBB (good for efficacy, bad for CNS toxicity)

**Drug Interactions**
- No published interaction studies with anticonvulsants
- AMPA antagonism may interact with other neuromodulatory drugs
- Unknown interaction with steroids (affect glutamate transmission)

### Evidence Weaknesses

**KG Score Limitations** (Reliability: 35%)
- KG rank 11/30, score -11.7475, Z-score 5.729
- Higher rank than cediranib, yet explicitly failed Phase II in recurrent GBM
- Proves KG scores don't predict clinical success

**FAERS Inverse Signal Caveats** (Reliability: 0%)
- Zero reports = zero information
- This is the most data-sparse candidate

**Literature Gaps** (Reliability: 40%)
- The "good" Phase II data cited: **mOS 15.8 months vs 15.0 historical** = 0.8 month benefit
- That's statistically and clinically meaningless
- "75% PFS6 in 2024-2026 trials" from **NCT06345622 with no published results yet**—this is a FUTURE trial, not evidence
- "Dual benefit: antitumor + seizure control" is speculative—no RCT comparing seizure rates
- Only 20 citations (lowest of top candidates)—limited scientific interest

**Molecular Analysis Caveats** (Reliability: 10%)
- Only 1 database hit (itself)—completely unique scaffold
- Unique = unpredictable PK, toxicity, drug interactions
- No structural precedent for success
- Tanimoto 0.1286 to temozolomide = unrelated to anything that works
- No docking data = guessing about AMPA receptor binding pose

### Missing Evidence

**What I would need to see:**
1. **Why was NCT00062504 terminated?**—get the real reason from ClinicalTrials.gov
2. **Seizure endpoint data** from controlled trials—prove the "dual benefit" claim
3. **Cognitive function testing** pre/post treatment—AMPA antagonism likely impairs memory
4. **Phase III data** in newly diagnosed GBM with OS as endpoint
5. **Target engagement study**—measure AMPA receptor occupancy in human brain tissue

### Bottom Line

A drug that explicitly failed Phase II in recurrent GBM (stopped for futility) should not be a top-3 candidate. The 0.8 month survival benefit in newly diagnosed patients is noise, not signal. Unique scaffold means unpredictable behavior—could be brilliant or catastrophic, and we have no precedent to judge.

---

## Candidate 4: RIVOCERANIB
**Risk Assessment: VERY HIGH**

### Why This Drug Doesn't Belong Here

This candidate has **ZERO glioblastoma trials** (NCT search returned nothing). The literature mentions a vague "45% ORR in 20 patients" with no trial registration number, no publication, no details. This is not evidence—it's hearsay.

### Safety Concerns

**FAERS Risk Signals** (Severity: 7/10)
- 94 total reports (more than perifosine), 0 GBM reports
- Literature reports **42.5% hypertension** in Phase II adenoid cystic carcinoma
- That's an unacceptably high rate for GBM patients already at risk for intracranial hemorrhage
- VEGFR2 inhibition class effects: bleeding, thrombosis, GI perforation, proteinuria

**Known Side Effects in Target Population**
- Severe hypertension in brain tumor patients = stroke risk
- No BBB penetration data = likely excluded from brain
- Oral formulation sounds convenient, but if drug doesn't reach brain, convenience is moot

### Evidence Weaknesses

**All Evidence Metrics** (Reliability: <5%)
- NO GBM TRIALS = this entire candidacy is speculative
- KG score is meaningless—just reflects that VEGF and GBM are mentioned in same papers
- Literature "STRONG" recommendation is a joke—based on mechanism, not data
- One unverifiable claim of 20 patients with no citation

### Missing Evidence

**Everything.** This drug should not be in the top 5 without a single GBM trial.

### Bottom Line

Including rivoceranib in this analysis is malpractice. Zero trials = zero evidence = zero reason to risk patient lives. The 42.5% hypertension rate would cause more strokes than the drug prevents deaths.

---

## Closing Argument

The standard of evidence for drug repurposing must be HIGH, not low. Glioblastoma patients are desperate, but desperation is not a reason to lower our standards—it's a reason to raise them. Every failed trial, every adverse event, every month of delayed access to effective supportive care represents a life cut short.

**The hard truths:**
- **Knowledge graph scores measure popularity, not efficacy.** Drugs can be "close" to disease nodes because they've been extensively studied and failed.
- **FAERS is useless for rare diseases.** The absence of signals tells us nothing.
- **Preclinical models lie.** 83% survival increase in mice (edotecarin) meant nothing in Phase III humans.
- **Phase II response rates are mirages.** They don't predict survival, and uncontrolled historical comparisons are junk science.
- **"Business decisions" are euphemisms.** Pharmaceutical companies don't abandon profitable drugs.

**The translation gap is real:**
- >90% of preclinical findings fail to translate to humans
- ~95% of repurposing candidates fail in Phase III
- Blood-brain barrier defeats most small molecules
- Glioblastoma's molecular heterogeneity means "one-size-fits-all" approaches fail

**What we're really being asked to do:**
Invest millions of dollars and years of patient lives into candidates with:
- Zero single-agent activity (perifosine)
- P-gp efflux excluding them from the target organ (cediranib)
- Explicit Phase II futility stops (talampanel)
- Zero clinical trials in the disease (rivoceranib)
- Phase III efficacy failures (edotecarin—not even discussed here, but in the evidence)

**I'm not opposed to drug repurposing.** I'm opposed to premature investment in underpowered candidates that will waste resources and patient lives. Before recommending any of these drugs, I need:

1. **Phase III randomized controlled trials** with overall survival as the primary endpoint
2. **Pharmacokinetic studies** proving brain penetration at therapeutic concentrations
3. **Biomarker-driven patient selection** to identify who might benefit
4. **Clear mechanistic validation** showing target engagement in human tumor tissue
5. **Honest safety data** including worst-case scenarios, not just "manageable toxicity"

Extraordinary claims require extraordinary evidence. Glioblastoma patients deserve better than graph topology, mouse models, and corporate castoffs. Show me the Phase III data, or don't ask me to recommend these drugs.

**Respectfully submitted,**

The Skeptic
DrugRescue Evidence Court
