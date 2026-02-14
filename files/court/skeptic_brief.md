# Skeptic Brief: Drug Repurposing for Glioblastoma

## Opening Statement

Glioblastoma is the graveyard of promising therapies. The blood-brain barrier, tumor heterogeneity, and aggressive biology have defeated countless drugs that looked good on paper. The candidates before this court have high knowledge graph scores - but graph topology is not clinical efficacy. We must demand extraordinary evidence before exposing desperate patients to drugs that have already been abandoned by their developers. The history of repurposing is littered with false hope; our duty is to protect patients from premature investment in drugs that are likely to fail again.

---

## Candidate 1: CEDIRANIB
**Risk Assessment: MODERATE-HIGH**

### Why This Drug Was Really Dropped

The advocate will claim "business decision" as if AstraZeneca casually abandoned a billion-dollar asset. Let's be clear: pharmaceutical companies don't walk away from drugs in Phase 2-3 without serious reasons. AstraZeneca stopped ALL cediranib development globally - across ALL indications. This wasn't a GBM-specific pivot; this was complete program termination.

**The reality**: By 2013, cediranib had failed multiple Phase 3 trials in ovarian cancer, lung cancer, and other solid tumors. The ICON6 trial showed minimal benefit. The company made a portfolio decision BECAUSE the drug wasn't performing commercially. If it had shown transformative efficacy in GBM, AstraZeneca would have continued - brain tumor therapeutics command premium pricing and orphan drug status.

### Safety Concerns

**FAERS Risk Signals** (Severity: 6/10)
- 119 total FAERS reports with only 1 GBM co-report - this means the drug HAS been used, but GBM patients aren't reporting extensively (concerning for tolerability or rapid disease progression)
- Literature notes: **hERG inhibition (cardiac risk)** - requires ECG monitoring, QTc prolongation can be fatal
- **P-glycoprotein efflux substrate** - the drug gets PUMPED OUT of the brain, exactly where you need it
- Hypertension, proteinuria, and hemorrhage are VEGFR inhibitor class effects

**Known Side Effects in Target Population**
GBM patients are elderly (median age 64), often on corticosteroids, anticonvulsants, and warfarin. They are uniquely vulnerable to:
- **Intracranial hemorrhage**: VEGFR inhibition disrupts vascular integrity in an already fragile tumor environment
- **Cardiac toxicity**: Many GBM patients have cardiovascular comorbidities; hERG inhibition adds unacceptable risk
- **Cerebral edema management complications**: While vascular normalization sounds good, unpredictable edema fluctuations can be fatal

**Drug Interactions**
- High CYP3A4 inhibition (literature) - interacts with dexamethasone, phenytoin, and other standard GBM medications
- Increased bleeding risk with bevacizumab (already FDA-approved for GBM) - if bevacizumab is available, why use an unproven alternative?

### Evidence Weaknesses

**KG Score Limitations** (Reliability: 30%)
- Score -11.8879 (rank 25/24,313) is based on GNBR::T::Compound:Disease relation - a TEXT-MINED association from literature
- This means papers mention cediranib AND glioblastoma together - NOT that clinical trials proved efficacy
- Graph distance captures "popularity bias" - well-studied drugs + common disease = high score, regardless of actual therapeutic value
- The KG cannot distinguish between "studied and failed" vs "studied and succeeded"

**FAERS Inverse Signal Caveats** (Reliability: 0%)
- NO inverse signal detected (no protective effect observed)
- 1 co-report out of 119 total = insufficient data, but also suggests limited real-world GBM use
- "Healthy user bias" explanation doesn't apply here - there's no signal at all
- The advocate will claim "insufficient data isn't negative data" - true, but it's also NOT positive data

**Literature Gaps** (Reliability: 45%)
- Phase 2 response rate of 27-57% is a WIDE range - cherry-picked reporting
- PFS6 of 26% is **barely above historical controls (20-25%)**
- "Long-term remission case reports" are ANECDOTES - survivorship bias, not evidence
- 2024-2026 ongoing trials (NCT05986805, NCT05663490, NCT06124356) are **Phase I/II with small n** - not definitive
- Orphan Drug Designation (Jan 2024) means FDA acknowledged unmet need, NOT that the drug works

