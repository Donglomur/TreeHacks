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

## HTTP API (Frontend Integration)

Install API dependencies:

```bash
pip install -e ".[api,agent]"
```

Run the backend API:

```bash
PYTHONPATH=src uvicorn drug_rescue.server:app --reload --port 8000
```

Alternative (explicit env file loading via uvicorn):

```bash
PYTHONPATH=src uvicorn drug_rescue.server:app --reload --port 8000 --env-file .env
```

Environment variables:

- `DRUGRESCUE_PRECOMPUTED_ROOT` (default: `files`)
- `DRUGRESCUE_ALLOW_LIVE_FALLBACK` (default: `true`)
- `DRUGRESCUE_DEFAULT_CONVERSATION_ID` (default: `c_123`)
- `DRUGRESCUE_CORS_ORIGINS` (optional, e.g. `http://localhost:3000`)

Endpoints:

- `GET /health`
- `GET /v1/artifacts?disease=glioblastoma&subtype=...`
- `POST /v1/chat`

## Next.js Route Proxy Example

In your separate frontend repo, your route handler can proxy directly:

```ts
import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.DRUGRESCUE_API_BASE_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  const disease = request.nextUrl.searchParams.get("disease") || "glioblastoma";
  const subtype = request.nextUrl.searchParams.get("subtype") || "";
  const url = new URL(`${API_BASE}/v1/artifacts`);
  url.searchParams.set("disease", disease);
  if (subtype) url.searchParams.set("subtype", subtype);

  const resp = await fetch(url.toString(), { cache: "no-store" });
  const data = await resp.json();
  return NextResponse.json(data, { status: resp.status });
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const resp = await fetch(`${API_BASE}/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  const data = await resp.json();
  return NextResponse.json(data, { status: resp.status });
}
```

## License

MIT — TreeHacks 2026
