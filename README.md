# TreeHacks - FAERS Agent

This repository contains a production-style FAERS inverse-signal detector for drug repurposing.

## What it does

Given a disease and candidate drugs, it queries OpenFDA FAERS data and computes per drug-event:

- 2x2 contingency table (`a,b,c,d`)
- Reporting Odds Ratio (ROR)
- 95% confidence interval
- inverse signal flag (`ROR < 1` and `CI_upper < 1`)
- normalized score for downstream multi-agent consensus

It supports:

- Dynamic total FAERS report count retrieval (`count=receivedate`)
- Async OpenFDA calls with retry/backoff
- Query caching
- Disease -> MedDRA expansion
- Multiple testing correction (`none`, `bonferroni`, `fdr`)
- Claude SDK-compatible tool wrapper

## Project layout

- `faers_agent/client.py`: OpenFDA client
- `faers_agent/stats.py`: ROR/CI/stat functions
- `faers_agent/detector.py`: batch screening orchestrator
- `faers_agent/agent.py`: Claude tool wrapper
- `faers_agent/mappings.py`: disease/MedDRA map
- `main.py`: CLI entrypoint
- `tests/`: unit tests

## Run with uv

Install `uv` first (see: https://docs.astral.sh/uv/getting-started/installation/), then verify:

```bash
uv --version
```

Sync dependencies:

```bash
uv sync --dev
```

Set your OpenFDA API key (optional but recommended):

```bash
export OPENFDA_API_KEY="your_api_key_here"
```

Run the CLI:

```bash
uv run python main.py \
  --disease alzheimer \
  --drugs metformin atorvastatin simvastatin \
  --api-key "$OPENFDA_API_KEY" \
  --correction fdr
```

JSON output:

```bash
uv run python main.py --disease cancer --drugs metformin --json
```

Run tests:

```bash
uv run pytest -q
```

## Claude integration

Use `ClaudeFAERSAgent.tool_definition()` to register a tool in your orchestrator.
Route tool calls to `await ClaudeFAERSAgent.handle_tool_call(name, tool_input)`.

Tool name:

- `faers_inverse_signal_detector`

Input schema fields:

- `disease` (string, required)
- `candidate_drugs` (array[string], required)
- `disease_events` (array[string], optional)
- `alpha` (number, default `0.05`)
- `correction` (`none|bonferroni|fdr`, default `none`)

## Notes

- OpenFDA rate limits are much better with an API key.
- FAERS inverse signals are hypothesis-generating, not causal proof.