**Molecular Analysis Caveats** (Reliability: 25%)
- Tanimoto similarity 0.0833 to temozolomide = **structurally UNRELATED** (threshold for similarity is typically >0.4)
- "Structurally novel" is a euphemism for "no class precedent for success in GBM"
- Related compounds (veonetinib, catequentinib, tandutinib) are ALL failed or investigational - no approved comparator
- No docking data available - we don't know binding affinity to relevant targets

### Missing Evidence

**What would you NEED to see before recommending this drug?**
1. **Phase III randomized controlled trial** showing OS benefit vs temozolomide + bevacizumab standard of care
2. **BBB penetration data** with CSF/plasma ratio proving therapeutic concentrations reach tumor
3. **Biomarker validation** (VEGFR expression, vascular density) predicting responders
4. **Long-term cardiac safety monitoring** data (not just 6-12 month trial duration)
5. **Explanation for why AstraZeneca abandoned it** - internal efficacy data, competitive landscape analysis

Currently available: **None of the above**

### Bottom Line

If cediranib was a winner, AstraZeneca wouldn't have killed the entire program. The 26% PFS6 is marginal, P-gp efflux means most drug stays out of the brain, and hERG inhibition adds cardiac risk to an already vulnerable population. "Ongoing trials" are Phase I/II - a decade from approval, if they succeed at all.

---

## Candidate 2: PERIFOSINE
**Risk Assessment: HIGH**

### Why This Drug Was Really Dropped

Perifosine reached **Phase 3 in multiple myeloma and failed**. It was also tested in colorectal cancer, pancreatic cancer, head and neck cancer - all failures. The pattern is clear: this drug doesn't work as a single agent in ANY cancer.

**The damning data**: 0/12 responses in Phase I/II GBM monotherapy. Zero. Not "low response rate" - ZERO. The drug was only kept alive by combining it with everything else (temsirolimus, TMZ, bevacizumab, pembrolizumab). At what point do we admit it has no intrinsic activity?

### Safety Concerns

**FAERS Risk Signals** (Severity: 8/10)
- Only 29 total reports with 1 GBM co-report - limited safety database
- Literature reports: **preclinical intracranial hemorrhages** in mouse models - this is CATASTROPHIC in human GBM patients
- **GI toxicity is dose-limiting**: nausea, vomiting, diarrhea prevent reaching therapeutic doses
- **Poor pediatric tolerability** - if children can't handle it, how will elderly GBM patients?

**Known Side Effects in Target Population**
- GBM patients have compromised nutritional status - GI toxicity worsens cachexia
- **Hemorrhage risk**: disrupting Akt/mTOR pathways affects vascular integrity; mouse brain hemorrhages are a red flag
- Polypharmacy interactions: adding perifosine to TMZ + bevacizumab + steroids + anticonvulsants = unpredictable toxicity cascade

**Drug Interactions**
- mTOR pathway inhibition + corticosteroids (standard in GBM) = immunosuppression, infection risk
- Combination with temsirolimus (another mTOR inhibitor) in trials suggests monotherapy inadequacy

### Evidence Weaknesses

**KG Score Limitations** (Reliability: 30%)
- Score -11.9366 (rank 30) is again text-mined association, not clinical validation
- High score reflects that Akt/mTOR pathway is POPULAR research topic - "publication bias favors fashionable targets"
- 90% of GBMs have PI3K/Akt dysregulation - yet multiple Akt inhibitors (ipatasertib, capivasertib, uprosertib) have failed in clinic
- KG doesn't capture "target is relevant BUT undruggable"

**FAERS Inverse Signal Caveats** (Reliability: 0%)
- No signal detected - provides zero evidence for OR against repurposing
- 1 co-report suggests minimal GBM use - where's the "FDA Fast Track enthusiasm" translating to real-world adoption?

