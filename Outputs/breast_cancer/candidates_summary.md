# Drug Rescue Candidates for Breast Cancer

**Discovery Method:** RotatE embeddings on DRKG knowledge graph
**Total Compounds Scored:** 24,313
**Candidates Returned:** 30
**Min Percentile:** 75.0
**Discovery Time:** 629ms

## Candidate Statistics
- **Dropped (Phase I-III, never approved):** 0
- **Withdrawn:** 0
- **Novel (not in clinical database):** 30

## Top Candidates

| Rank | Drug Name | Status | KG Percentile | KG Score | Z-Score | DrugBank ID | ChEMBL ID |
|------|-----------|--------|---------------|----------|---------|-------------|-----------|
| 1 | DOXORUBICIN | novel | 100.0 | -10.08 | 7.21 | DB00997 | CHEMBL53463 |
| 2 | ETOPOSIDE | novel | 100.0 | -10.28 | 6.85 | DB00773 | CHEMBL44657 |
| 3 | DAUNORUBICIN | novel | 99.99 | -10.37 | 6.69 | DB00694 | CHEMBL178 |
| 4 | MITOXANTRONE | novel | 99.99 | -10.39 | 6.66 | DB01204 | CHEMBL58 |
| 5 | EPIRUBICIN | novel | 99.98 | -10.48 | 6.49 | DB00445 | CHEMBL417 |
| 6 | DACTINOMYCIN | novel | 99.98 | -10.50 | 6.46 | DB00970 | CHEMBL1554 |
| 7 | TOPOTECAN | novel | 99.98 | -10.53 | 6.41 | DB01030 | CHEMBL84 |
| 8 | FULVESTRANT | novel | 99.97 | -10.53 | 6.40 | DB00947 | CHEMBL1358 |
| 9 | EXEMESTANE | novel | 99.97 | -10.69 | 6.12 | DB00990 | CHEMBL1200374 |
| 10 | PACLITAXEL | novel | 99.96 | -10.73 | 6.04 | DB01229 | CHEMBL428647 |
| 11 | RAPAMYCIN | novel | 99.96 | -10.74 | 6.04 | DB00877 | CHEMBL413 |
| 12 | TAMOXIFEN | novel | 99.95 | -10.75 | 6.02 | DB00675 | CHEMBL83 |
| 13 | IDARUBICIN | novel | 99.95 | -10.76 | 6.00 | DB01177 | CHEMBL1117 |
| 14 | TEMOZOLOMIDE | novel | 99.95 | -10.82 | 5.89 | DB00853 | CHEMBL810 |
| 15 | DASATINIB | novel | 99.94 | -10.83 | 5.88 | DB01254 | CHEMBL1421 |
| 16 | METHOTREXATE | novel | 99.94 | -10.84 | 5.85 | DB00563 | CHEMBL34259 |
| 17 | IRINOTECAN | novel | 99.93 | -10.85 | 5.84 | DB00762 | CHEMBL481 |
| 18 | DOCETAXEL | novel | 99.93 | -10.85 | 5.83 | DB01248 | CHEMBL92 |
| 19 | MELPHALAN | novel | 99.93 | -10.85 | 5.83 | DB01042 | CHEMBL852 |
| 20 | VINORELBINE | novel | 99.92 | -10.87 | 5.80 | DB00361 | CHEMBL553025 |
| 21 | CAPECITABINE | novel | 99.92 | -10.87 | 5.80 | DB01101 | CHEMBL1773 |
| 22 | NILOTINIB | novel | 99.91 | -10.88 | 5.78 | DB04868 | CHEMBL255863 |
| 23 | LETROZOLE | novel | 99.91 | -10.88 | 5.78 | DB01006 | CHEMBL1444 |
| 24 | LENALIDOMIDE | novel | 99.91 | -10.92 | 5.71 | DB00480 | CHEMBL848 |
| 25 | VINBLASTINE | novel | 99.9 | -10.94 | 5.67 | DB00570 | CHEMBL159 |
| 26 | RALOXIFENE | novel | 99.9 | -10.95 | 5.67 | DB00481 | CHEMBL81 |
| 27 | ESTRADIOL | novel | 99.89 | -10.95 | 5.66 | DB00783 | CHEMBL135 |
| 28 | TOREMIFENE | novel | 99.89 | -10.95 | 5.66 | DB00539 | CHEMBL1655 |
| 29 | GEMCITABINE | novel | 99.88 | -10.98 | 5.61 | DB00441 | CHEMBL888 |
| 30 | 5-AZACYTIDINE | novel | 99.88 | -10.98 | 5.61 | DB00928 | CHEMBL1489 |

## Notes
- **Status "novel"**: Compound exists in DRKG but not found in the dropped_drugs clinical database
- **KG Percentile**: Higher values indicate stronger graph-based evidence (0-100 scale)
- **KG Score**: RotatE embedding distance (lower/more negative = stronger predicted relationship)
- **Z-Score**: Statistical significance of the graph relationship
- All candidates meet minimum percentile threshold of 75.0

## Next Steps
These candidates should be further evaluated with:
1. Clinical trials analysis
2. Safety profile assessment (FAERS)
3. Literature evidence review
4. Molecular docking studies
5. Structural similarity analysis
