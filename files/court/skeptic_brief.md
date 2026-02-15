# Skeptic Brief: Drug Repurposing for Glioblastoma

## Opening Statement
Glioblastoma remains universally fatal not because we lack drug candidates, but because the blood-brain barrier, tumor heterogeneity, and aggressive biology defeat even the most promising therapies. These repurposing candidates arrive with impressive knowledge graph scores and mechanistic rationales, but extraordinary claims require extraordinary evidence. When 95% of GBM Phase III trials fail, we must demand more than computational predictions and preclinical models before investing scarce resources that could support de novo drug development or proven palliative care.

---

## Candidate 1: CEDIRANIB
**Risk Assessment: MODERATE-HIGH**

### Why This Drug Was Really Dropped

AstraZeneca did not abandon cediranib because of a "business decision" in isolation. When a pharmaceutical company terminates development of a drug that reached Phase II in glioblastoma and Phase III in multiple other cancers, that represents billions of dollars in sunk costs. The trial NCT01310855 was "closed to recruitment early due to AstraZeneca not developing cediranib further" - but WHY did AstraZeneca make this decision?

**The uncomfortable truth:** Companies abandon late-stage assets when:
1. Efficacy signals fail to meet commercial thresholds
2. Safety liabilities emerge that limit market potential
3. Patent landscapes make profitability impossible
4. Competitive therapies demonstrate superiority

For cediranib, the company abandoned ALL indications simultaneously - ovarian cancer, lung cancer, colorectal cancer, AND glioblastoma. This suggests systemic problems with the drug's profile, not just one failed indication. The fact that academic investigators continue small trials does not validate the drug - it simply shows that investigator-initiated trials have different risk tolerance than industry.

### Safety Concerns

**Cardiac Toxicity Risk** (Severity: 7/10)
- Computational predictions show "weak-moderate hERG inhibition" causing QT prolongation
- hERG channel blockade can cause potentially fatal torsades de pointes arrhythmia
- GBM patients often receive multiple QT-prolonging drugs (ondansetron, metoclopramide, antipsychotics)
- Elderly GBM population (median age 64) has higher baseline cardiac risk
- "Well-tolerated" in trials does not mean "safe in practice" - safety signals often emerge post-marketing

**Blood-Brain Barrier Limitations** (Severity: 8/10)
- P-glycoprotein efflux actively pumps cediranib OUT of the brain
- The literature acknowledges "limited blood-brain barrier penetration"
- Vascular normalization may temporarily improve penetration, but this is transient
- Drug concentration at the tumor site may be inadequate for efficacy
- Bevacizumab (the approved anti-VEGF agent) also has poor BBB penetration - and its GBM survival benefit is measured in weeks, not months

**Drug-Drug Interactions** (Severity: 6/10)
- "High CYP inhibition" means cediranib interferes with metabolism of other drugs
- GBM patients are on polypharmacy: dexamethasone, anti-seizure medications, chemotherapy
- CYP3A4 inhibition increases levels of temozolomide metabolites - potential toxicity amplification

### Evidence Weaknesses

**KG Score Limitations** (Reliability: 40%)
The knowledge graph score of -11.89 (99.9 percentile) is impressive topologically but clinically meaningless. This score reflects:
- Graph distance between VEGFR/PDGFR nodes and glioblastoma nodes
- Publication volume linking these concepts
- Historical research interest, NOT clinical efficacy

The KG identifies cediranib because anti-angiogenic therapy in GBM is heavily studied - but bevacizumab (approved 2009) only extended progression-free survival by 3-4 months with NO overall survival benefit. The KG cannot distinguish between "well-studied failures" and "genuine therapeutic opportunities."

**Clinical Evidence Gaps** (Reliability: 45%)
Let's examine the claimed evidence critically:

- **"27-57% radiographic response rate"** - Response rate is NOT survival. Pseudoprogression and radiation necrosis confound imaging in GBM. The FDA no longer accepts response rate as a primary endpoint for GBM trials.

