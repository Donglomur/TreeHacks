from faers_agent.stats import benjamini_hochberg_qvalues, compute_inverse_signal, normalize_faers_signal


def test_compute_inverse_signal_detects_protective_association():
    signal = compute_inverse_signal(
        drug="metformin",
        event="Neoplasm malignant",
        a=5000,
        b=500000,
        c=2_000_000,
        d=15_000_000,
        total_faers=17_505_000,
        drug_total_reports=505000,
        event_total_reports=2_005_000,
    )

    assert signal.insufficient_data is False
    assert signal.is_inverse_signal is True
    assert signal.ror is not None
    assert 0.07 <= signal.ror <= 0.08
    assert signal.ci_upper is not None and signal.ci_upper < 1.0
    assert normalize_faers_signal(signal) > 0.9


def test_bh_qvalues_monotonic_and_bounded():
    pvals = [0.001, 0.02, 0.03, 0.2]
    qvals = benjamini_hochberg_qvalues(pvals)
    assert len(qvals) == 4
    assert all(0 <= q <= 1 for q in qvals)
    assert qvals[0] <= qvals[1] <= qvals[2] <= qvals[3]
