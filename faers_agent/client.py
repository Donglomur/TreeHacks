"""Async OpenFDA client with retries, caching, and dynamic FAERS totals."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)


class OpenFDAClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.fda.gov/drug/event.json",
        timeout: float = 20.0,
        max_retries: int = 3,
        delay_between_calls: float = 0.25,
        fallback_total_reports: int = 20_000_000,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay_between_calls = delay_between_calls
        self.fallback_total_reports = fallback_total_reports

        self._cache: dict[str, int] = {}
        self._total_reports: Optional[int] = None
        self._drug_query_cache: dict[str, str] = {}
        self._ssl_context = self._build_ssl_context()

    @staticmethod
    def _build_ssl_context() -> ssl.SSLContext:
        cafile = os.getenv("SSL_CERT_FILE") or os.getenv("REQUESTS_CA_BUNDLE")
        if cafile:
            return ssl.create_default_context(cafile=cafile)
        try:
            import certifi

            return ssl.create_default_context(cafile=certifi.where())
        except Exception:  # noqa: BLE001
            return ssl.create_default_context()

    @staticmethod
    def drug_query(drug_name: str) -> str:
        canonical = drug_name.upper()
        generic_exact = f'patient.drug.openfda.generic_name.exact:"{canonical}"'
        medicinal_fallback = f'patient.drug.medicinalproduct:"{canonical}"'
        # OR fallback increases recall when openfda.generic_name is missing.
        return f"({generic_exact} OR {medicinal_fallback})"

    @staticmethod
    def drug_query_variants(drug_name: str) -> list[str]:
        canonical = drug_name.upper()
        return [
            f'patient.drug.openfda.generic_name.exact:"{canonical}"',
            f'patient.drug.medicinalproduct:"{canonical}"',
            f'patient.drug.openfda.substance_name.exact:"{canonical}"',
        ]

    @staticmethod
    def event_query(event_term: str) -> str:
        return f'patient.reaction.reactionmeddrapt.exact:"{event_term}"'

    async def get_total_reports(self, force_refresh: bool = False) -> int:
        if self._total_reports is not None and not force_refresh:
            return self._total_reports

        params = {"count": "receivedate"}
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            payload, status_code = await self._fetch_json(params)
            if status_code == 200:
                results = payload.get("results", [])
                total = sum(int(item.get("count", 0)) for item in results)
                if total > 0:
                    self._total_reports = total
                    return total
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed dynamic FAERS total fetch: %s", exc)

        self._total_reports = self.fallback_total_reports
        return self._total_reports

    async def _fetch_json(self, params: dict[str, str]) -> tuple[dict, int]:
        def blocking_fetch() -> tuple[dict, int]:
            query = urllib.parse.urlencode(params)
            url = f"{self.base_url}?{query}"
            try:
                with urllib.request.urlopen(
                    url, timeout=self.timeout, context=self._ssl_context
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    return payload, int(response.status)
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    return {}, 404
                if exc.code == 429:
                    return {}, 429
                return {}, exc.code
            except urllib.error.URLError as exc:
                msg = str(exc)
                if "CERTIFICATE_VERIFY_FAILED" in msg:
                    raise RuntimeError(
                        "TLS certificate verification failed. Ensure CA roots are installed "
                        "or set SSL_CERT_FILE to a valid CA bundle."
                    ) from exc
                raise

        return await asyncio.to_thread(blocking_fetch)

    async def get_count(self, search_query: str, use_cache: bool = True) -> int:
        if use_cache and search_query in self._cache:
            return self._cache[search_query]

        for attempt in range(self.max_retries):
            params = {"search": search_query, "count": "receivedate"}
            if self.api_key:
                params["api_key"] = self.api_key

            try:
                payload, status_code = await self._fetch_json(params)
                if status_code == 404:
                    self._cache[search_query] = 0
                    return 0
                if status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                if status_code == 200:
                    results = payload.get("results", [])
                    count = sum(int(item.get("count", 0)) for item in results)
                    self._cache[search_query] = count
                    return count
                await asyncio.sleep(2 ** attempt)
            except (TimeoutError, urllib.error.URLError):
                await asyncio.sleep(2 ** attempt)

        return 0

    async def resolve_drug_query(self, drug_name: str) -> str:
        key = drug_name.strip().upper()
        if key in self._drug_query_cache:
            return self._drug_query_cache[key]

        variants = self.drug_query_variants(drug_name)
        best_query = variants[0]
        best_count = -1
        for query in variants:
            count = await self.get_count(query)
            if count > best_count:
                best_count = count
                best_query = query

        self._drug_query_cache[key] = best_query
        logger.info(
            "Using drug query variant for %s: %s (count=%s)",
            key,
            best_query,
            max(best_count, 0),
        )
        return best_query

    async def top_event_terms(
        self,
        *,
        drug: str | None = None,
        limit: int = 100,
    ) -> list[tuple[str, int]]:
        base_params: dict[str, str | int] = {
            "count": "patient.reaction.reactionmeddrapt.exact",
            "limit": max(1, min(limit, 1000)),
        }
        if self.api_key:
            base_params["api_key"] = self.api_key

        queries = [None]
        if drug:
            queries = self.drug_query_variants(drug)

        for query in queries:
            params = dict(base_params)
            if query:
                params["search"] = query
            payload, status_code = await self._fetch_json(params)
            if status_code != 200:
                continue
            rows = payload.get("results", [])
            out: list[tuple[str, int]] = []
            for row in rows:
                term = str(row.get("term", "")).strip()
                count = int(row.get("count", 0))
                if term:
                    out.append((term, count))
            if out:
                logger.info("Event term suggestion query matched using: %s", query or "<none>")
                return out
        return []

    async def contingency_counts(
        self,
        drug: str,
        event: str,
        *,
        total_reports: Optional[int] = None,
    ) -> tuple[int, int, int, int, int, int, int]:
        total_n = total_reports if total_reports is not None else await self.get_total_reports()
        dq = await self.resolve_drug_query(drug)
        eq = self.event_query(event)

        a = await self.get_count(f"{dq} AND {eq}")
        await asyncio.sleep(self.delay_between_calls)
        a_plus_b = await self.get_count(dq)
        await asyncio.sleep(self.delay_between_calls)
        a_plus_c = await self.get_count(eq)

        if a == 0 and a_plus_b > 0 and a_plus_c > 0:
            logger.warning(
                "Zero overlap for drug-event pair despite nonzero marginals: drug=%s event=%s",
                drug,
                event,
            )

        b = max(a_plus_b - a, 0)
        c = max(a_plus_c - a, 0)
        d = max(total_n - a - b - c, 1)
        return a, b, c, d, total_n, a_plus_b, a_plus_c