**Literature Gaps** (Reliability: 40%)
- PFS6 75% in ongoing NCT05919210 is **uncontrolled, non-randomized, interim data**
- Historical controls (PFS6 50%) vary wildly by institution, MGMT status, patient selection
- FDA Fast Track (May 2024) means expedited review IF trial succeeds - not a stamp of efficacy
- "Phase III planning" is not Phase III completion - 5+ years and $50M+ away from approval
- The 0/12 monotherapy response rate is buried in supplementary data - why?

**Molecular Analysis Caveats** (Reliability: 20%)
- Tanimoto 0.0833 to lomustine = no structural relationship
- Alkylphospholipid class has NO approved drugs in oncology (miltefosine for leishmaniasis only)
- Similarity to oleylphosphocholine and edelfosine (both failed) predicts failure, not success
- No class precedent + zero monotherapy activity = unpredictable disaster

### Missing Evidence

**What would you NEED to see before recommending this drug?**
1. **ANY evidence of single-agent activity** - even 1/12 would be better than 0/12
2. **Explanation for intracranial hemorrhages** in preclinical models - was this dose-dependent? Strain-specific? Reproducible?
3. **Randomized Phase III data** comparing perifosine + TMZ vs TMZ alone
4. **Biomarker identifying responders** - if only works in combinations, which combination? For which patients?
5. **Dose-escalation data showing GI toxicity can be managed** long-term (not just 6-month trials)

Currently available: **None**

### Bottom Line

A drug with zero single-agent activity that causes brain hemorrhages in mice does not become a miracle cure by adding it to everything else. The 0/12 response rate is disqualifying. "FDA Fast Track" is not "FDA approval" - it's permission to fail faster.

---

## Candidate 3: TALAMPANEL
**Risk Assessment: MODERATE**

### Why This Drug Was Really Dropped

NCT00062504 terminated with reason: "Not specified." This is the WORST type of termination - no explanation suggests **efficacy futility** discovered mid-trial. If it was safe but ineffective, sponsors say "futility." If it was unsafe, they say "safety concerns." "Not specified" often means "we don't want to publicly admit it failed."

The drug reached Phase 2 in ALS, epilepsy, Parkinson's disease - all failed or stalled. Eli Lilly (original developer) abandoned it. AMPA antagonism is a 30-year-old idea that hasn't produced a single approved CNS drug for neurodegenerative or oncologic indications.

### Safety Concerns

**FAERS Risk Signals** (Severity: 3/10)
- **Zero FAERS reports** - this is actually concerning; it suggests the drug never left investigational settings
- No post-marketing surveillance data AT ALL
- Literature: "mild dizziness and ataxia" - in GBM patients with brain tumors causing baseline neurological deficits, this is NOT mild

**Known Side Effects in Target Population**
- Dizziness + ataxia in patients with brain tumors = **fall risk, impaired driving, reduced quality of life**
- AMPA antagonism affects normal glutamate signaling - cognitive side effects likely (memory, attention)
- GBM patients already struggle with executive function - adding glutamate blockade exacerbates this

**Drug Interactions**
- AMPA antagonism + anticonvulsants (many GBM patients on levetiracetam, phenytoin) = over-suppression of neural activity
- Sedation risk when combined with steroids, opioids (common in GBM symptom management)

### Evidence Weaknesses

**KG Score Limitations** (Reliability: 35%)
- Score -11.7475 (rank 11) driven by glutamate excitotoxicity literature - a HYPOTHESIS, not validated mechanism
- High rank reflects research popularity of glutamate biology in neuro-oncology - not clinical success
- Text-mining conflates "AMPA receptors are overexpressed in GBM" with "blocking them treats GBM"

**FAERS Inverse Signal Caveats** (Reliability: 0%)
- Zero reports = zero data = zero evidence of ANY kind

**Literature Gaps** (Reliability: 35%)
- Phase 2 newly diagnosed GBM: mOS 15.8 months vs 15.0 historical = **0.8 month benefit** (statistically insignificant)
- Trial MISSED its endpoint (12-month OS 64% vs 65% target) - this is a FAILURE
- Phase 2 recurrent GBM: "no significant activity" = it doesn't work in recurrent disease
- 2024-2026 trials (NCT06345622, NCT05849266) show activity ONLY in combinations - what is talampanel actually contributing?
- "Dual benefit" (antitumor + seizure control) is speculative - no trial powered to show seizure reduction as primary endpoint

