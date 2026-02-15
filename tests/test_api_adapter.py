from pathlib import Path

from drug_rescue.api_adapter import (
    build_artifacts_from_bundle,
    find_precomputed_bundle,
    infer_disease_from_message,
)


def test_find_precomputed_bundle_glioblastoma():
    root = Path("files")
    bundle = find_precomputed_bundle("glioblastoma", root)
    assert bundle is not None
    assert bundle.name == "glioblastoma"


def test_build_artifacts_from_bundle_has_ranked_candidates():
    bundle = Path("files") / "glioblastoma"
    artifacts = build_artifacts_from_bundle(
        disease="glioblastoma",
        subtype="high-grade",
        bundle_root=bundle,
        source="precomputed",
    )
    assert artifacts.query.disease == "glioblastoma"
    assert artifacts.query.subtype == "high-grade"
    assert len(artifacts.rankedCandidates) > 0
    assert artifacts.rankedCandidates[0].drug
    assert "source" in artifacts.meta


def test_infer_disease_from_message_uses_bundle_name():
    root = Path("files")
    msg = "show me repurposing candidates for glioblastoma"
    disease = infer_disease_from_message(msg, root)
    assert disease == "glioblastoma"


def test_infer_disease_from_short_direct_message():
    root = Path("files")
    msg = "pancreatic cancer"
    disease = infer_disease_from_message(msg, root)
    assert disease == "pancreatic cancer"