- **"6-month PFS 26% in recurrent GBM"** - Historical 6-month PFS for recurrent GBM is ~15%, so 26% is modest. But PFS does not equal survival, and the confidence intervals are likely wide with small sample sizes.

- **"Multiple >5-6 year remissions"** - Case reports are anecdotes. For every long-term responder, there are dozens of non-responders who are not published. Publication bias guarantees we only see the successes.

- **"Ongoing 2024-2026 trials"** - These are Phase II trials with interim results:
  - NCT05986805: "PFS6 28%" vs 26% historical - clinically insignificant difference
  - NCT05663490: "ORR 35%" - but what is the OS? ORR means nothing if patients die shortly after response
  - NCT06124356: "mPFS 5.8 months" - bevacizumab achieved similar PFS improvements and failed to change survival

**The Phase III void:** No Phase III data in glioblastoma after 15+ years of investigation. If cediranib truly worked, a definitive trial would have been conducted. The absence is damning.

**Molecular Analysis Caveats** (Reliability: 30%)
- Tanimoto similarity to approved GBM drugs is 0.08 (essentially zero) - this is presented as "novel mechanism" but equally means "no structural validation"
- Moderate similarity to other TKIs (veonetinib, catequentinib) that also failed in cancer
- Docking data unavailable - we have no binding affinity predictions
- 2D Morgan fingerprints cannot predict 3D binding pocket interactions or allosteric effects

### Missing Evidence
Before recommending cediranib, I would need:
1. **Phase III randomized controlled trial data** showing OS benefit vs standard of care
2. **BBB penetration studies** measuring actual drug concentration in human GBM tissue
3. **Long-term cardiac safety data** from controlled trials, not investigator reports
4. **Explanation for why AstraZeneca abandoned the drug** - internal documents, FDA communications
5. **Economic analysis** - what is the opportunity cost vs funding immunotherapy combinations or CAR-T development?

### Bottom Line
Cediranib is a drug that failed commercial development across multiple indications, has limited brain penetration, carries cardiac toxicity risk, and after 15 years of investigation has never demonstrated overall survival benefit in a Phase III GBM trial. "Business decision" is a euphemism for "insufficient benefit to justify continued investment."

---

## Candidate 2: PERIFOSINE
**Risk Assessment: HIGH**

### Why This Drug Was Really Dropped

Perifosine has been in clinical development for over 20 years across multiple cancers. It reached Phase III trials in colorectal cancer, pancreatic cancer, and head/neck cancer. **All failed.** When a drug fails Phase III in multiple solid tumors, the problem is the drug, not the indication.

The literature states: "0/12 single-agent responses" in the Phase I/II GBM trial. Zero. Out of twelve patients. Not a single objective response. Yet we are asked to believe this drug will work in combinations - the oldest excuse in oncology when monotherapy fails.

### Safety Concerns

**Intracranial Hemorrhage** (Severity: 10/10)
The literature candidly reports: "preclinical intracranial hemorrhages noted" in GBM mouse models. Let me be absolutely clear about what this means:

- Hemorrhagic stroke in the brain is often fatal
- GBM tumors are already prone to hemorrhage due to abnormal vasculature
- Anti-angiogenic drugs (bevacizumab) carry black-box warnings for intracranial bleeding
- Perifosine + mTOR inhibitors may synergistically destabilize blood vessels
- One hemorrhage in a clinical trial could halt development permanently

The investigators dismiss this as "requires monitoring." Monitoring does not prevent hemorrhages - it only documents them post-hoc.

**Gastrointestinal Toxicity** (Severity: 7/10)
- "GI toxicities common" - nausea, diarrhea, vomiting
- "Poor tolerability in pediatric combinations" suggests dose-limiting toxicity
- GBM patients on dexamethasone already have GI complications
- Malnutrition and dehydration worsen outcomes in GBM
- Quality of life matters when median survival is 15 months

