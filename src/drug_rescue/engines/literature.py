"""
Perplexity Sonar Literature Research Engine
=============================================
TreeHacks 2026

4-query biomedical research pipeline:
    1. Mechanism of action + disease relevance
    2. Clinical/preclinical evidence (trials, case reports, animal models)
    3. Regulatory/patent/safety status
    4. Recent developments (2024-2026)

Aggregates citations across all queries, classifies evidence strength via
weighted keyword scoring, extracts key findings and safety notes, tracks
token usage and cost.

Originally by teammate, refactored: httpx → stdlib urllib, single file.

Usage:
    from drug_rescue.engines.literature import LiteratureEngine

    engine = LiteratureEngine(api_key="pplx-...")
    report = await engine.research("metformin", "glioblastoma")
    print(report.evidence_level, report.recommendation)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Optional, Sequence

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MODELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class DrugResearchReport:
    """Structured output from the 4-query research pipeline."""

    drug_name: str
    disease: str
    mechanism: str
    evidence: str
    regulatory: str
    recent_developments: str
    all_citations: list[str] = field(default_factory=list)
    citation_count: int = 0
    evidence_level: str = "UNKNOWN"   # STRONG / MODERATE / WEAK / NONE / UNKNOWN
    recommendation: str = "UNKNOWN"   # PURSUE / INVESTIGATE_FURTHER / DEPRIORITIZE
    key_findings: list[str] = field(default_factory=list)
    safety_notes: str = ""
    total_cost_estimate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EVIDENCE CLASSIFICATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def classify_evidence(mechanism: str, evidence: str, regulatory: str) -> str:
    """
    Weighted keyword scoring across all Perplexity responses.

    +3: RCTs, Phase III, meta-analyses, FDA approval
    +2: Phase II, case series, animal models, pilot studies
    +1: In vitro, pathway analysis, theoretical
    -2: Negative results (no benefit, failed, withdrawn)

    ≥6 → STRONG, ≥3 → MODERATE, ≥1 → WEAK, ≤-2 → NONE
    """
    combined = f"{mechanism} {evidence} {regulatory}".lower()
    score = 0

    strong = [
        "randomized controlled trial", "phase iii", "phase 3",
        "meta-analysis", "fda approved", "statistically significant",
    ]
    for p in strong:
        if p in combined:
            score += 3

    moderate = [
        "phase ii", "phase 2", "case series", "preclinical",
        "animal model", "pilot study", "observational study",
        "retrospective", "cohort study",
    ]
    for p in moderate:
        if p in combined:
            score += 2

    weak = [
        "in vitro", "cell line", "theoretical", "pathway",
        "hypothesis", "computational", "molecular docking",
    ]
    for p in weak:
        if p in combined:
            score += 1

    negative = [
        "no benefit", "failed to show", "no evidence",
        "withdrawn", "terminated", "no significant difference",
    ]
    for p in negative:
        if p in combined:
            score -= 2

    if score >= 6:
        return "STRONG"
    elif score >= 3:
        return "MODERATE"
    elif score >= 1:
        return "WEAK"
    elif score <= -2:
        return "NONE"
    return "UNKNOWN"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ASYNC PERPLEXITY CLIENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"

BIOMEDICAL_DOMAINS = [
    "pubmed.ncbi.nlm.nih.gov", "clinicaltrials.gov",
    "fda.gov", "drugbank.com", "nature.com", "nejm.org",
    "biorxiv.org", "medrxiv.org", "nih.gov", "who.int",
]


class SonarClient:
    """Async Perplexity Sonar client with retry logic. Zero external deps."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "sonar-pro",
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or os.environ.get("PERPLEXITY_API_KEY", "")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    async def search(
        self,
        query: str,
        system_prompt: str | None = None,
        domain_filter: list[str] | None = None,
        recency: str | None = None,
    ) -> dict[str, Any]:
        """
        Single Perplexity Sonar query with retry logic.

        Returns: {"answer": str, "citations": list[str], "usage": dict}
        """
        if not system_prompt:
            system_prompt = (
                "You are a pharmaceutical research specialist. Provide "
                "detailed, evidence-based answers with specific citations."
            )

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            "temperature": 0.1,
            "max_tokens": 2500,
            "stream": False,
        }
        if domain_filter:
            payload["search_domain_filter"] = domain_filter[:10]
        if recency:
            payload["search_recency_filter"] = recency

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(self.max_retries):
            try:
                result = await asyncio.to_thread(
                    self._blocking_post, headers, payload,
                )
                if result.get("_status") == 429:
                    await asyncio.sleep((2 ** attempt) * 3)
                    continue
                if "_error" in result:
                    raise RuntimeError(result["_error"])
                return result
            except Exception:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        return {"answer": "", "citations": [], "usage": {}}

    def _blocking_post(
        self,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Synchronous HTTP POST via stdlib urllib."""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            PERPLEXITY_URL,
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            try:
                from drug_rescue.tools._http import _urlopen_with_ssl_retry
                resp_ctx = _urlopen_with_ssl_retry(req, timeout=self.timeout)
            except ImportError:
                resp_ctx = urllib.request.urlopen(req, timeout=self.timeout, context=ssl.create_default_context())
            with resp_ctx as resp:
                body = json.loads(resp.read().decode())
            return {
                "answer": body["choices"][0]["message"]["content"],
                "citations": body.get("citations", []),
                "usage": body.get("usage", {}),
            }
        except urllib.error.HTTPError as e:
            if e.code == 429:
                return {"_status": 429, "answer": "", "citations": [], "usage": {}}
            body = e.read().decode("utf-8", errors="replace")[:500]
            return {"_error": f"Perplexity HTTP {e.code}: {body}"}
        except Exception as e:
            return {"_error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FINDINGS / SAFETY EXTRACTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FINDING_KEYWORDS = [
    "phase ii", "phase iii", "phase 2", "phase 3",
    "nct", "case report", "preclinical",
    "mouse model", "animal model", "xenograft",
    "clinical trial", "randomized",
]

SAFETY_KEYWORDS = [
    "black box", "contraindicated", "adverse",
    "warning", "toxicity", "hepatotoxicity",
    "cardiotoxicity", "nephrotoxicity",
]


def _extract_key_findings(evidence_text: str, max_findings: int = 5) -> list[str]:
    """Pull lines mentioning trials, NCT numbers, animal models, etc."""
    findings = []
    for line in evidence_text.split("\n"):
        clean = line.strip("-•* ").strip()
        if not clean:
            continue
        # Skip markdown table artifacts
        if clean.startswith("|") or set(clean) <= {"-", "|", " "}:
            continue
        if clean.lower().startswith("clinical trials"):
            continue
        if "nct number" in clean.lower():
            continue

        if any(k in clean.lower() for k in FINDING_KEYWORDS):
            findings.append(clean)

    return findings[:max_findings]


def _extract_safety_notes(regulatory_text: str) -> str:
    """Pull safety warnings from regulatory response."""
    notes = []
    for line in regulatory_text.split("\n"):
        clean = line.strip("-•* ").strip()
        if any(k in clean.lower() for k in SAFETY_KEYWORDS):
            notes.append(clean)
    return " | ".join(notes)


def _clean_markdown(text: str) -> str:
    """Strip markdown formatting for plain text output."""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"###\s*", "", text)
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class LiteratureEngine:
    """
    4-query biomedical literature research pipeline via Perplexity Sonar.

    Query 1 — Mechanism of action + disease pathway relevance
    Query 2 — Clinical/preclinical evidence (trials, NCTs, case reports)
    Query 3 — Regulatory + patent + safety status
    Query 4 — Recent developments (2024-2026)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "sonar-pro",
        max_concurrent: int = 2,
    ) -> None:
        self.client = SonarClient(api_key=api_key, model=model)
        self.max_concurrent = max_concurrent

    async def research(
        self,
        drug_name: str,
        disease: str,
    ) -> DrugResearchReport:
        """Run the full 4-query pipeline for one drug × disease pair."""

        # Query 1: Mechanism
        mech = await self.client.search(
            f"What is the mechanism of action of {drug_name} and how "
            f"might it be relevant to treating {disease}?",
            domain_filter=BIOMEDICAL_DOMAINS,
        )
        await asyncio.sleep(0.5)

        # Query 2: Evidence
        evid = await self.client.search(
            f"How has {drug_name} been studied for {disease}? Find "
            f"clinical trials (NCT numbers), case reports, preclinical "
            f"data about repurposing {drug_name} for {disease}.",
            domain_filter=BIOMEDICAL_DOMAINS,
        )
        await asyncio.sleep(0.5)

        # Query 3: Regulatory / Safety
        reg = await self.client.search(
            f"Patent and regulatory status of {drug_name}? Generic "
            f"availability? Safety warnings? Max clinical phase reached?",
            domain_filter=["fda.gov", "drugbank.com", "nih.gov"],
        )
        await asyncio.sleep(0.5)

        # Query 4: Recent developments
        recent = await self.client.search(
            f"Latest 2024-2026 developments for {drug_name}, especially "
            f"related to {disease}, including new clinical trials, FDA "
            f"decisions, conference proceedings.",
            recency="month",
        )

        # Aggregate citations
        all_citations = set()
        for r in [mech, evid, reg, recent]:
            all_citations.update(r.get("citations", []))

        # Classify evidence
        level = classify_evidence(
            mech["answer"], evid["answer"], reg["answer"],
        )
        if level == "STRONG":
            recommendation = "PURSUE"
        elif level == "MODERATE":
            recommendation = "INVESTIGATE_FURTHER"
        else:
            recommendation = "DEPRIORITIZE"

        # Extract structured data
        key_findings = _extract_key_findings(evid["answer"])
        safety_notes = _extract_safety_notes(reg["answer"])

        # Cost estimate (Sonar Pro ≈ $5/M tokens)
        total_tokens = sum(
            r.get("usage", {}).get("total_tokens", 0)
            for r in [mech, evid, reg, recent]
        )

        return DrugResearchReport(
            drug_name=drug_name,
            disease=disease,
            mechanism=mech["answer"],
            evidence=evid["answer"],
            regulatory=reg["answer"],
            recent_developments=recent["answer"],
            all_citations=sorted(all_citations),
            citation_count=len(all_citations),
            evidence_level=level,
            recommendation=recommendation,
            key_findings=key_findings,
            safety_notes=safety_notes,
            total_cost_estimate=round(total_tokens * 5e-6, 4),
        )

    async def batch_research(
        self,
        candidates: Sequence[dict[str, str]],
        max_concurrent: int | None = None,
    ) -> list[DrugResearchReport]:
        """
        Research multiple drug-disease pairs with rate limiting.

        Each entry: {"drug_name": "metformin", "disease": "glioblastoma"}
        """
        sem = asyncio.Semaphore(max_concurrent or self.max_concurrent)

        async def limited(drug: str, disease: str) -> DrugResearchReport | None:
            async with sem:
                try:
                    return await self.research(drug, disease)
                except Exception as e:
                    logger.error("Research failed: %s → %s: %s", drug, disease, e)
                    return None

        tasks = [
            limited(c["drug_name"], c["disease"])
            for c in candidates
        ]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]
