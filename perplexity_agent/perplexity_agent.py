import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Optional
import httpx
import re
logger = logging.getLogger(__name__)

@dataclass
class DrugResearchReport:
    drug_name: str
    disease: str
    mechanism: str
    evidence: str
    regulatory: str
    recent_developments: str
    all_citations: list[str]
    citation_count: int
    evidence_level: str
    recommendation: str
    key_findings: list[str]
    safety_notes: str
    total_cost_estimate: float

class SonarClient:
    """Async Perplexity Sonar client with retry logic."""
    def __init__(self, api_key, model="sonar-pro", timeout=30, max_retries=3):
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.biomedical_domains = [
        "pubmed.ncbi.nlm.nih.gov", "clinicaltrials.gov",
        "fda.gov", "drugbank.com", "nature.com", "nejm.org",
        "biorxiv.org", "medrxiv.org", "nih.gov", "who.int",
        ]
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def search(self, query, system_prompt=None, domain_filter=None, recency=None):
        if not system_prompt:
            system_prompt = (
            "You are a pharmaceutical research specialist. Provide "
            "detailed, evidence-based answers with specific citations."
            )
        payload = {
            "model": self.model,
            "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        }
        if domain_filter:
            payload["search_domain_filter"] = domain_filter[:10]
        if recency:
            payload["search_recency_filter"] = recency
        for attempt in range(self.max_retries):
            try:
                # async with httpx.AsyncClient() as client:
                resp = await self.client.post(
                    self.base_url,
                    headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.timeout,
                )
                if resp.status_code == 429:
                    await asyncio.sleep((2 ** attempt) * 3)
                    continue
                resp.raise_for_status()
                data = resp.json()
                return {
                        "answer": data["choices"][0]["message"]["content"],
                        "citations": data.get("citations", []),
                        "usage": data.get("usage", {}),
                    }
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

class EvidenceClassification:
    @staticmethod
    def classify(mechanism, evidence, regulatory):
        combined = f"{mechanism} {evidence} {regulatory}".lower()
        score = 0
        # Strong indicators (+3 each)
        strong = ["randomized controlled trial", "phase iii", "phase 3",
        "meta-analysis", "fda approved", "statistically significant"]
        for p in strong:
            if p in combined:
                score += 3
        # Moderate indicators (+2 each)
        moderate = ["phase ii", "phase 2", "case series", "preclinical",
        "animal model", "pilot study", "observational study"]
        for p in moderate:
            if p in combined:
                score += 2
        # Weak indicators (+1 each)
        weak = ["in vitro", "cell line", "theoretical", "pathway", "hypothesis"]
        for p in weak:
            if p in combined:
                score += 1
        # Negative indicators (-2 each)
        negative = ["no benefit", "failed to show", "no evidence", "withdrawn"]
        for p in negative:
            if p in combined:
                score -= 2
        if score >= 6: return "STRONG"
        elif score >= 3: return "MODERATE"
        elif score >= 1: return "WEAK"
        elif score <= -2: return "NONE"
        else: return "UNKNOWN"

class SonarResearchAgent:
    """Agent 4: 4-query biomedical research pipeline."""
    def __init__(self, api_key, model="sonar-pro"):
        self.client = SonarClient(api_key=api_key, model=model)
        self.classifier = EvidenceClassification()

    async def research_drug_disease(self, drug_name, disease_name):
        """Run the full 4-query pipeline."""
        # Query 1: Mechanism
        mech = await self.client.search(
        f"What is the mechanism of action of {drug_name} and how "
        f"might it be relevant to treating {disease_name}?",
        domain_filter=self.client.biomedical_domains,
        )
        await asyncio.sleep(0.5)

        # Query 2: Evidence
        evid = await self.client.search(
            f"How has {drug_name} been studied for {disease_name}? Find "
            f"clinical trials (NCT numbers), case reports, preclinical data about repurposing {drug_name} for {disease_name}.",
            domain_filter=self.client.biomedical_domains,
        )
        await asyncio.sleep(0.5)

        # key_findings = []
        # for line in evid["answer"].split("\n"):
        #     line_clean = line.strip("-• ").strip()
        #     if not line_clean:
        #         continue
        
        #     if any(k in line_clean.lower() for k in ["phase ii", "phase iii", "nct", "case report", "preclinical", "mouse model", "animal model"]):
        #         key_findings.append(line_clean)
        key_findings = []

        for line in evid["answer"].split("\n"):
            line_clean = line.strip("-• ").strip()

            if not line_clean:
                continue

            if line_clean.startswith("|"):
                continue

            if "nct number" in line_clean.lower():
                continue

            if set(line_clean) <= {"-", "|", " "}:
                continue

            if line_clean.lower().startswith("clinical trials"):
                continue

            if any(k in line_clean.lower() for k in [
                "phase ii",
                "phase iii",
                "nct",
                "case report",
                "preclinical",
                "mouse model",
                "animal model"
            ]):
                key_findings.append(line_clean)


        # Query 3: Regulatory
        reg = await self.client.search(
            f"Patent and regulatory status of {drug_name}? Generic "
            f"availability? Safety warnings? Max clinical phase reached?",
            domain_filter=["fda.gov", "drugbank.com", "nih.gov"],
        )
        await asyncio.sleep(0.5)

        safety_notes = []
        for line in reg["answer"].split("\n"):
            line_clean = line.strip("-• ").strip()
            if any(k in line_clean.lower() for k in ["black box", "contraindicated", "adverse", "warning", "toxicity"]):
                safety_notes.append(line_clean)
        safety_notes = " | ".join(safety_notes)

        # Query 4: Recent
        recent = await self.client.search(
            f"Latest 2024-2026 developments for {drug_name}, especially "
            f"related to {disease_name}, including new clinical trials, FDA decision, conference proceedings.",
            recency="month",
        )

        # Aggregate citations
        all_citations = set()
        for r in [mech, evid, reg, recent]:
            all_citations.update(r["citations"])

        # Classify evidence
        level = EvidenceClassification.classify(
            mech["answer"], evid["answer"], reg["answer"]
        )

        if level == "STRONG":
            recommendation = "PURSUE"
        elif level == "MODERATE":
            recommendation = "INVESTIGATE_FURTHER"
        else:
            recommendation = "DEPRIORITIZE"
        
        # Cost estimate
        total_tokens = sum(
            r["usage"].get("total_tokens", 0)
            for r in [mech, evid, reg, recent]
        )

        return DrugResearchReport(
            drug_name=drug_name,
            disease=disease_name,
            mechanism=mech["answer"],
            evidence=evid["answer"],
            regulatory=reg["answer"],
            recent_developments=recent["answer"],
            all_citations=sorted(all_citations),
            citation_count=len(all_citations),
            evidence_level=level,
            recommendation=recommendation,
            key_findings=key_findings[:5],
            safety_notes=safety_notes,
            total_cost_estimate=round(total_tokens * 5e-6, 4),
        )
    
    async def batch_research(self, candidates, max_concurrent=2):
        """Research multiple candidates with rate limiting."""
        sem = asyncio.Semaphore(max_concurrent)
        async def limited(drug, disease):
            async with sem:
                try:
                    return await self.research_drug_disease(drug, disease)
                except Exception as e:
                    logger.error(f"Research failed: {drug} → {disease}: {e}")
                    return None
                
        tasks = [limited(c["drug_name"], c["disease"]) for c in candidates]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]
    
