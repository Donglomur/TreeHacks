"""
FAERS Inverse Signal Detection Engine
=======================================
TreeHacks 2026

Single-file engine that screens drugs against diseases in FDA FAERS.

Detects inverse signals (drug associated with FEWER symptom reports than
expected) using Reporting Odds Ratio (ROR) with proper statistical testing.

Built from teammate's async OpenFDA client with:
    - Multi-variant drug query resolution (generic_name, medicinalproduct,
      substance_name — picks highest-count match)
    - Response caching (same query never hits API twice)
    - Exponential backoff on 429s with configurable retries
    - SSL cert fallback via certifi / env vars
    - Semaphore-controlled concurrent API calls
    - One-sided p-values + Bonferroni / BH-FDR multiple testing correction
    - Normalized scoring (0-1) for orchestrator integration

Usage:
    from drug_rescue.engines.faers import FAERSEngine

    engine = FAERSEngine(api_key="...")
    result = await engine.screen(
        drugs=["metformin", "aspirin"],
        disease="glioblastoma",
    )
    for sig in result.inverse_signals:
        print(sig.drug, sig.event, sig.ror, sig.interpretation)
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any, Optional, Sequence

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MODELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class InverseSignal:
    """One drug × event pair analysis result."""

    drug: str
    event: str
    a: int                          # reports with BOTH drug AND event
    b: int                          # reports with drug, NOT event
    c: int                          # reports with event, NOT drug
    d: int                          # reports with NEITHER
    total_faers: int
    drug_total_reports: int         # a + b
    event_total_reports: int        # a + c
    report_count: int               # = a
    ror: float | None = None
    ci_lower: float | None = None
    ci_upper: float | None = None
    p_value: float | None = None
    q_value: float | None = None    # BH-adjusted p-value
    is_inverse_signal: bool = False
    is_positive_signal: bool = False
    insufficient_data: bool = False
    protection_pct: float = 0.0     # (1 - ROR) * 100 when ROR < 1
    interpretation: str = ""
    normalized_score: float = 0.0   # 0-1 for orchestrator

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScreeningResult:
    """Full screening output for one disease query."""

    disease: str
    events: list[str]
    total_faers: int
    tests_run: int
    correction_method: str
    alpha: float
    corrected_alpha: float
    by_pair: list[InverseSignal] = field(default_factory=list)
    inverse_signals: list[InverseSignal] = field(default_factory=list)
    strongest_by_drug: list[InverseSignal] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "disease": self.disease,
            "events": self.events,
            "total_faers": self.total_faers,
            "tests_run": self.tests_run,
            "correction_method": self.correction_method,
            "alpha": self.alpha,
            "corrected_alpha": self.corrected_alpha,
            "inverse_signals": [x.to_dict() for x in self.inverse_signals],
            "strongest_by_drug": [x.to_dict() for x in self.strongest_by_drug],
            # Omit by_pair from default serialization — too verbose for Claude.
            # Access it programmatically if needed.
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DISEASE → MedDRA MAPPINGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# MedDRA Preferred Terms as they appear in FAERS.  Case matters for
# the .exact field in openFDA.  These are curated starting points —
# the engine also supports dynamic event discovery from FAERS itself.

DISEASE_TO_MEDDRA: dict[str, list[str]] = {
    "glioblastoma": [
        "GLIOBLASTOMA",
        "GLIOBLASTOMA MULTIFORME",
        "BRAIN NEOPLASM MALIGNANT",
        "BRAIN CANCER",
    ],
    "alzheimer": [
        # Verified via count endpoint — only these MedDRA PTs exist in FAERS
        "DEMENTIA ALZHEIMER'S TYPE",
        "DEMENTIA",
        "COGNITIVE DISORDER",
        "MEMORY IMPAIRMENT",
    ],
    "parkinson": [
        "PARKINSON'S DISEASE",
        "TREMOR",
        "BRADYKINESIA",
        "MUSCLE RIGIDITY",
        "GAIT DISTURBANCE",
    ],
    "als": [
        "AMYOTROPHIC LATERAL SCLEROSIS",
        "MOTOR NEURON DISEASE",
        "MUSCULAR WEAKNESS",
        "DYSPHAGIA",
        "RESPIRATORY FAILURE",
    ],
    "breast cancer": [
        "BREAST CANCER",
        "BREAST NEOPLASM",
        "BREAST CANCER METASTATIC",
    ],
    "lung cancer": [
        "LUNG NEOPLASM MALIGNANT",
        "NON-SMALL CELL LUNG CANCER",
        "SMALL CELL LUNG CANCER",
    ],
    "depression": [
        "DEPRESSION",
        "DEPRESSED MOOD",
        "MAJOR DEPRESSION",
        "SUICIDAL IDEATION",
    ],
    "diabetes": [
        "DIABETES MELLITUS",
        "TYPE 2 DIABETES MELLITUS",
        "HYPERGLYCAEMIA",
        "GLYCOSYLATED HAEMOGLOBIN INCREASED",
    ],
    "ipf": [
        "IDIOPATHIC PULMONARY FIBROSIS",
        "PULMONARY FIBROSIS",
        "DYSPNOEA",
        "COUGH",
    ],
    "epilepsy": [
        "EPILEPSY",
        "SEIZURE",
        "GENERALISED TONIC-CLONIC SEIZURE",
        "STATUS EPILEPTICUS",
    ],
    "multiple myeloma": [
        "MULTIPLE MYELOMA",
        "PLASMACYTOMA",
        "BONE PAIN",
        "HYPERCALCAEMIA",
    ],
    "leukemia": [
        "LEUKAEMIA",
        "ACUTE MYELOID LEUKAEMIA",
        "CHRONIC LYMPHOCYTIC LEUKAEMIA",
        "PANCYTOPENIA",
    ],
}


def resolve_disease_terms(
    disease: str,
    override_terms: Sequence[str] | None = None,
) -> list[str]:
    """Map a disease name to MedDRA Preferred Terms for FAERS queries.
    
    FAERS stores all MedDRA terms in ALL CAPS, so we uppercase everything.
    """
    if override_terms:
        return list(dict.fromkeys(
            t.strip().upper() for t in override_terms if t and t.strip()
        ))
    key = disease.lower().strip()
    # Try exact key, then substring match
    if key in DISEASE_TO_MEDDRA:
        return DISEASE_TO_MEDDRA[key]
    for k, v in DISEASE_TO_MEDDRA.items():
        if k in key or key in k:
            return v
    # Fallback: uppercase (FAERS uses ALL CAPS)
    return [disease.strip().upper()]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STATISTICS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _normal_cdf(x: float) -> float:
    """Standard normal CDF via the error function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def compute_signal(
    *,
    drug: str,
    event: str,
    a: int,
    b: int,
    c: int,
    d: int,
    total_faers: int,
    drug_total_reports: int,
    event_total_reports: int,
    min_case_reports: int = 3,
) -> InverseSignal:
    """
    Build an InverseSignal from a 2×2 contingency table.

    ROR = (a*d) / (b*c)
    SE  = sqrt(1/a + 1/b + 1/c + 1/d)
    95% CI = exp(ln(ROR) ± 1.96 * SE)
    p-value = Φ(ln(ROR) / SE)  — one-sided for inverse hypothesis

    Inverse signal: ROR < 1 AND upper CI < 1
    Positive signal: ROR > 1 AND lower CI > 1
    """
    sig = InverseSignal(
        drug=drug, event=event,
        a=a, b=b, c=c, d=d,
        total_faers=total_faers,
        drug_total_reports=drug_total_reports,
        event_total_reports=event_total_reports,
        report_count=a,
    )

    if a < min_case_reports or b <= 0 or c <= 0 or d <= 0:
        sig.insufficient_data = True
        sig.interpretation = (
            f"Insufficient data (a={a}, b={b}, c={c}, d={d}). "
            f"Need ≥{min_case_reports} co-reports for stable estimate."
        )
        return sig

    ror = (a * d) / (b * c)
    se = math.sqrt(1.0 / a + 1.0 / b + 1.0 / c + 1.0 / d)
    ln_ror = math.log(ror)

    ci_lower = math.exp(ln_ror - 1.96 * se)
    ci_upper = math.exp(ln_ror + 1.96 * se)

    # One-sided p-value: P(Z ≤ z) where z = ln(ROR)/SE.
    # Small p → strong evidence ROR < 1 (protective).
    z = ln_ror / se
    p_inverse = _normal_cdf(z)

    is_inverse = ror < 1.0 and ci_upper < 1.0
    is_positive = ror > 1.0 and ci_lower > 1.0
    protection = max(0.0, (1.0 - ror) * 100.0) if ror < 1.0 else 0.0

    if is_inverse:
        interp = (
            f"PROTECTIVE: {drug} users report '{event}' {protection:.1f}% less often "
            f"(ROR={ror:.4f}, CI=[{ci_lower:.4f}, {ci_upper:.4f}], p={p_inverse:.4g}, n={a})."
        )
    elif is_positive:
        excess = (ror - 1.0) * 100.0
        interp = (
            f"RISK: {drug} users report '{event}' {excess:.1f}% more often "
            f"(ROR={ror:.4f}, CI=[{ci_lower:.4f}, {ci_upper:.4f}], n={a})."
        )
    else:
        interp = (
            f"Neutral: no significant signal for '{event}' "
            f"(ROR={ror:.4f}, CI=[{ci_lower:.4f}, {ci_upper:.4f}], n={a})."
        )

    sig.ror = round(ror, 6)
    sig.ci_lower = round(ci_lower, 6)
    sig.ci_upper = round(ci_upper, 6)
    sig.p_value = p_inverse
    sig.is_inverse_signal = is_inverse
    sig.is_positive_signal = is_positive
    sig.protection_pct = round(protection, 3)
    sig.interpretation = interp
    return sig


