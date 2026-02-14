# Glioblastoma Drug Candidates - Knowledge Graph Analysis

## Summary
- **Disease**: glioblastoma
- **Total compounds scored**: 24,313
- **Candidates returned**: 30
- **Method**: RotatE embeddings
- **Analysis time**: 558.2ms

## Candidate Breakdown
- **Dropped** (failed trials, prime repurposing targets): 6
- **Withdrawn**: 0
- **Novel** (not in clinical database): 24

---

## DROPPED DRUGS (Prime Repurposing Candidates)

| Rank | Drug Name | Max Phase | KG Percentile | KG Score | SMILES | ChEMBL | DrugBank |
|------|-----------|-----------|---------------|----------|--------|--------|----------|
| 11 | TALAMPANEL | Phase 2 | 99.96 | -11.75 | CC(=O)N1N=C(c2ccc(N)cc2)c2cc3c(cc2C[C@H]1C)OCO3 | CHEMBL61872 | DB04982 |
| 17 | RIVOCERANIB | Phase 3 | 99.93 | -11.86 | N#CC1(c2ccc(NC(=O)c3cccnc3NCc3ccncc3)cc2)CCCC1 | CHEMBL3186534 | DB14765 |
| 23 | GENISTEIN | Phase 2 | 99.91 | -11.88 | O=c1c(-c2ccc(O)cc2)coc2cc(O)cc(O)c12 | CHEMBL44 | DB01645 |
| 24 | EDOTECARIN | Phase 3 | 99.91 | -11.89 | O=C1c2c(c3c4ccc(O)cc4n([C@@H]4O[C@H](CO)[C@@H](O)[C@H](O)[C@H]4O)c3c3[nH]c4cc(O)ccc4c23)C(=O)N1NC(CO)CO | CHEMBL435191 | DB04882 |
| 25 | CEDIRANIB | Phase 3 | 99.90 | -11.89 | COc1cc2c(Oc3ccc4[nH]c(C)cc4c3F)ncnc2cc1OCCCN1CCCC1 | CHEMBL491473 | DB04849 |
| 30 | PERIFOSINE | Phase 3 | 99.88 | -11.94 | CCCCCCCCCCCCCCCCCCOP(=O)([O-])OC1CC[N+](C)(C)CC1 | CHEMBL372764 | DB06641 |

---

## NOVEL/APPROVED DRUGS

| Rank | Drug Name | KG Percentile | KG Score | ChEMBL | DrugBank |
|------|-----------|---------------|----------|--------|----------|
| 1 | AF38469 | 100.00 | -11.58 | - | - |
| 2 | 4-BORONOPHENYLALANINE | 100.00 | -11.59 | - | - |
| 3 | SORAFENIB | 99.99 | -11.60 | - | - |
| 4 | NIMUSTINE HYDROCHLORIDE | 99.99 | -11.61 | CHEMBL1256616 | - |
| 5 | GEFITINIB | 99.98 | -11.61 | - | - |
| 6 | ETOPOSIDE | 99.98 | -11.62 | CHEMBL44657 | DB00773 |
| 7 | TEMOZOLOMIDE | 99.98 | -11.65 | - | - |
| 8 | ERLOTINIB | 99.97 | -11.69 | - | - |
| 9 | CISPLATIN | 99.97 | -11.72 | - | DB00515 |
| 10 | SUNITINIB | 99.96 | -11.72 | - | - |
| 12 | DOCETAXEL | 99.95 | -11.75 | - | - |
| 13 | DACOMITINIB | 99.95 | -11.77 | - | - |
| 14 | TAMOXIFEN | 99.95 | -11.78 | CHEMBL83 | DB00675 |
| 15 | NAC-SAR-GLY-VAL-(D-ALLO-ILE)-THR-NVA-ILE-ARG-PRONET | 99.94 | -11.79 | - | - |
| 16 | CAPECITABINE | 99.94 | -11.86 | - | - |
| 18 | BACILLITHIOL(1-) | 99.93 | -11.86 | - | - |
| 19 | 5-FLUOROURACIL | 99.93 | -11.86 | CHEMBL185 | DB00544 |
| 20 | TALAPORFIN | 99.92 | -11.86 | CHEMBL2111186 | DB11812 |
| 21 | PACLITAXEL | 99.92 | -11.87 | CHEMBL428647 | DB01229 |
| 22 | DOXORUBICIN | 99.91 | -11.88 | CHEMBL53463 | DB00997 |
| 26 | RAPAMYCIN | 99.90 | -11.90 | CHEMBL413 | DB00877 |
| 27 | 4-AMINO-5-FLUORO-3-(5-(4-METHYLPIPERAZIN-1-YL)-1H-BENZIMIDAZOL-2-YL)QUINOLIN-2(1H)-ONE | 99.89 | -11.91 | - | - |
| 28 | CABOZANTINIB | 99.89 | -11.93 | CHEMBL2105717 | DB08875 |
| 29 | IFOSFAMIDE | 99.88 | -11.93 | CHEMBL1024 | DB01181 |

---

## Notes
- **KG Percentile**: Higher = stronger evidence in knowledge graph (0-100 scale)
- **KG Score**: RotatE embedding distance score (more negative = stronger relationship)
- **Dropped drugs**: Reached Phase I-III but never approved - prime candidates for repurposing
- **Novel drugs**: Not found in clinical trial database - may be approved, experimental, or natural compounds
- **SMILES**: Molecular structure notation preserved for downstream analysis
