"""Statistical utilities for FAERS inverse-signal detection."""

from __future__ import annotations

import math

from .models import InverseSignal


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def compute_inverse_signal(
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
    signal = InverseSignal(
        drug=drug,
        event=event,
        a=a,
        b=b,
        c=c,
        d=d,
        total_faers=total_faers,
        drug_total_reports=drug_total_reports,
        event_total_reports=event_total_reports,
        report_count=a,
    )

    if a < min_case_reports or b <= 0 or c <= 0 or d <= 0:
        signal.insufficient_data = True
        signal.interpretation = (
            f"Insufficient data for stable estimate (a={a}, b={b}, c={c}, d={d})."
        )
        return signal

    ror = (a * d) / (b * c)
    se = math.sqrt(1.0 / a + 1.0 / b + 1.0 / c + 1.0 / d)
    ln_ror = math.log(ror)

    ci_lower = math.exp(ln_ror - 1.96 * se)
    ci_upper = math.exp(ln_ror + 1.96 * se)

    # One-sided p-value for inverse signal hypothesis (ln(ROR) < 0).
    z = ln_ror / se
    p_inverse = normal_cdf(z)

    is_inverse = ror < 1.0 and ci_upper < 1.0
    is_positive = ror > 1.0 and ci_lower > 1.0
    protection = max(0.0, (1.0 - ror) * 100.0) if ror < 1.0 else 0.0

    if is_inverse:
        interpretation = (
            f"PROTECTIVE: {drug} users report '{event}' {protection:.1f}% less often "
            f"(ROR={ror:.4f}, CI=[{ci_lower:.4f}, {ci_upper:.4f}], n={a})."
        )
    elif is_positive:
        interpretation = (
            f"RISK: elevated reporting for '{event}' "
            f"(ROR={ror:.4f}, CI=[{ci_lower:.4f}, {ci_upper:.4f}], n={a})."
        )
    else:
        interpretation = (
            f"No significant signal (ROR={ror:.4f}, "
            f"CI=[{ci_lower:.4f}, {ci_upper:.4f}], n={a})."
        )

    signal.ror = round(ror, 6)
    signal.ci_lower = round(ci_lower, 6)
    signal.ci_upper = round(ci_upper, 6)
    signal.p_value = p_inverse
    signal.is_inverse_signal = is_inverse
    signal.is_positive_signal = is_positive
    signal.protection_pct = round(protection, 3)
    signal.interpretation = interpretation
    return signal


def normalize_faers_signal(signal: InverseSignal) -> float:
    if signal.insufficient_data:
        return 0.0

    if not signal.is_inverse_signal:
        if signal.ror is not None and signal.ror < 1.0:
            return 0.2
        return 0.0

    ror = signal.ror if signal.ror is not None else 1.0
    count = signal.report_count

    if ror < 0.3:
        ror_score = 1.0
    elif ror < 0.5:
        ror_score = 0.8
    elif ror < 0.7:
        ror_score = 0.6
    else:
        ror_score = 0.4

    vol_bonus = 0.2 if count >= 100 else (0.1 if count >= 30 else 0.0)
    return min(ror_score + vol_bonus, 1.0)


def bonferroni_alpha(alpha: float, tests_run: int) -> float:
    if tests_run <= 0:
        return alpha
    return alpha / tests_run


def benjamini_hochberg_qvalues(p_values: list[float]) -> list[float]:
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