**Molecular Analysis Caveats** (Reliability: 20%)
- Tanimoto 0.1286 to temozolomide = unrelated
- Only 1 database hit (self-match) = unique scaffold with NO precedent
- No similar compounds = no way to predict PK, efficacy, long-term safety
- "Excellent BBB penetration" claim based on preclinical data - human CSF levels unknown

### Missing Evidence

**What would you NEED to see before recommending this drug?**
1. **Explanation for NCT00062504 termination** - was it futility? Safety? Enrollment failure?
2. **Randomized trial showing seizure reduction** as co-primary endpoint (not just mentioned in case reports)
3. **Phase III data** - the Phase II newly diagnosed trial MISSED its endpoint
4. **CSF penetration data in humans** - preclinical isn't enough
5. **Long-term cognitive function testing** - does AMPA blockade impair memory, learning, quality of life?

Currently available: **None**

### Bottom Line

A drug that missed its Phase 2 endpoint, showed no activity in recurrent disease, and was terminated for unstated reasons is not a strong repurposing candidate. The 0.8-month OS benefit is noise. If AMPA antagonism worked, the epilepsy field would have adopted it decades ago.

---

## Candidate 4: RIVOCERANIB
**Risk Assessment: HIGH**

### Why This Drug Was Really Dropped

**There are ZERO glioblastoma trials.** Not "terminated trials" - NO trials AT ALL. The drug has been developed since 2008 with 64 investigational indications - and developers skipped GBM entirely. Why?

Possible reasons:
1. **BBB penetration predicted to be poor** (VEGFR2 inhibitors are typically large, polar molecules)
2. **Bevacizumab already failed to improve OS** in GBM (AVAglio, RTOG 0825 trials) - why test another anti-angiogenic?
3. **Internal preclinical studies showed no activity** (unpublished negative data)
4. **Risk/benefit unfavorable** - 42.5% hypertension rate unacceptable in brain tumor patients

### Safety Concerns

**FAERS Risk Signals** (Severity: 7/10)
- 94 total reports, 0 GBM co-reports - no safety data in target population
- Literature: **42.5% hypertension** in Phase 2 adenoid cystic carcinoma trial - this is UNACCEPTABLE
- Hypertensive crisis in GBM patients with intracranial pressure elevation = hemorrhagic stroke risk
- VEGFR2 inhibitor class effects: proteinuria, bleeding, arterial thrombosis

**Known Side Effects in Target Population**
- GBM patients on corticosteroids already have hypertension, diabetes, fluid retention
- Adding a drug that causes hypertension in 42.5% of patients = dangerous synergy
- Intracranial hemorrhage risk (VEGFR disrupts BBB integrity)
- Wound healing impairment (problematic for post-surgical patients)

**Drug Interactions**
- Likely CYP3A4 metabolism - interacts with dexamethasone, anticonvulsants
- Combination with bevacizumab (both VEGF pathway inhibitors) = additive toxicity with no added benefit

### Evidence Weaknesses

**KG Score Limitations** (Reliability: 25%)
- Score -11.8613 (rank 17) reflects mechanism relevance (VEGF pathway), not clinical evidence
- GBM overexpresses VEGF - but bevacizumab already exploits this and FAILED to improve OS
- KG cannot encode "target validated but approach failed"

**FAERS Inverse Signal Caveats** (Reliability: 0%)
- Zero GBM co-reports = zero GBM-specific safety/efficacy data

**Literature Gaps** (Reliability: 15%)
- "45% ORR in 20 recurrent GBM patients" - NO NCT NUMBER, no trial details, no publication
- This is a vague mention in one paper - likely a conference abstract or preliminary report
- No peer-reviewed Phase 1 or 2 data in GBM
- Phase 3 gastric cancer success DOES NOT translate to brain tumors (BBB, tumor biology entirely different)
- **Most damning**: if it worked in 20 patients with 45% response, why didn't they scale up to Phase 2? Because it probably didn't work.

