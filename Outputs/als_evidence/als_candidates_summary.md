# ALS Drug Repurposing Candidates - Knowledge Graph Analysis

**Disease**: Amyotrophic Lateral Sclerosis (ALS)
**Method**: RotatE embeddings
**Total Compounds Scored**: 24,313
**Candidates Returned**: 30
**Analysis Time**: 666.9 ms

## Summary Statistics

- **Dropped Drugs** (Phase I-III trials, never approved): 5
- **Withdrawn Drugs**: 0
- **Novel/Approved Drugs**: 25

## Disease Entities Used
- Disease::MESH:D000690
- Disease::DOID:332

## Treatment Relations Used
- DRUGBANK::treats::Compound:Disease
- GNBR::T::Compound:Disease
- Hetionet::CtD::Compound:Disease

---

## Top 30 Candidates (Sorted by Status: Dropped First)

### DROPPED DRUGS - Prime Repurposing Targets

| Rank | Drug Name | ChEMBL ID | DrugBank ID | Max Phase | KG Percentile | KG Score | Z-Score | SMILES |
|------|-----------|-----------|-------------|-----------|---------------|----------|---------|--------|
| 1 | **OLESOXIME** | CHEMBL3545254 | - | Phase 3 | 100.0 | -11.208 | 7.644 | CC(C)CCC[C@@H](C)[C@H]1CC[C@H]2[C@@H]3CCC4=CC(=NO)CC[C@]4(C)[C@H]3CC[C@]12C |
| 4 | **THREONINE** | CHEMBL291747 | DB00156 | Phase 2 | 99.99 | -11.900 | 5.919 | C[C@@H](O)[C@H](N)C(=O)O |
| 5 | **PRIDOPIDINE** | CHEMBL596802 | DB11947 | Phase 3 | 99.98 | -11.966 | 5.755 | CCCN1CCC(c2cccc(S(C)(=O)=O)c2)CC1 |
| 14 | **POTASSIUM** | CHEMBL1201290 | DB14500 | Phase 3 | 99.95 | -12.238 | 5.076 | [K] |
| 16 | **METHYLCOBALAMIN** | CHEMBL4297672 | DB03614 | Phase 2 | 99.94 | -12.257 | 5.028 | - |

### NOVEL/APPROVED DRUGS

| Rank | Drug Name | ChEMBL ID | DrugBank ID | KG Percentile | KG Score | Z-Score |
|------|-----------|-----------|-------------|---------------|----------|---------|
| 2 | **RILUZOLE** | CHEMBL744 | DB00740 | 100.0 | -11.615 | 6.631 |
| 3 | **ARIMOCLOMOL** | CHEMBL4760607 | DB05025 | 99.99 | -11.749 | 6.296 |
| 6 | **SUGAMMADEX** | - | - | 99.98 | -11.992 | 5.690 |
| 7 | **GABAPENTIN** | - | - | 99.98 | -12.003 | 5.662 |
| 8 | **PRAMIPEXOLE** | - | - | 99.97 | -12.021 | 5.618 |
| 9 | **BROMOCRIPTINE** | CHEMBL493 | DB01200 | 99.97 | -12.034 | 5.584 |
| 10 | **CHEBI:53317** | - | - | 99.96 | -12.071 | 5.494 |
| 11 | **DEXAMETHASONE** | CHEMBL384467 | DB01234 | 99.96 | -12.073 | 5.487 |
| 12 | **TREHALOSE** | CHEMBL1236395 | DB12310 | 99.95 | -12.109 | 5.398 |
| 13 | **CANNABINOIDS** | - | - | 99.95 | -12.227 | 5.104 |
| 15 | **1,4-DIHYDROPYRIDINE** | - | - | 99.94 | -12.255 | 5.034 |
| 17 | **RIFAMPICIN** | CHEMBL374478 | DB01045 | 99.93 | -12.279 | 4.973 |
| 18 | **FLUOXETINE** | CHEMBL41 | DB00472 | 99.93 | -12.284 | 4.963 |
| 19 | **ETHANOL** | CHEMBL545 | DB00898 | 99.93 | -12.290 | 4.947 |
| 20 | **SIMENDAN** | - | - | 99.92 | -12.292 | 4.941 |
| 21 | **MELATONIN** | CHEMBL45 | DB01065 | 99.92 | -12.302 | 4.917 |
| 22 | **VERAPAMIL** | CHEMBL6966 | DB00661 | 99.91 | -12.316 | 4.881 |
| 23 | **ETHYLENE GLYCOL** | CHEMBL457299 | - | 99.91 | -12.319 | 4.875 |
| 24 | **PACLITAXEL** | CHEMBL428647 | DB01229 | 99.91 | -12.340 | 4.821 |
| 25 | **VALPROIC ACID** | CHEMBL109 | DB00313 | 99.9 | -12.343 | 4.816 |
| 26 | **2-AMINO-1-METHYL-4,5-DIHYDRO-1H-IMIDAZOL-4-ONE** | - | DB11846 | 99.9 | -12.354 | 4.788 |
| 27 | **RISPERIDONE** | CHEMBL85 | DB00734 | 99.89 | -12.363 | 4.766 |
| 28 | **ROCURONIUM** | - | - | 99.89 | -12.367 | 4.756 |
| 29 | **PHENYTOIN** | CHEMBL16 | DB00252 | 99.88 | -12.396 | 4.684 |
| 30 | **ASPIRIN** | CHEMBL25 | DB00945 | 99.88 | -12.411 | 4.646 |

---

## Key Findings

### Priority Repurposing Candidates (Dropped Drugs)

1. **OLESOXIME** - Top-ranked compound with strongest KG evidence (percentile: 100.0, z-score: 7.644)
   - Failed Phase 3 trials but shows exceptional graph connectivity to ALS
   - Neuroprotective cholesterol-like compound

2. **PRIDOPIDINE** - High KG score (percentile: 99.98, z-score: 5.755)
   - Phase 3 candidate
   - Dopamine stabilizer with potential neuroprotective effects

3. **THREONINE** - Amino acid with strong graph evidence (percentile: 99.99, z-score: 5.919)
   - Phase 2 candidate
   - Essential amino acid, may support protein synthesis

4. **METHYLCOBALAMIN** - Vitamin B12 derivative (percentile: 99.94, z-score: 5.028)
   - Phase 2 candidate
   - Known for nerve regeneration properties

5. **POTASSIUM** - Electrolyte supplement (percentile: 99.95, z-score: 5.076)
   - Phase 3 candidate
   - May address electrolyte imbalances in ALS

### Notable Novel/Approved Drugs

- **RILUZOLE** - The only FDA-approved drug for ALS, correctly identified by the graph (rank 2)
- **ARIMOCLOMOL** - Heat shock protein inducer, currently in clinical development for ALS
- **GABAPENTIN** - Approved for other conditions, shows strong ALS graph connectivity
- **DEXAMETHASONE** - Corticosteroid with anti-inflammatory properties
- **MELATONIN** - Antioxidant with neuroprotective potential

---

## Interpretation

**KG Score**: Lower (more negative) scores indicate stronger predicted treatment relationships
**KG Percentile**: Higher percentiles (75-100) indicate stronger evidence in the knowledge graph
**Z-Score**: Measures how many standard deviations above the mean the compound scores
**Status = "dropped"**: These drugs reached Phase I-III trials but were never approved - prime repurposing targets

---

*Generated using RotatE embeddings on DRKG (Drug Repurposing Knowledge Graph)*
*Total compounds in graph: 24,313*
