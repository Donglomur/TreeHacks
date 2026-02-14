import pytest

from faers_agent.detector import FAERSDetector


class FakeClient:
    def __init__(self):
        self._total = 10_000_000

    async def get_total_reports(self):
        return self._total

    async def contingency_counts(self, drug, event, total_reports=None):
        # Make metformin strongly inverse and everything else neutral/risky.
        total_n = total_reports or self._total
        if drug.lower() == "metformin":
            a, b, c = 10, 8_000, 150_000
            d = total_n - a - b - c
            return a, b, c, d, total_n, a + b, a + c
        a, b, c = 200, 3000, 2000
        d = total_n - a - b - c
        return a, b, c, d, total_n, a + b, a + c


@pytest.mark.asyncio
async def test_screen_drugs_returns_strongest_per_drug():
    detector = FAERSDetector(client=FakeClient(), max_concurrent=2)

    result = await detector.screen_drugs(
        drug_names=["metformin", "atorvastatin"],
        disease="cancer",
        disease_events=["Neoplasm malignant", "Metastasis"],
        correction="none",
    )

    assert result.tests_run == 4
    assert len(result.strongest_by_drug) == 2
    best = {r.drug: r for r in result.strongest_by_drug}
    assert best["metformin"].is_inverse_signal is True
    assert best["atorvastatin"].is_inverse_signal is False