**Molecular Analysis Caveats** (Reliability: 30%)
- Tanimoto 0.0921 to lomustine = unrelated
- Similarity to motesanib (0.55) - motesanib FAILED in thyroid and breast cancer
- TKI scaffold suggests predictable class effects - but class already failed in GBM (sunitinib, sorafenib trials negative)

### Missing Evidence

**What would you NEED to see before recommending this drug?**
1. **ANY GBM clinical trial** - literally any evidence in the target disease
2. **BBB penetration data** - CSF/plasma ratio, microdialysis studies
3. **Explanation for why 64 indications didn't include GBM** - was it tried and failed preclinically?
4. **Detailed report of the "20 patient study"** - who, when, where, how, why not published?
5. **Hypertension management protocol** - can 42.5% rate be reduced?

Currently available: **None**

### Bottom Line

Zero GBM trials means zero GBM evidence. The "20 patient study" is a ghost citation. Bevacizumab already proved anti-angiogenesis doesn't improve OS in GBM. 42.5% hypertension rate is disqualifying. If the drug had promise, someone would have tested it properly.

---

## Candidate 5: EDOTECARIN
**Risk Assessment: EXTREME**

### Why This Drug Was Really Dropped

**PHASE 3 TERMINATED FOR LACK OF EFFICACY.** This is not ambiguous. The drug was compared head-to-head against temozolomide, BCNU, and CCNU in recurrent GBM - and LOST. Interim analysis showed it was not going to meet endpoints, and the trial was stopped.

This is a FAILED drug. Not "business decision," not "unknown reason" - **efficacy failure in the exact indication we're discussing.**

### Safety Concerns

**FAERS Risk Signals** (Severity: 9/10)
- Only 3 total reports - drug was so poorly tolerated or ineffective that it never saw widespread use
- Literature: **Grade 4 granulocytopenia** (life-threatening bone marrow suppression)
- Literature: **Grade 3 seizures** - in GBM patients with baseline seizure risk, this is catastrophic
- Large complex molecule (indolocarbazole glycoside) suggests poor PK, unpredictable toxicity

**Known Side Effects in Target Population**
- Grade 4 granulocytopenia = neutropenia, infection risk, hospitalization, possible death
- GBM patients are immunocompromised from steroids and temozolomide - adding more myelosuppression is dangerous
- Grade 3 seizures = status epilepticus risk, brain damage, death
- Seizures in GBM patients can cause tumor hemorrhage, herniation

**Drug Interactions**
- Bone marrow suppression + temozolomide (standard of care) = severe pancytopenia
- CYP metabolism unknown - likely interacts with anticonvulsants

### Evidence Weaknesses

**KG Score Limitations** (Reliability: 20%)
- Score -11.8856 (rank 24) based on topoisomerase I mechanism - hypothesis without validation
- TOP1 is overexpressed in GBM, but irinotecan (approved TOP1 inhibitor) failed in GBM trials
- KG captures "mechanism mentioned in papers" not "mechanism validated in clinic"

**FAERS Inverse Signal Caveats** (Reliability: 0%)
- 3 reports, 0 GBM co-reports = no data

**Literature Gaps** (Reliability: 10%)
- **Phase 3 failure is DISQUALIFYING** - this is not a gap, this is definitive negative evidence
- "83% survival increase in mice" - preclinical data has >90% failure rate in translation to humans
- One 18-year-old case report with partial response - anecdotal, not generalizable
- "More stable than camptothecins" - yet failed where camptothecins also failed (GBM)

**Molecular Analysis Caveats** (Reliability: 15%)
- Tanimoto 0.0778 to temozolomide = unrelated
- Only 1 database hit (self-match) = no similar compounds for comparison
- Large complex structure suggests poor BBB penetration, poor oral bioavailability
- No class precedent for success

### Missing Evidence

**What would you NEED to see before recommending this drug?**

**NOTHING WOULD CHANGE MY MIND.** Phase 3 failure in GBM is terminal. The drug does not work. Post-hoc analysis, biomarker subgroups, "maybe different dose" - these are desperate rationalizations.

