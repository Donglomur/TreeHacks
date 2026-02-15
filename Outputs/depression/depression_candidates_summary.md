# Depression Drug Repurposing Candidates

**Disease:** Depression
**Method:** RotatE embeddings on DRKG
**Total Compounds Scored:** 24,313
**Candidates Returned:** 30 (min_percentile: 75.0)
**Discovery Date:** 2026-02-14

## Summary Statistics

- **Dropped Drugs** (Phase I-III, never approved): 5
- **Withdrawn Drugs**: 0
- **Novel/Other Compounds**: 25

## Top Candidates by Status

### DROPPED DRUGS (Prime Repurposing Targets)

| Rank | Drug Name | ChEMBL ID | Max Phase | KG Percentile | KG Score | Z-Score | SMILES |
|------|-----------|-----------|-----------|---------------|----------|---------|--------|
| 1 | BEFURALINE | CHEMBL1076256 | Phase 2 | 100.0 | -10.91 | 5.79 | O=C(c1cc2ccccc2o1)N1CCN(Cc2ccccc2)CC1 |
| 5 | ROXINDOLE | CHEMBL431367 | Phase 2 | 99.98 | -11.06 | 5.53 | Oc1ccc2[nH]cc(CCCCN3CC=C(c4ccccc4)CC3)c2c1 |
| 12 | SEROTONIN | CHEMBL39 | Phase 3 | 99.95 | -11.23 | 5.24 | NCCc1c[nH]c2ccc(O)cc12 |
| 15 | BENZODIAZEPINE | CHEMBL4297264 | Phase 3 | 99.94 | -11.26 | 5.19 | C1=Cc2ccccc2NN=C1 |
| 22 | LITHIUM | CHEMBL1201333 | Phase 3 | 99.91 | -11.31 | 5.09 | [Li] |

### NOVEL/OTHER COMPOUNDS (Top 10)

| Rank | Drug Name | ChEMBL/DrugBank ID | KG Percentile | KG Score | Z-Score |
|------|-----------|-------------------|---------------|----------|---------|
| 2 | ETHANOL | CHEMBL545 / DB00898 | 100.0 | -10.97 | 5.69 |
| 3 | N-((2,3-DIHYDRO-1,4-BENZODIOXIN-2-YL)METHYL)-5-METHOXY-1H-INDOLE-3-ETHANAMINE | - | 99.99 | -11.03 | 5.59 |
| 4 | CHEBI:3724 | - | 99.99 | -11.05 | 5.56 |
| 6 | WS 5570 | - | 99.98 | -11.09 | 5.48 |
| 7 | 1-(5-CHLORO-1-((2,4-DIMETHOXYPHENYL)SULFONYL)-3-(2-METHOXYPHENYL)-2-OXO-2,3-DIHYDRO-1H-INDOL-3-YL)-4-HYDROXY-N,N-DIMETHYL-2-PYRROLIDINECARBOXAMIDE | - | 99.98 | -11.13 | 5.41 |
| 8 | DIBENZAZEPINES | - | 99.97 | -11.14 | 5.40 |
| 9 | RUBIDIUM CHLORIDE | - | 99.97 | -11.18 | 5.33 |
| 10 | REMIFEMIN | - | 99.96 | -11.18 | 5.32 |
| 11 | CHEBI:35501 | - | 99.96 | -11.23 | 5.24 |
| 13 | NOXIPTILIN | - | 99.95 | -11.24 | 5.22 |

## Notable Findings

### Highest Priority Dropped Drugs
1. **BEFURALINE** - Phase 2 antidepressant with serotonergic properties. Top-ranked candidate (100th percentile).
2. **ROXINDOLE** - Phase 2 dopamine agonist with indole structure. Very strong KG signal (99.98th percentile).
3. **SEROTONIN** - Phase 3 compound, direct neurotransmitter involvement. High repurposing potential.

### Known Mechanisms Present
- Serotonergic modulation (Befuraline, Serotonin, Vortioxetine)
- Dopaminergic activity (Roxindole, Dopamine, Pramipexole, Aripiprazole)
- GABA-ergic (Benzodiazepine)
- Mood stabilization (Lithium)
- Natural extracts (Hypericum/St. John's Wort, Remifemin)

### Treatment Relations Used
- DRUGBANK::treats::Compound:Disease
- GNBR::T::Compound:Disease (Treatment)
- Hetionet::CtD::Compound:Disease

---

**Next Steps:**
1. Investigate dropped drugs (especially Befuraline, Roxindole) for safety profile review
2. Examine clinical trial history and reasons for discontinuation
3. Assess molecular targets and pathway overlap with approved antidepressants
4. Consider combination therapy potential