import os
import argparse

async def main():
    # api_key = os.getenv("PERPLEXITY_API_KEY")

    # agent = SonarResearchAgent(api_key=api_key)

    # report = await agent.research_drug_disease(
    #     drug_name="Metformin",
    #     disease_name="Alzheimer's disease"
    # )
    parser = argparse.ArgumentParser(description="Run drug-disease research")
    parser.add_argument("--drug", type=str, required=True, help="Drug name")
    parser.add_argument("--disease", type=str, required=True, help="Disease name")
    args = parser.parse_args()

    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise ValueError("Please set the PERPLEXITY_API_KEY environment variable")

    agent = SonarResearchAgent(api_key=api_key)

    report = await agent.research_drug_disease(
        drug_name=args.drug,
        disease_name=args.disease
    )

    print("\n=== RESULT ===")
    print("Drug:", report.drug_name)
    print("Disease:", report.disease)
    print("Evidence Level:", report.evidence_level)
    print("Recommendation:", report.recommendation)
    print("Citations:", report.citation_count)
    print("Cost Estimate:", report.total_cost_estimate)
    
    import re

    def clean_markdown(text):
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
        text = re.sub(r"###\s*", "", text)
        text = re.sub(r"\[\d+\]", "", text)
        text = re.sub(r"\s{2,}", " ", text)
        return text.strip()

    print("\nKey Findings:")
    for i, finding in enumerate(report.key_findings, 1):
        print(f"{i}. {clean_markdown(finding)}")

    print("\nSafety Notes:")
    for note in report.safety_notes.split(" | "):
        print(f"- {clean_markdown(note)}")


if __name__ == "__main__":
    asyncio.run(main())
