# DrugRescue AI

> AI-powered drug repurposing agent — TreeHacks 2026

Built with the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python)

## What It Does

Give it a disease. It scores all ~24,000 compounds in the DRKG biomedical
knowledge graph using trained RotatE embeddings, cross-references a database
of dropped clinical trials, and returns ranked repurposing candidates.

## Project Structure

```
TreeHacks/                          ← repo root (you are here)
├── pyproject.toml
├── .gitignore
├── .env.example
├── README.md
├── test_drugrescue.py
├── scripts/
│   └── download_data.py
├── data/                           ← your 9 Modal files (gitignored)
│   ├── embeddings/
│   ├── database/
│   ├── fingerprints/
│   └── models/
└── src/
    └── drug_rescue/                ← the Python package
        ├── __init__.py
        ├── __main__.py
        ├── agent.py
        ├── engines/
        │   ├── __init__.py
        │   ├── scorer.py
        │   └── discover.py
        ├── tools/
        │   ├── __init__.py
        │   └── kg_discovery.py
        └── prompts/
            ├── __init__.py
            └── system.py
```

## Data Setup

```bash
mkdir -p data/{embeddings,fingerprints,models,database}
cp rotate_entity_embeddings.npy rotate_relation_embeddings.npy \
   entity_to_idx.json relation_to_idx.json        data/embeddings/
cp morgan_fps.npy fp_drug_index.json               data/fingerprints/
cp metadata.json trained_model.pt                   data/models/
cp dropped_drugs.db                                 data/database/
```

## Install & Run

```bash
pip install -e .

# Standalone — runs KG tool directly, no Claude needed
python -m drug_rescue --disease glioblastoma --standalone

# Full agent — Claude reasons + uses tools
pip install -e ".[agent]"
python -m drug_rescue --disease glioblastoma

# Interactive chat
python -m drug_rescue
```

## License

MIT — TreeHacks 2026