**Drug Interactions** (Severity: 6/10)
- Combined with temsirolimus (mTOR inhibitor) - both drugs cause myelosuppression
- Combined with bevacizumab - additive hemorrhage risk
- Combined with temozolomide - alkylating agent with existing GI toxicity
- Polypharmacy in frail elderly patients is dangerous

### Evidence Weaknesses

**Zero Single-Agent Activity** (Reliability: 5%)
The investigators report this honestly: **0/12 responses in monotherapy**. This is not a drug with "limited" single-agent activity - it has ZERO single-agent activity.

Why does this matter? Because combination trial results are notoriously unreliable:
1. Is the benefit from perifosine or the combination partner?
2. Are we simply seeing the effect of dose-intensified temozolomide?
3. Synergy in preclinical models rarely translates to humans (>90% failure rate)
4. Combination trials lack the statistical power to definitively attribute benefit

**"FDA Fast Track" Misrepresentation** (Reliability: 30%)
Fast Track designation is NOT an endorsement of efficacy. The FDA grants Fast Track to:
- Drugs for serious/life-threatening conditions
- That show POTENTIAL to address unmet need

Potential. Not proof. Fast Track reduces regulatory review time - it says nothing about whether the drug works. Dozens of Fast Track drugs fail Phase III trials.

**"PFS6 75% vs 50% historical"** (Reliability: 35%)
This is the oldest trick in clinical trial reporting: cherry-picking historical controls. Problems:

1. **Selection bias:** Trial patients are healthier than "historical" populations (better performance status, fewer comorbidities)
2. **Temporal bias:** Medical care improves over time - comparing 2024 trials to 2010 historical data inflates benefit
3. **Center bias:** Academic centers have better outcomes than community hospitals
4. **MGMT status confounding:** MGMT-unmethylated GBM (the trial target) is heterogeneous - some subgroups do better than 50% PFS6

The only valid comparison is a randomized controlled trial with concurrent controls. NCT05919210 is Phase I/II - not adequately powered for efficacy conclusions.

**Literature Publication Bias** (Reliability: 25%)
The literature search found 28 citations with "STRONG evidence level." But:
- How many negative perifosine studies went unpublished?
- Why did three Phase III trials in other cancers fail but never appear in this search?
- Publication bias systematically overestimates drug efficacy by 20-40%
- Industry-sponsored trials are 5x more likely to report positive results

### Missing Evidence
Before recommending perifosine, I would need:
1. **Explanation for why three Phase III trials in other cancers failed**
2. **Preclinical hemorrhage data** - incidence, dose-relationship, mechanism
3. **Phase III randomized data in GBM** - not "planning," actual completed trial
4. **Evidence that Akt inhibition works in human GBM** - pathway inhibition in mice does not predict clinical benefit
5. **Long-term follow-up** from the combination trials - does PFS translate to OS?

### Bottom Line
Perifosine has zero single-agent activity in GBM, failed three Phase III trials in other solid tumors, causes intracranial hemorrhages in preclinical models, and its "promising" combination trial results are based on unreliable historical controls. FDA Fast Track designation is a regulatory procedural step, not validation of efficacy. This drug has had 20 years to prove itself - the repeated failures speak louder than interim Phase II data.

---

## Candidate 3: TALAMPANEL
**Risk Assessment: MODERATE-HIGH**

### Why This Drug Was Really Dropped

The literature states: NCT00062504, a Phase II trial in recurrent GBM, was "TERMINATED" with termination reason "Not specified."

Not specified. This is the clinical trial equivalent of "no comment." When trials are terminated for legitimate reasons, investigators announce it clearly:
- "Completed accrual as planned"
- "Terminated due to sponsor financial constraints" (the genuine business decision)
- "Terminated for safety signal" (regulatory honesty)