def normalize_signal(sig: InverseSignal) -> float:
    """Map an InverseSignal to 0-1 for the orchestrator consensus score."""
    if sig.insufficient_data:
        return 0.0
    if not sig.is_inverse_signal:
        # Trending protective but CI crosses 1
        if sig.ror is not None and sig.ror < 1.0:
            return 0.2
        return 0.0

    ror = sig.ror if sig.ror is not None else 1.0
    if ror < 0.3:
        base = 1.0
    elif ror < 0.5:
        base = 0.8
    elif ror < 0.7:
        base = 0.6
    else:
        base = 0.4

    # Volume bonus: more reports = more reliable signal
    n = sig.report_count
    bonus = 0.2 if n >= 100 else (0.1 if n >= 30 else 0.0)
    return min(base + bonus, 1.0)


def bonferroni_alpha(alpha: float, n_tests: int) -> float:
    return alpha / max(n_tests, 1)


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    """Return BH-adjusted q-values (same order as input)."""
    n = len(p_values)
    if n == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    qvals = [1.0] * n
    prev = 1.0
    for rank_from_end, (idx, p) in enumerate(reversed(indexed), start=1):
        rank = n - rank_from_end + 1
        q = min(prev, p * n / rank)
        prev = q
        qvals[idx] = q
    return qvals


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  OPENFDA CLIENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class OpenFDAClient:
    """Async OpenFDA FAERS client with caching, retries, and drug query resolution."""

    BASE_URL = "https://api.fda.gov/drug/event.json"

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 20.0,
        max_retries: int = 3,
        delay: float = 0.25,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENFDA_API_KEY")
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay = delay

        self._cache: dict[str, int] = {}
        self._total: int | None = None
        self._drug_cache: dict[str, str] = {}

    @staticmethod
    def _get_ssl() -> ssl.SSLContext:
        try:
            from drug_rescue.tools._http import get_ssl_context
            return get_ssl_context()
        except ImportError:
            # Fallback if used standalone outside package
            cafile = os.getenv("SSL_CERT_FILE") or os.getenv("REQUESTS_CA_BUNDLE")
            if cafile and os.path.exists(cafile):
                return ssl.create_default_context(cafile=cafile)
            try:
                import certifi
                return ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                for path in ["/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"]:
                    if os.path.exists(path):
                        return ssl.create_default_context(cafile=path)
                return ssl.create_default_context()

    # ── Low-level HTTP ──

    async def _fetch(self, params: dict[str, Any]) -> tuple[dict, int]:
        """Thread-offloaded HTTP GET using requests library.
        
        Migrated from urllib to requests — same fix that resolved
        ClinicalTrials.gov (cookie/redirect) and PubChem (gzip) issues.
        
        URL construction for openFDA:
          - The 'search' param contains Lucene query syntax chars
            (: " . * AND OR) that must be encoded carefully.
          - requests.get(url, params=dict) auto-encodes, but it
            percent-encodes characters that openFDA needs literal.
          - So we build the search portion of the URL manually
            using quote_plus with a targeted safe set, then let
            requests handle everything else.
        """
        import requests as _req

        def _blocking() -> tuple[dict, int]:
            # Separate search from other params — search needs special encoding
            search = params.pop("search", None)

            # Build URL: search param is manually encoded, rest via urlencode
            other = urllib.parse.urlencode(
                {k: v for k, v in params.items() if k != "search"}
            )
            if search:
                # quote_plus encodes spaces to +, everything else to %XX
                # safe chars:  ' → literal (MedDRA possessives — BUT we use
                #                  wildcard * now, so this is just defense-in-depth)
                #              () → literal (OR grouping in drug resolution)
                #              * → literal (wildcard for apostrophe terms)
                safe_search = urllib.parse.quote_plus(search, safe="'()*")
                qs = f"search={safe_search}&{other}" if other else f"search={safe_search}"
                params["search"] = search  # restore for caller/caching
            else:
                qs = other

            url = f"{self.BASE_URL}?{qs}"
            logger.debug("FAERS URL: %s", url)
            try:
                resp = _req.get(url, timeout=self.timeout)
                if resp.status_code in (404, 429):
                    return {}, resp.status_code
                resp.raise_for_status()
                return resp.json(), resp.status_code
            except _req.exceptions.HTTPError as e:
                code = e.response.status_code if e.response else 500
                return {}, code
            except _req.exceptions.RequestException as e:
                logger.warning("FAERS request failed: %s", e)
                raise

        return await asyncio.to_thread(_blocking)

    # ── Count queries ──

    async def get_count(self, search: str) -> int:
        """Get total matching report count for a search query. Cached."""
        if search in self._cache:
            return self._cache[search]

        for attempt in range(self.max_retries):
            params: dict[str, Any] = {"search": search, "count": "receivedate"}
            if self.api_key:
                params["api_key"] = self.api_key

            try:
                payload, code = await self._fetch(params)
                if code == 404:
                    self._cache[search] = 0
                    return 0
                if code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                if code == 200:
                    total = sum(
                        int(r.get("count", 0))
                        for r in payload.get("results", [])
                    )
                    self._cache[search] = total
                    return total
            except (TimeoutError, OSError, Exception) as e:
                logger.debug("get_count attempt %d failed: %s", attempt, e)
                await asyncio.sleep(2 ** attempt)

        return 0

    async def get_total_reports(self) -> int:
        """Total reports in FAERS (cached after first call)."""
        if self._total is not None:
            return self._total

        params: dict[str, Any] = {"count": "receivedate"}
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            payload, code = await self._fetch(params)
            if code == 200:
                total = sum(
                    int(r.get("count", 0))
                    for r in payload.get("results", [])
                )
                if total > 0:
                    self._total = total
                    return total
        except Exception as e:
            logger.warning("Failed to fetch FAERS total: %s", e)

        self._total = 20_000_000  # Fallback ~current FAERS size
        return self._total

    # ── Drug query resolution ──

    @staticmethod
    def _drug_variants(name: str) -> list[str]:
        """Generate openFDA query variants for a drug name."""
        canonical = name.strip().upper()
        return [
            f'patient.drug.openfda.generic_name.exact:"{canonical}"',
            f'patient.drug.medicinalproduct:"{canonical}"',
            f'patient.drug.openfda.substance_name.exact:"{canonical}"',
        ]

    async def resolve_drug(self, name: str) -> str:
        """Pick the drug query variant with the most FAERS reports."""
        key = name.strip().upper()
        if key in self._drug_cache:
            return self._drug_cache[key]

        best_query, best_count = "", -1
        for variant in self._drug_variants(name):
            count = await self.get_count(variant)
            if count > best_count:
                best_count = count
                best_query = variant
            await asyncio.sleep(self.delay)

        if best_count <= 0:
            # Last resort: OR all variants together
            canonical = key
            best_query = (
                f'(patient.drug.openfda.generic_name.exact:"{canonical}" OR '
                f'patient.drug.medicinalproduct:"{canonical}")'
            )

        self._drug_cache[key] = best_query
        logger.info("Drug %s → %s (count=%d)", key, best_query, max(best_count, 0))
        return best_query

    @staticmethod
    def event_query(term: str) -> str:
        """Build a SEARCH query for an event term (clean terms only).
        
        For terms WITHOUT apostrophes: uses .exact with quotes.
        For terms WITH apostrophes: use _event_broad_filter() + _count_exact_term()
        instead — this method returns a broad filter that WILL overcount.
        
        The contingency() method handles this automatically.
        """
        upper = term.strip().upper()
        if "'" not in upper:
            return f'patient.reaction.reactionmeddrapt.exact:"{upper}"'
        # Apostrophe: return broad tokenized filter (overcounts!)
        # Callers should use _count_exact_term() for precise counts.
        return OpenFDAClient._event_broad_filter(term)

    @staticmethod
    def _event_broad_filter(term: str) -> str:
        """Build a broad tokenized-field filter for apostrophe MedDRA terms.
        
        Strategy: split into words, use wildcard for apostrophe words,
        AND them together on the tokenized field.
        
        Example: "DEMENTIA ALZHEIMER'S TYPE" →
          patient.reaction.reactionmeddrapt:DEMENTIA
          AND patient.reaction.reactionmeddrapt:ALZHEIMER*
          AND patient.reaction.reactionmeddrapt:TYPE
          
        This is INTENTIONALLY broad — it's used as a pre-filter for
        the count endpoint, which then gives us precise .exact counts.
        """
        field = "patient.reaction.reactionmeddrapt"
        clauses = []
        for word in term.strip().upper().split():
            if "'" in word:
                # ALZHEIMER'S → ALZHEIMER* (wildcard matches the 's)
                base = word.split("'")[0]
                clauses.append(f"{field}:{base}*")
            else:
                clauses.append(f"{field}:{word}")
        return " AND ".join(clauses)

    @staticmethod
    def _normalize_term(term: str) -> str:
        """Normalize FAERS data quality issues in MedDRA terms.
        
        FAERS has known data quality problems where the same MedDRA term
        appears with different punctuation:
          - DEMENTIA ALZHEIMER'S TYPE  (1,671 reports — apostrophe)
          - DEMENTIA ALZHEIMER^S TYPE  (7,426 reports — caret)
          
        These represent the SAME concept entered differently by submitters.
        We normalize to apostrophe for matching, then SUM all variants.
        """
        return term.replace("^", "'")

    async def _count_exact_term(
        self,
        search_filter: str,
        target_term: str,
    ) -> int:
        """Get precise count for a specific MedDRA .exact term.
        
        Uses the COUNT endpoint to bypass the apostrophe parsing bug:
        1. Filter reports broadly (e.g., reactionmeddrapt:ALZHEIMER*)
        2. Count by reactionmeddrapt.exact (returns term→count pairs)
        3. Find ALL matching variants (apostrophe + caret) and SUM them
        
        The apostrophe/caret normalization handles known FAERS data quality
        issues where the same MedDRA term is stored with different
        punctuation (e.g., ALZHEIMER'S vs ALZHEIMER^S).
        """
        cache_key = f"__cet__{search_filter}__{target_term}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        params: dict[str, Any] = {
            "search": search_filter,
            "count": "patient.reaction.reactionmeddrapt.exact",
            "limit": 1000,
        }
        if self.api_key:
            params["api_key"] = self.api_key

        for attempt in range(self.max_retries):
            try:
                payload, code = await self._fetch(params)
                if code == 404:
                    break
                if code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                if code == 200:
                    target_norm = self._normalize_term(
                        target_term.strip().upper()
                    )
                    # Sum ALL variants that normalize to the same string
                    total = 0
                    matched_variants = []
                    for r in payload.get("results", []):
                        term_raw = r.get("term", "").strip().upper()
                        term_norm = self._normalize_term(term_raw)
                        if term_norm == target_norm:
                            count = int(r.get("count", 0))
                            total += count
                            matched_variants.append(
                                f"{r.get('term', '?')}={count}"
                            )
                    if total > 0:
                        self._cache[cache_key] = total
                        logger.info(
                            "Count endpoint: '%s' → %d (variants: %s)",
                            target_term, total,
                            ", ".join(matched_variants),
                        )
                        return total
                    # Term not found in results at all
                    logger.debug(
                        "Count endpoint: '%s' not in top %d results "
                        "(filter: %s)",
                        target_term,
                        len(payload.get("results", [])),
                        search_filter[:60],
                    )
                    break
            except Exception as e:
                logger.debug("_count_exact_term attempt %d: %s", attempt, e)
                await asyncio.sleep(2 ** attempt)

        self._cache[cache_key] = 0
        return 0

    # ── Contingency table ──

    async def contingency(
        self,
        drug: str,
        event: str,
        total: int | None = None,
    ) -> tuple[int, int, int, int, int, int, int]:
        """
        Build 2×2 contingency table from FAERS for one drug × event pair.

        Returns: (a, b, c, d, N, drug_total, event_total)
            a = both drug AND event
            b = drug but NOT event
            c = event but NOT drug
            d = neither
            N = total FAERS reports
            
        For terms with apostrophes (ALZHEIMER'S, PARKINSON'S, CROHN'S):
        uses the count endpoint approach to get precise .exact counts
        without ever putting the apostrophe in the query string.
        """
        N = total if total is not None else await self.get_total_reports()
        dq = await self.resolve_drug(drug)

        has_apostrophe = "'" in event

        if not has_apostrophe:
            # ── Clean term: standard .exact approach ──
            eq = f'patient.reaction.reactionmeddrapt.exact:"{event.strip().upper()}"'
            a = await self.get_count(f"{dq} AND {eq}")
            await asyncio.sleep(self.delay)
            drug_total = await self.get_count(dq)
            await asyncio.sleep(self.delay)
            event_total = await self.get_count(eq)
        else:
            # ── Apostrophe term: count endpoint approach ──
            broad = self._event_broad_filter(event)
            target = event.strip().upper()

            # a = drug AND event (count endpoint with drug filter)
            a = await self._count_exact_term(f"{dq} AND {broad}", target)
            await asyncio.sleep(self.delay)
            drug_total = await self.get_count(dq)
            await asyncio.sleep(self.delay)
            # event_total (count endpoint, no drug filter)
            event_total = await self._count_exact_term(broad, target)

        b = max(drug_total - a, 0)
        c = max(event_total - a, 0)
        d = max(N - a - b - c, 1)

        return a, b, c, d, N, drug_total, event_total

    # ── Event discovery ──

    async def top_events(
        self,
        drug: str | None = None,
        limit: int = 100,
    ) -> list[tuple[str, int]]:
        """
        Fetch most-reported MedDRA terms from FAERS.

        If drug is provided, returns events reported for that drug.
        Otherwise returns globally most-reported events.
        """
        params: dict[str, Any] = {
            "count": "patient.reaction.reactionmeddrapt.exact",
            "limit": max(1, min(limit, 1000)),
        }
        if self.api_key:
            params["api_key"] = self.api_key

        queries: list[str | None] = [None]
        if drug:
            queries = self._drug_variants(drug)

        for query in queries:
            if query:
                params["search"] = query
            elif "search" in params:
                del params["search"]

            payload, code = await self._fetch(params)
            if code != 200:
                continue

            results = [
                (str(r.get("term", "")).strip(), int(r.get("count", 0)))
                for r in payload.get("results", [])
                if r.get("term", "").strip()
            ]
            if results:
                return results

        return []


