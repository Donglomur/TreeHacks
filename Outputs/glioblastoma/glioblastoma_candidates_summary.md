# Glioblastoma Drug Candidates - DRKG Discovery Results

**Disease:** Glioblastoma
**Method:** RotatE embeddings
**Compounds Scored:** 24,313
**Candidates Returned:** 30
**Query Time:** 575.6 ms

## Summary Statistics

- **Dropped Drugs:** 6 (candidates that reached Phase I-III but never approved - prime repurposing targets)
- **Novel/Other Compounds:** 24 (compounds in knowledge graph but not in dropped drugs database)
- **Withdrawn Drugs:** 0

---

## Top Candidates (sorted by status, then KG percentile)

### DROPPED DRUGS - Prime Repurposing Candidates

| Rank | Drug Name | Max Phase | KG Percentile | KG Score | SMILES | ChEMBL | DrugBank |
|------|-----------|-----------|---------------|----------|--------|---------|----------|
| 11 | TALAMPANEL | Phase 2 | 99.96 | -11.7475 | CC(=O)N1N=C(c2ccc(N)cc2)c2cc3c(cc2C[C@H]1C)OCO3 | CHEMBL61872 | DB04982 |
| 17 | RIVOCERANIB | Phase 3 | 99.93 | -11.8613 | N#CC1(c2ccc(NC(=O)c3cccnc3NCc3ccncc3)cc2)CCCC1 | CHEMBL3186534 | DB14765 |
| 23 | GENISTEIN | Phase 2 | 99.91 | -11.8821 | O=c1c(-c2ccc(O)cc2)coc2cc(O)cc(O)c12 | CHEMBL44 | DB01645 |
| 24 | EDOTECARIN | Phase 3 | 99.91 | -11.8856 | O=C1c2c(c3c4ccc(O)cc4n([C@@H]4O[C@H](CO)[C@@H](O)[C@H](O)[C@H]4O)c3c3[nH]c4cc(O)ccc4c23)C(=O)N1NC(CO)CO | CHEMBL435191 | DB04882 |
| 25 | CEDIRANIB | Phase 3 | 99.90 | -11.8879 | COc1cc2c(Oc3ccc4[nH]c(C)cc4c3F)ncnc2cc1OCCCN1CCCC1 | CHEMBL491473 | DB04849 |
| 30 | PERIFOSINE | Phase 3 | 99.88 | -11.9366 | CCCCCCCCCCCCCCCCCCOP(=O)([O-])OC1CC[N+](C)(C)CC1 | CHEMBL372764 | DB06641 |

### NOVEL/OTHER COMPOUNDS

| Rank | Drug Name | KG Percentile | KG Score | ChEMBL | DrugBank |
|------|-----------|---------------|----------|---------|----------|
| 1 | AF38469 | 100.00 | -11.5766 | - | - |
| 2 | 4-BORONOPHENYLALANINE | 100.00 | -11.5920 | - | - |
| 3 | SORAFENIB | 99.99 | -11.6020 | - | - |
| 4 | NIMUSTINE HYDROCHLORIDE | 99.99 | -11.6055 | CHEMBL1256616 | - |
| 5 | GEFITINIB | 99.98 | -11.6124 | - | - |
| 6 | ETOPOSIDE | 99.98 | -11.6237 | CHEMBL44657 | DB00773 |
| 7 | TEMOZOLOMIDE | 99.98 | -11.6545 | - | - |
| 8 | ERLOTINIB | 99.97 | -11.6933 | - | - |
| 9 | CISPLATIN | 99.97 | -11.7184 | - | DB00515 |
| 10 | SUNITINIB | 99.96 | -11.7230 | - | - |
| 12 | DOCETAXEL | 99.95 | -11.7542 | - | - |
| 13 | DACOMITINIB | 99.95 | -11.7685 | - | - |
| 14 | TAMOXIFEN | 99.95 | -11.7798 | CHEMBL83 | DB00675 |
| 15 | NAC-SAR-GLY-VAL-(D-ALLO-ILE)-THR-NVA-ILE-ARG-PRONET | 99.94 | -11.7881 | - | - |
| 16 | CAPECITABINE | 99.94 | -11.8562 | - | - |
| 18 | BACILLITHIOL(1-) | 99.93 | -11.8614 | - | - |
| 19 | 5-FLUOROURACIL | 99.93 | -11.8617 | CHEMBL185 | DB00544 |
| 20 | TALAPORFIN | 99.92 | -11.8647 | CHEMBL2111186 | DB11812 |
| 21 | PACLITAXEL | 99.92 | -11.8730 | CHEMBL428647 | DB01229 |
| 22 | DOXORUBICIN | 99.91 | -11.8754 | CHEMBL53463 | DB00997 |
| 26 | RAPAMYCIN | 99.90 | -11.9004 | CHEMBL413 | DB00877 |
| 27 | 4-AMINO-5-FLUORO-3-(5-(4-METHYLPIPERAZIN-1-YL)-1H-BENZIMIDAZOL-2-YL)QUINOLIN-2(1H)-ONE | 99.89 | -11.9117 | - | - |
| 28 | CABOZANTINIB | 99.89 | -11.9281 | CHEMBL2105717 | DB08875 |
| 29 | IFOSFAMIDE | 99.88 | -11.9325 | CHEMBL1024 | DB01181 |

---

## Key Metrics Explained

- **KG Percentile:** Percentile ranking in the knowledge graph (0-100, higher = stronger evidence)
- **KG Score:** Raw RotatE embedding distance (more negative = closer/stronger relationship)
- **KG Z-Score:** Standardized score showing how many standard deviations from mean
- **Status:**
  - **dropped** = reached Phase I-III clinical trials but never approved (prime repurposing candidates)
  - **novel** = in knowledge graph but not in clinical phase database
  - **withdrawn** = previously approved but withdrawn from market

---

**Treatment Relations Used:**
- DRUGBANK::treats::Compound:Disease
- GNBR::T::Compound:Disease
- Hetionet::CtD::Compound:Disease

**Disease Entity:** Disease::MESH:D005909