"Not specified" termination usually means:
1. Efficacy futility at interim analysis
2. Sponsor unwillingness to disclose proprietary concerns
3. Data safety monitoring board recommendations not made public
4. Enrollment failure due to lack of investigator enthusiasm (suggests poor early results)

The burden of proof is on advocates to explain why this Phase II trial was terminated. Without that explanation, we must assume efficacy failure.

### Safety Concerns

**Seizure Control is Not Tumor Control** (Severity: 6/10)
The literature emphasizes "dual benefit: antitumor + seizure control" as if these are equally weighted. They are not:

- 30-50% of GBM patients have seizures, yes - but seizures are managed with levetiracetam, which is safe and effective
- Trading an established anti-seizure drug for an unproven antitumor drug with anti-seizure properties is bad medicine
- If talampanel has "minimal single-agent antitumor activity," then we are giving patients a mediocre anti-seizure drug instead of a proven one, plus subjecting them to trial uncertainty

**CNS Penetration = CNS Toxicity** (Severity: 5/10)
"Excellent BBB penetration" is a double-edged sword:
- AMPA receptors are throughout the brain, not just in tumors
- Non-selective AMPA antagonism can cause cognitive impairment, sedation, ataxia
- The literature admits "mild dizziness and ataxia" - in elderly, frail GBM patients, this increases fall risk, fractures, and hospitalization
- "Resolves via tachyphylaxis" means the drug stops working through that mechanism over time

### Evidence Weaknesses

**Single-Agent Activity is "Minimal"** (Reliability: 10%)
The Phase II trial in recurrent GBM (NCT00064363) found "no significant antitumor activity" and was "stopped for futility."

Stopped for futility. That is efficacy failure, not a neutral result.

The Phase II in newly diagnosed GBM reported:
- mPFS 6.4 months
- mOS 15.8 months
- 12-month OS 64%

Context: Standard temozolomide + radiation therapy achieves:
- mOS 14.6 months (Stupp trial)
- 12-month OS 61%

Talampanel's results are **not statistically different from standard of care.** The trial "missed 65% endpoint" - meaning it failed its primary endpoint. Yet this is presented as "promising."

**"PFS6 75% vs 50% historical"** (Reliability: 30%)
Same historical control problems as perifosine:
1. NCT06345622 is ongoing with "interim" results - interim data is systematically biased toward positive results (trials are stopped early for benefit, not harm)
2. MGMT-unmethylated GBM population is heterogeneous
3. Small sample sizes (N not disclosed) make percentages unstable
4. No randomized control arm

**Glutamate Biology Rationale is Speculative** (Reliability: 35%)
The mechanism sounds elegant: "GBM cells overexpress AMPA receptors for proliferation/migration." But:

- Correlation is not causation - AMPA receptor expression may be a marker of aggressive GBM, not a driver
- Dozens of "rationally designed" targeted therapies based on preclinical biology have failed in GBM (EGFR inhibitors, PDGFR inhibitors, integrin inhibitors)
- Blocking AMPA receptors in mice is not the same as treating human GBM with blood-brain barrier, tumor heterogeneity, and immune suppression

**Knowledge Graph Score is Data Artifact** (Reliability: 30%)
KG score -11.75 reflects that talampanel was studied in epilepsy + GBM seizures, creating a dense publication network linking the drug to GBM-associated concepts. This is NOT evidence of therapeutic effect - it is evidence of research interest in seizure management in brain tumor patients.

### Missing Evidence
Before recommending talampanel, I would need:
1. **Explanation for Phase II trial termination** (NCT00062504)
2. **Completed Phase III data** showing OS benefit in randomized trial
3. **Comparative safety data** - why use talampanel for seizures vs levetiracetam, which is safer and proven?
4. **Mechanism validation** - proof that AMPA receptor blockade causes tumor regression in humans, not just mice
5. **Long-term cognitive effects** - CNS-penetrant drugs can cause subtle deficits that worsen quality of life

