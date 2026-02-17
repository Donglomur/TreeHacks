# RescueRX 
** How many drugs have been shelved that could save lives for diseases they were never tested on? We use AI to find drugs abandoned for business reasons & pinpoint diseases they're best suited to fight. **

🏆 **Winner — Best Use of Clinical Information in TreeHacks 2026**

## What It Does

Give it a disease. It scores all ~24,000 compounds in the DRKG biomedical
knowledge graph using trained RotatE embeddings, cross-references a database
of dropped clinical trials, and returns ranked repurposing candidates.
---

## Overview

**RescueRX** is a multi-agent drug repurposing system that finds **high-potential, previously-shelved drugs** for a target disease and explains *why* they’re worth pursuing.

It combines:
- **Knowledge graph discovery** (biological plausibility)
- **Clinical trials scanning** (why drugs were dropped)
- **Real-world safety signals** (FAERS inverse signals)
- **Literature grounding** (citations-backed mechanisms)
- **Molecular confirmation** (fingerprints + optional docking)
- **Adversarial “evidence court”** (Advocate vs Skeptic → Judge verdict)

The result is a **ranked list of candidates** with **tiered confidence**, safety considerations, and transparent reasoning clinicians can inspect.

---

## How It Works (3 Layers • 9 Agents)

### Layer 1 — Discovery
1) **Knowledge Graph Agent**: scores drugs vs. the disease using learned graph embeddings (RotatE-style scoring)

### Layer 2 — Evidence Wall (runs in parallel)
2) **Trial Scanner**: queries ClinicalTrials.gov for terminated/withdrawn trials and classifies whether failure was *scientific* vs *non-scientific*  
3) **FAERS Inverse Signal Agent**: asks “what does this drug *prevent*?” via reporting odds ratios  
4) **Literature Agent**: produces citation-backed mechanism + prior evidence summaries  
5) **Molecular Similarity Agent**: Morgan fingerprints + Tanimoto similarity vs known treatments  
6) **Safety Arbitration**: excludes candidates with strong risk signals / contraindication concerns

### Layer 3 — Adversarial Court
7) **Advocate**: best case *for* rescuing the drug  
8) **Skeptic**: best case *against* rescuing the drug  
9) **Judge**: weighs both sides → assigns a final **Rescue Score** and recommended next steps

---
Built with ❤️ during TreeHacks 2026