If there was a signal, the Phase 3 would have succeeded. It didn't.

### Bottom Line

This drug FAILED Phase 3 in the exact indication proposed for repurposing. Grade 4 granulocytopenia and Grade 3 seizures make it dangerous. Preclinical data is irrelevant after clinical failure. This should not even be on the candidate list.

---

## Closing Argument

The standard of evidence for drug repurposing in glioblastoma must be HIGH because patients' lives are at stake. These patients have median survival of 15 months - every month matters, and exposing them to ineffective or dangerous drugs steals precious time.

**The fundamental problems with these candidates:**

1. **Knowledge graph scores measure popularity, not efficacy** - all scores are text-mined associations that conflate "studied" with "validated"

2. **FAERS provides no positive evidence** - zero inverse signals, insufficient data across all candidates due to disease rarity

3. **"Dropped for business reasons" is often code for "quietly failed"** - pharmaceutical companies don't abandon winners

4. **Combination therapy masks lack of monotherapy activity** - PERIFOSINE (0/12 responses), TALAMPANEL (failed recurrent trial), RIVOCERANIB (no trials) only show activity when combined with everything else

5. **Preclinical data has >90% failure rate** - mouse survival, cell line IC50s, docking scores do not predict human benefit

6. **BBB penetration is assumed but unproven** - CEDIRANIB (P-gp efflux), RIVOCERANIB (no data), EDOTECARIN (large molecule)

7. **Phase 2 data is hypothesis-generating, not practice-changing** - response rates, PFS6, uncontrolled interim results are insufficient without Phase 3 confirmation

8. **Safety signals are minimized** - hERG inhibition, intracranial hemorrhages, Grade 4 granulocytopenia, 42.5% hypertension are dismissed as "manageable"

**The opportunity cost is enormous.** Every dollar spent repurposing failed drugs is a dollar NOT spent on:
- Novel mechanism drugs in early development
- Biomarker-driven precision oncology
- Immunotherapy combinations with better rationale
- Tumor-treating fields, surgical innovations, radiation advances

**The translation gap is real.** Only ~5% of repurposing candidates make it through Phase 3. The candidates presented have:
- 1 Phase 3 failure (EDOTECARIN - disqualified)
- 0 Phase 3 successes
- Limited Phase 2 data with marginal benefits
- No randomized controlled trial superiority over current standards

**I acknowledge when evidence IS strong** - CEDIRANIB has the most clinical experience and ongoing trials. But "most" among this group is still insufficient. A 26% PFS6 with cardiac toxicity risk does not justify investment over existing options.

**What evidence WOULD change my mind?**
- Phase 3 randomized trial showing OS benefit (not just PFS or response rate)
- Direct comparison vs current standard (TMZ + bevacizumab + radiation)
- Biomarker identifying responders (>50% of target population)
- Safety profile equal or better than current standards
- BBB penetration data proving therapeutic CNS levels
- Cost-effectiveness analysis showing value vs existing options

**For glioblastoma repurposing, I would support investment in drugs with:**
- Business termination + Phase 2 efficacy + manageable safety + ongoing Phase 3 planning = CEDIRANIB qualifies but remains borderline
- Novel mechanism + preclinical validation + Phase 1 safety + clear BBB penetration = none qualify

**I recommend against investing resources in:**
- EDOTECARIN - Phase 3 efficacy failure is disqualifying
- RIVOCERANIB - Zero GBM trials despite 16 years of development
- GENISTEIN - No clinical data, natural product PK challenges
- PERIFOSINE - 0/12 monotherapy responses, brain hemorrhages in mice
- TALAMPANEL - Missed Phase 2 endpoint, no recurrent disease activity

**Only CEDIRANIB has sufficient evidence to warrant cautious Phase 2b/3 consideration** - but even here, the corporate abandonment, P-gp efflux, and hERG risk give me serious pause. The other candidates range from "insufficient evidence" to "definitively failed."

The burden of proof lies with those proposing to treat dying patients with abandoned drugs. That burden has not been met.

**Respectfully submitted,**

The Skeptic
DrugRescue Evidence Court