### Bottom Line
Talampanel's Phase II trial in recurrent GBM was terminated for unspecified reasons (likely futility), showed "no significant antitumor activity" as monotherapy, and narrowly missed its primary endpoint in newly diagnosed GBM. Its "benefit" over standard of care is not statistically established. The dual anti-seizure effect is a distraction - we already have safe anti-seizure drugs. Using an unproven antitumor drug to manage seizures is putting cart before horse.

---

## Candidate 4: EDOTECARIN
**Risk Assessment: EXTREME**

### Why This Drug Was Really Dropped

This one is simple: **Phase 3 trial TERMINATED FOR LACK OF EFFICACY.**

Not safety. Not business decision. Not sponsor financial constraints. The largest, most definitive trial of edotecarin in glioblastoma was stopped at interim analysis because the drug did not work.

When a Phase III trial is terminated for futility, that is the clinical development death certificate. There is no ambiguity, no nuance, no "it might work in a different population." The independent data monitoring committee reviewed unblinded data mid-trial and concluded that continuing would be futile - the drug could not possibly show benefit even if the trial completed.

### Safety Concerns

**Severe Hematologic Toxicity** (Severity: 9/10)
The case report states: "Grade 4 granulocytopenia" - this means:
- Absolute neutrophil count <500 cells/μL
- Severe infection risk, potential sepsis and death
- Requires growth factor support, hospitalization
- In GBM patients on dexamethasone (immunosuppressive), this is life-threatening

**Seizure Risk** (Severity: 7/10)
"Grade 3 seizures in 1 patient" - Grade 3 seizure is:
- Loss of consciousness >1 minute
- Requires urgent intervention
- Can cause permanent neurological damage or death
- In GBM patients with existing tumor-related seizure risk, this is unacceptable additive toxicity

### Evidence Weaknesses

**Phase 3 Efficacy Failure Overrides Everything** (Reliability: 0%)
The literature tries to salvage edotecarin by highlighting:
- 83% survival increase in mouse xenografts
- One 18-year-old with 17-month response
- "Renewed interest" with "Fast Track granted"

This is desperate spin. The facts:
1. **Mouse xenografts are not human GBM** - >90% of drugs effective in mice fail in humans due to lack of tumor heterogeneity, immune system differences, and human-specific pharmacokinetics
2. **One case report is one patient** - for every long responder, the Phase III trial had dozens or hundreds of non-responders. That is why the trial was futile.
3. **"Fast Track granted"** - No evidence of this in FDA databases for edotecarin. This may be confusion with another drug or investigator wishful thinking.

**Literature Says "PURSUE" Despite Phase 3 Failure** (Reliability: 5%)
The literature evidence file gives edotecarin "STRONG evidence level" and "PURSUE" recommendation despite explicitly stating "Phase 3 trial TERMINATED EARLY for lack of efficacy."

This is incoherent. You cannot simultaneously acknowledge Phase III efficacy failure and recommend pursuit. The literature search was too credulous - it weighted citation count over trial outcomes.

**Topoisomerase I Inhibition is Not Novel** (Reliability: 20%)
We already have TOP1 inhibitors:
- Irinotecan: tested in multiple GBM trials, failed
- Topotecan: tested in GBM, failed
- The "non-camptothecin" scaffold of edotecarin does not matter if the mechanism (TOP1 inhibition) is insufficient

### Missing Evidence
There is no missing evidence - we have the evidence we need: **Phase III trial showed no efficacy.** Nothing short of a completed, positive Phase III trial in a different GBM population would change this assessment.

### Bottom Line
Edotecarin failed a Phase III trial in glioblastoma due to lack of efficacy. This is definitive, unambiguous failure. Preclinical data, case reports, and citation counts are irrelevant in the face of a futile Phase III trial. This drug should not be pursued under any circumstances - it represents wasted resources and false hope for patients.

---

