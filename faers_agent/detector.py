"""High-level FAERS detector that screens many drug/event pairs."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Sequence

from .client import OpenFDAClient
from .mappings import resolve_disease_terms
from .models import InverseSignal, ScreeningResult
from .stats import (
    benjamini_hochberg_qvalues,
    bonferroni_alpha,
    compute_inverse_signal,
    normalize_faers_signal,
)


class FAERSDetector:
    def __init__(self, client: OpenFDAClient, max_concurrent: int = 5) -> None:
        self.client = client
        self.max_concurrent = max_concurrent

    async def _run_pair(
        self,
        drug: str,
        event: str,
        total_faers: int,
    ) -> InverseSignal:
        a, b, c, d, total_n, a_plus_b, a_plus_c = await self.client.contingency_counts(
            drug=drug,
            event=event,
            total_reports=total_faers,
        )

        signal = compute_inverse_signal(
            drug=drug,
            event=event,
            a=a,
            b=b,
            c=c,
            d=d,
            total_faers=total_n,
            drug_total_reports=a_plus_b,
            event_total_reports=a_plus_c,
        )
        signal.normalized_score = normalize_faers_signal(signal)
        return signal

    async def screen_drugs(
        self,
        *,
        drug_names: Sequence[str],
        disease: str,
        disease_events: Sequence[str] | None = None,
        alpha: float = 0.05,
        correction: str = "none",
    ) -> ScreeningResult:
        events = resolve_disease_terms(disease, disease_events)
        total_faers = await self.client.get_total_reports()

        sem = asyncio.Semaphore(self.max_concurrent)

        async def limited(drug: str, event: str) -> InverseSignal:
            async with sem:
                return await self._run_pair(drug, event, total_faers)

        pairs = [(drug.strip(), event.strip()) for drug in drug_names for event in events]
        tasks = [limited(drug, event) for drug, event in pairs if drug and event]
        by_pair = await asyncio.gather(*tasks)

        tests_run = len(by_pair)
        correction = correction.lower().strip()
        corrected_alpha = alpha

        if correction == "bonferroni":
            corrected_alpha = bonferroni_alpha(alpha, tests_run)
            for signal in by_pair:
                if signal.p_value is None:
                    continue
                signal.is_inverse_signal = signal.is_inverse_signal and signal.p_value <= corrected_alpha
        elif correction in {"fdr", "bh", "benjamini-hochberg"}:
            pvals = [1.0 if s.p_value is None else s.p_value for s in by_pair]
            qvals = benjamini_hochberg_qvalues(pvals)
            for signal, qval in zip(by_pair, qvals):
                signal.q_value = qval
                signal.is_inverse_signal = signal.is_inverse_signal and qval <= alpha
        elif correction != "none":
            raise ValueError("correction must be one of: none, bonferroni, fdr")

        inverse_signals = [s for s in by_pair if s.is_inverse_signal]
        inverse_signals.sort(key=lambda s: (s.ror if s.ror is not None else 1.0, -s.report_count))

        by_drug: dict[str, list[InverseSignal]] = defaultdict(list)
        for signal in by_pair:
            by_drug[signal.drug].append(signal)

        strongest_by_drug: list[InverseSignal] = []
        for _, candidates in by_drug.items():
            candidates.sort(
                key=lambda s: (
                    not s.is_inverse_signal,
                    s.ror if s.ror is not None else 1.0,
                    -s.report_count,
                )
            )
            strongest_by_drug.append(candidates[0])

        strongest_by_drug.sort(
            key=lambda s: (not s.is_inverse_signal, s.ror if s.ror is not None else 1.0)
        )

        return ScreeningResult(
            disease=disease,
            events=events,
            total_faers=total_faers,
            tests_run=tests_run,
            correction_method=correction,
            alpha=alpha,
            corrected_alpha=corrected_alpha,
            by_pair=by_pair,
            inverse_signals=inverse_signals,
            strongest_by_drug=strongest_by_drug,
        )
