"""Disease-to-MedDRA mapping used for FAERS search expansion."""

DISEASE_TO_MEDDRA = {
    "glioblastoma": [
        "Glioblastoma",
        "Glioblastoma multiforme",
        "Brain neoplasm malignant",
        "Brain cancer",
    ],
    "alzheimer": [
        "Alzheimer's disease",
        "Dementia",
        "Dementia Alzheimer's type",
        "Cognitive disorder",
        "Memory impairment",
    ],
    "cancer": [
        "Neoplasm malignant",
        "Metastasis",
        "Cancer pain",
    ],
    "parkinson": [
        "Parkinson's disease",
        "Tremor",
        "Bradykinesia",
    ],
}


def resolve_disease_terms(disease: str, override_terms=None):
    if override_terms:
        return list(dict.fromkeys(t.strip() for t in override_terms if t and t.strip()))
    terms = DISEASE_TO_MEDDRA.get(disease.lower().strip())
    if terms:
        return terms
    return [disease]