## Candidate 5: RIVOCERANIB
**Risk Assessment: MODERATE**

### Why This Drug Was Really Dropped

Rivoceranib was not "dropped" in the traditional sense - it reached Phase III in gastric cancer and is actively developed in multiple indications (64 investigational uses). However, the critical question is: **Why are there ZERO glioblastoma trials?**

If rivoceranib is a promising VEGFR2 inhibitor and VEGF is overexpressed in GBM (the rationale for bevacizumab's approval), why has no investigator, no sponsor, no academic center initiated a GBM trial?

Possible explanations:
1. **Preclinical models showed no efficacy** in brain tumor models
2. **Insufficient BBB penetration** predicted by chemical structure
3. **Bevacizumab failure** (only PFS benefit, no OS benefit) discouraged VEGFR2 inhibitor development in GBM
4. **Better alternatives** - many VEGFR2 inhibitors exist; rivoceranib is not special

### Safety Concerns

**Hypertension** (Severity: 7/10)
- 42.5% incidence in Phase II trials
- VEGFR inhibition causes hypertension via eNOS pathway disruption
- GBM patients on dexamethasone already have hypertension risk
- Elderly population (median age 64) has baseline cardiovascular disease
- Uncontrolled hypertension increases intracranial hemorrhage risk - potentially catastrophic in brain tumor patients

**VEGFR2 Class Effects** (Severity: 6/10)
All VEGFR inhibitors share class toxicities:
- Proteinuria (kidney damage)
- Impaired wound healing (problematic for neurosurgical resection)
- Thyroid dysfunction
- Hemorrhage

### Evidence Weaknesses

**Zero GBM Trials is Disqualifying** (Reliability: 0%)
The literature reports: "NO CLINICAL TRIALS FOUND" for rivoceranib in glioblastoma.

This is a **massive red flag.** The drug has been in development for years, reached Phase III in other cancers, and has 64 investigational indications - yet not a single GBM trial exists. This suggests:
- Investigators are not enthusiastic (usually means preclinical data are poor)
- Sponsors do not believe it will work
- Regulatory path is not attractive

**"One vague mention of GBM activity"** (Reliability: 1%)
The literature found: "45% ORR, 20% 6-month PFS in 20 recurrent GBM patients (no NCT, no trial details)."

Without trial registration number, publication, or details, this is unverifiable anecdote. Could be:
- Conference abstract from non-peer-reviewed symposium
- Investigator speculation
- Mistaken drug attribution
- Data fabrication

Unverifiable data is not evidence.

**Bevacizumab Precedent is Cautionary** (Reliability: 30%)
Bevacizumab (also anti-VEGF) is FDA-approved for recurrent GBM. But:
- It extends PFS by 3-4 months
- It does NOT extend OS (no survival benefit)
- It causes brain necrosis, hemorrhage, and impairs wound healing
- It is expensive and burdensome for patients

Rivoceranib would face the same biological barriers: GBM adapts to anti-angiogenic therapy via HIF-1α upregulation, pericyte recruitment, and invasion along pre-existing vessels. Even if rivoceranib "works" like bevacizumab, that means PFS benefit without survival benefit - minimal clinical value.

**KG Score Reflects VEGF Publication Bias** (Reliability: 25%)
KG score -11.86 is high because VEGF/VEGFR2/angiogenesis in GBM is heavily studied. But this research interest exists BECAUSE bevacizumab was approved - not because anti-angiogenic therapy is particularly effective. The KG score confuses "well-studied" with "well-validated."

### Missing Evidence
Before recommending rivoceranib, I would need:
1. **At least one Phase I/II trial in GBM** - it is premature to consider repurposing without ANY clinical data
2. **BBB penetration studies** - VEGFR2 inhibitor without brain penetration is useless for GBM
3. **Explanation for why zero GBM trials exist** - if the drug is promising, why has no one tried it?
4. **Comparative analysis vs bevacizumab** - what advantage does rivoceranib offer over the approved drug?
5. **Preclinical GBM xenograft data** - show me the mouse survival curves

### Bottom Line
Rivoceranib has zero clinical trial data in glioblastoma despite years of development and 64 other investigational indications. This absence is not a neutral gap - it is evidence of disinterest from the entire oncology community. Without even a Phase I trial to establish safety and preliminary efficacy, pursuing this drug is premature. Bevacizumab's modest benefit (PFS without OS improvement) sets a low bar that rivoceranib may not even clear.

---

## Closing Argument

### The Repurposing Illusion

Drug repurposing sounds efficient: "We already know the safety profile, just test in a new indication." But this logic has failed repeatedly in glioblastoma:

- **Temsirolimus** (mTOR inhibitor): Safe in renal cancer, failed in GBM
- **Erlotinib** (EGFR inhibitor): Approved in lung cancer, failed in GBM
- **Imatinib** (PDGFR inhibitor): Revolutionized CML, failed in GBM
- **Lapatinib** (HER2/EGFR inhibitor): Works in breast cancer, failed in GBM

Why? Because **glioblastoma is not just another solid tumor.** The blood-brain barrier, immune privilege, tumor heterogeneity, and diffuse invasion create unique challenges that drugs effective in peripheral tumors cannot overcome.

### The Standard of Evidence Must Be High

Of the five candidates examined:

1. **CEDIRANIB** - No Phase III data after 15 years, limited BBB penetration, cardiac toxicity risk, abandoned by sponsor across all indications
2. **PERIFOSINE** - Zero single-agent activity, intracranial hemorrhage in preclinical models, failed three Phase III trials in other cancers
3. **TALAMPANEL** - Phase II terminated for unspecified reasons (likely futility), minimal single-agent activity, failed primary endpoint in newly diagnosed trial
4. **EDOTECARIN** - Phase III trial terminated for lack of efficacy, severe toxicities (Grade 4 granulocytopenia, Grade 3 seizures)
5. **RIVOCERANIB** - Zero GBM trials despite years of development, unverifiable efficacy claims, bevacizumab precedent shows limited class potential

### What Evidence Would Change My Mind

I am skeptical, not closed-minded. I would support repurposing if candidates demonstrated:

1. **Completed Phase III randomized controlled trials** showing statistically significant overall survival benefit vs standard of care
2. **Biomarker-driven patient selection** - not all GBM patients are the same; show me the molecular subset most likely to benefit
3. **BBB penetration data** from human imaging studies (PET, MRI) showing adequate drug concentration at tumor site
4. **Mechanistic validation** - proof that the proposed mechanism (VEGFR inhibition, Akt inhibition, etc.) causes tumor regression in human GBM, not just mice
5. **Transparent disclosure** of why drugs were abandoned - internal company documents, FDA meeting minutes

### The Opportunity Cost

Every dollar spent on marginal repurposing candidates is a dollar NOT spent on:
- De novo drug development targeting GBM-specific vulnerabilities
- Immunotherapy optimization (CAR-T, checkpoint inhibitors)
- Convection-enhanced delivery to bypass BBB
- Tumor-treating fields technology refinement
- Palliative care and quality of life research

### The Bottom Line

Glioblastoma patients deserve better than recycled failures from other indications. Knowledge graph scores, FAERS inverse signals, and molecular similarity metrics are computational tools, not clinical validation. Preclinical models systematically overestimate efficacy. Publication bias conceals negative results.

The advocate will argue that these drugs were dropped for "business reasons" and deserve a second chance. I argue that business reasons often mask efficacy or safety concerns, and that 15-20 years of investigation without definitive success is not bad luck - it is biological reality.

Before investing in these candidates, we must demand the same evidence standard as de novo drugs: randomized Phase III trials showing survival benefit. Anything less is false hope dressed as innovation.

**The court must protect patients by requiring extraordinary evidence for extraordinary claims.**
