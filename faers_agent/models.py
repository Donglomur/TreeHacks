"""Core typed models for FAERS screening results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class InverseSignal:
    drug: str
    event: str
    a: int
    b: int
    c: int
    d: int
    total_faers: int
    drug_total_reports: int
    event_total_reports: int
    report_count: int
    ror: float | None = None
    ci_lower: float | None = None
    ci_upper: float | None = None
    p_value: float | None = None
    q_value: float | None = None
    is_inverse_signal: bool = False
    is_positive_signal: bool = False
    insufficient_data: bool = False
    protection_pct: float = 0.0
    interpretation: str = ""
    normalized_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScreeningResult:
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
            "by_pair": [x.to_dict() for x in self.by_pair],
            "inverse_signals": [x.to_dict() for x in self.inverse_signals],
            "strongest_by_drug": [x.to_dict() for x in self.strongest_by_drug],
        }