# Backward-compatible alias
FAERSClient = OpenFDAClient


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class FAERSEngine:
    """
    High-level FAERS inverse signal detector.

    Screens multiple drugs × multiple events concurrently with rate limiting,
    applies multiple testing correction, and returns structured results.
    """

    def __init__(
        self,
        api_key: str | None = None,
        max_concurrent: int = 5,
        timeout: float = 20.0,
        delay: float = 0.25,
    ) -> None:
        self.client = OpenFDAClient(
            api_key=api_key,
            timeout=timeout,
            delay=delay,
        )
        self.max_concurrent = max_concurrent

    async def _analyze_pair(
        self,
        drug: str,
        event: str,
        total: int,
    ) -> InverseSignal:
        """Score one drug × event pair."""
        a, b, c, d, N, drug_total, event_total = await self.client.contingency(
            drug=drug, event=event, total=total,
        )
        sig = compute_signal(
            drug=drug, event=event,
            a=a, b=b, c=c, d=d,
            total_faers=N,
            drug_total_reports=drug_total,
            event_total_reports=event_total,
        )
        sig.normalized_score = normalize_signal(sig)
        return sig

    async def screen(
        self,
        *,
        drugs: Sequence[str],
        disease: str,
        disease_events: Sequence[str] | None = None,
        alpha: float = 0.05,
        correction: str = "none",
    ) -> ScreeningResult:
        """
        Screen drugs against a disease for inverse signals.

        Args:
            drugs: Drug generic names to screen.
            disease: Disease name (resolves to MedDRA terms).
            disease_events: Override MedDRA terms (bypass built-in mapping).
            alpha: Significance level.
            correction: "none", "bonferroni", or "fdr".

        Returns:
            ScreeningResult with all pair-level analyses, inverse signals,
            and per-drug summary verdicts.
        """
        events = resolve_disease_terms(disease, disease_events)
        total = await self.client.get_total_reports()

        # Build all drug × event pairs
        pairs = [
            (d.strip(), e.strip())
            for d in drugs for e in events
            if d.strip() and e.strip()
        ]

        # Run with concurrency control
        sem = asyncio.Semaphore(self.max_concurrent)

        async def limited(drug: str, event: str) -> InverseSignal:
            async with sem:
                return await self._analyze_pair(drug, event, total)

        results = await asyncio.gather(
            *(limited(d, e) for d, e in pairs)
        )

        # Multiple testing correction
        n_tests = len(results)
        correction = correction.lower().strip()
        corrected_alpha = alpha

        if correction == "bonferroni":
            corrected_alpha = bonferroni_alpha(alpha, n_tests)
            for sig in results:
                if sig.p_value is not None:
                    sig.is_inverse_signal = (
                        sig.is_inverse_signal and sig.p_value <= corrected_alpha
                    )
        elif correction in ("fdr", "bh", "benjamini-hochberg"):
            pvals = [1.0 if s.p_value is None else s.p_value for s in results]
            qvals = benjamini_hochberg(pvals)
            for sig, qval in zip(results, qvals):
                sig.q_value = qval
                sig.is_inverse_signal = sig.is_inverse_signal and qval <= alpha
            correction = "fdr"
        elif correction != "none":
            raise ValueError("correction must be: none, bonferroni, or fdr")

        # Collect inverse signals, sorted by ROR (lowest = strongest)
        inverse = sorted(
            [s for s in results if s.is_inverse_signal],
            key=lambda s: (s.ror if s.ror is not None else 1.0, -s.report_count),
        )

        # Per-drug summary: strongest signal per drug
        by_drug: dict[str, list[InverseSignal]] = defaultdict(list)
        for sig in results:
            by_drug[sig.drug].append(sig)

        strongest: list[InverseSignal] = []
        for drug_signals in by_drug.values():
            drug_signals.sort(key=lambda s: (
                not s.is_inverse_signal,
                s.ror if s.ror is not None else 1.0,
                -s.report_count,
            ))
            strongest.append(drug_signals[0])

        strongest.sort(key=lambda s: (
            not s.is_inverse_signal,
            s.ror if s.ror is not None else 1.0,
        ))

        return ScreeningResult(
            disease=disease,
            events=events,
            total_faers=total,
            tests_run=n_tests,
            correction_method=correction,
            alpha=alpha,
            corrected_alpha=corrected_alpha,
            by_pair=results,
            inverse_signals=inverse,
            strongest_by_drug=strongest,
        )

    async def suggest_events(
        self,
        drug: str | None = None,
        limit: int = 25,
    ) -> list[tuple[str, int]]:
        """Fetch top MedDRA event terms from FAERS."""
        return await self.client.top_events(drug=drug, limit=limit)
