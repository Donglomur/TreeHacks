"""Adapter utilities for mapping DrugRescue artifacts into frontend response shape."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .api_types import (
    Artifacts,
    ChatResponse,
    Citation,
    DockSignal,
    FAERSSignal,
    KGSignal,
    QueryArtifact,
    RankedCandidate,
    Signals,
    TrialSignal,
)


def normalize_disease_name(value: str) -> str:
    return " ".join(value.lower().strip().replace("_", " ").replace("-", " ").split())


def find_precomputed_bundle(disease: str, root: Path) -> Path | None:
    if not root.exists():
        return None

    normalized = normalize_disease_name(disease)
    candidates = [
        disease.strip(),
        normalized,
        normalized.replace(" ", "_"),
        normalized.replace(" ", "-"),
    ]
    for name in candidates:
        p = root / name
        if p.is_dir():
            return p

    for p in root.iterdir():
        if p.is_dir() and normalize_disease_name(p.name) == normalized:
            return p
    return None


def load_json_safe(path: Path, missing: list[str], warnings: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        missing.append(str(path))
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"invalid_json:{path}:{exc}")
        return None
    if not isinstance(data, dict):
        warnings.append(f"unexpected_shape:{path}")
        return None
    return data


def _upper_key_map(items: dict[str, Any] | None) -> dict[str, Any]:
    if not items:
        return {}
    return {str(k).upper(): v for k, v in items.items()}


def _first_trial_payload(drug_trials: dict[str, Any] | None) -> tuple[str | None, str | None]:
    if not isinstance(drug_trials, dict):
        return None, None
    trials = drug_trials.get("trials", [])
    if isinstance(trials, list) and trials:
        t0 = trials[0] if isinstance(trials[0], dict) else {}
        return str(t0.get("failure_category") or drug_trials.get("classification") or ""), str(
            t0.get("why_stopped") or drug_trials.get("interpretation") or ""
        )
    return str(drug_trials.get("classification") or ""), str(drug_trials.get("interpretation") or "")


def _extract_citations(lit_row: dict[str, Any] | None, ct_row: dict[str, Any] | None) -> list[Citation]:
    out: list[Citation] = []
    seen: set[str] = set()
    nct_re = re.compile(r"(NCT\d{8})", re.IGNORECASE)
    year_re = re.compile(r"\b(20\d{2}|19\d{2})\b")

    def add_title(title: str) -> None:
        if not title:
            return
        norm = title.strip()
        if not norm or norm.lower() in seen:
            return
        seen.add(norm.lower())
        nct_match = nct_re.search(norm)
        year_match = year_re.search(norm)
        out.append(
            Citation(
                title=norm[:220],
                year=int(year_match.group(1)) if year_match else None,
                pmid=None,
                nct=nct_match.group(1).upper() if nct_match else None,
            )
        )

    if isinstance(lit_row, dict):
        ce = lit_row.get("clinical_evidence")
        if isinstance(ce, dict):
            for value in ce.values():
                if isinstance(value, str):
                    add_title(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            add_title(item)
        for key in ("mechanism", "regulatory", "safety"):
            v = lit_row.get(key)
            if isinstance(v, str):
                add_title(v)

    if isinstance(ct_row, dict):
        trials = ct_row.get("trials", [])
        if isinstance(trials, list):
            for trial in trials:
                if not isinstance(trial, dict):
                    continue
                title = str(trial.get("title") or "").strip()
                nct = str(trial.get("nct_id") or "").strip()
                if nct:
                    title = f"{nct}: {title}" if title else nct
                add_title(title)

    return out[:8]


def _build_assistant_message(disease: str, ranked: list[RankedCandidate], source: str) -> str:
    if not ranked:
        return (
            "I can help with drug repurposing analysis. Tell me the disease or condition you "
            "want to investigate, and optionally subtype/markers."
        )
    lines = [
        f"I analyzed repurposing candidates for **{disease}** ({source}). Top results:",
        "",
    ]
    for idx, c in enumerate(ranked[:5], 1):
        lines.append(f"{idx}. **{c.drug}** (Score: {c.overallScore:.2f})")
    lines.append("")
    lines.append("Each candidate integrates clinical, KG, FAERS, and molecular signals.")
    return "\n".join(lines)


def infer_disease_from_message(message: str, precomputed_root: Path) -> str | None:
    msg = (message or "").strip()
    if not msg:
        return None

    lower = msg.lower()
    bundles: list[str] = []
    if precomputed_root.exists():
        bundles = [p.name for p in precomputed_root.iterdir() if p.is_dir() and p.name != "tool_cache"]
    for b in bundles:
        if normalize_disease_name(b) in lower:
            return normalize_disease_name(b)

    for pat in [
        r"\bfor\s+([a-z0-9][a-z0-9\-\s']{2,80})",
        r"\babout\s+([a-z0-9][a-z0-9\-\s']{2,80})",
        r"\bon\s+([a-z0-9][a-z0-9\-\s']{2,80})",
    ]:
        m = re.search(pat, lower)
        if m:
            value = m.group(1).strip(" .,!?:;")
            # Trim trailing words common in questions.
            value = re.sub(r"\b(repurpose|repurposing|candidates|drugs|therapy|treatment)\b.*$", "", value).strip()
            if value:
                return normalize_disease_name(value)

    # Fallback: handle short direct inputs like "pancreatic cancer" or "glioma".
    cleaned = re.sub(r"[^a-z0-9\s\-']", " ", lower)
    cleaned = " ".join(cleaned.split())
    cleaned = re.sub(
        r"^(show|find|give|list|what|which|help|analyze|analyse|investigate|tell)\b",
        "",
        cleaned,
    ).strip()
    cleaned = re.sub(
        r"\b(repurposing|repurpose|candidate|candidates|drug|drugs|for|about|on|please)\b",
        " ",
        cleaned,
    )
    tokens = [t for t in cleaned.split() if t]
    stopwords = {
        "a",
        "an",
        "and",
        "any",
        "can",
        "could",
        "do",
        "for",
        "help",
        "i",
        "in",
        "is",
        "it",
        "me",
        "my",
        "need",
        "of",
        "on",
        "please",
        "show",
        "tell",
        "that",
        "the",
        "this",
        "to",
        "us",
        "want",
        "we",
        "what",
        "which",
        "with",
        "you",
    }
    tokens = [t for t in tokens if t not in stopwords]
    if tokens and 1 <= len(tokens) <= 6:
        return normalize_disease_name(" ".join(tokens))
    return None


def build_artifacts_from_bundle(
    *,
    disease: str,
    subtype: str | None,
    bundle_root: Path,
    source: str,
) -> Artifacts:
    missing: list[str] = []
    warnings: list[str] = []

    candidates_json = load_json_safe(bundle_root / "candidates.json", missing, warnings)
    ct_json = load_json_safe(bundle_root / "evidence" / "clinical_trials.json", missing, warnings)
    faers_json = load_json_safe(bundle_root / "evidence" / "faers_signals.json", missing, warnings)
    literature_json = load_json_safe(bundle_root / "evidence" / "literature.json", missing, warnings)
    molecular_json = load_json_safe(bundle_root / "evidence" / "molecular.json", missing, warnings)
    verdict_json = load_json_safe(bundle_root / "court" / "verdict_scores.json", missing, warnings)

    candidates = candidates_json.get("candidates", []) if candidates_json else []
    candidate_by_drug = {
        str(item.get("drug_name", "")).upper(): item
        for item in candidates
        if isinstance(item, dict) and item.get("drug_name")
    }

    ct_results = _upper_key_map(ct_json.get("results", {}) if ct_json else {})
    faers_results = _upper_key_map(faers_json.get("results", {}) if faers_json else {})
    lit_results = _upper_key_map(literature_json.get("results", {}) if literature_json else {})
    mol_results = _upper_key_map(molecular_json.get("results", {}) if molecular_json else {})

    ranked_drugs: list[tuple[str, float, dict[str, Any]]] = []
    verdicts = verdict_json.get("verdicts", []) if verdict_json else []
    if isinstance(verdicts, list) and verdicts:
        for v in verdicts:
            if not isinstance(v, dict):
                continue
            drug = str(v.get("drug_name", "")).upper()
            if not drug:
                continue
            score = float(v.get("rescue_score", 0.0)) / 100.0
            ranked_drugs.append((drug, max(0.0, min(1.0, score)), v))
    else:
        for item in candidates[:8]:
            if not isinstance(item, dict):
                continue
            drug = str(item.get("drug_name", "")).upper()
            if not drug:
                continue
            score = float(item.get("kg_normalized", 0.0) or 0.0)
            ranked_drugs.append((drug, max(0.0, min(1.0, score)), {}))

    ranked_candidates: list[RankedCandidate] = []
    for drug_key, score, verdict_row in ranked_drugs[:8]:
        candidate = candidate_by_drug.get(drug_key, {})
        ct_row = ct_results.get(drug_key, {})
        faers_row = faers_results.get(drug_key, {})
        lit_row = lit_results.get(drug_key, {})
        mol_row = mol_results.get(drug_key, {})

        termination_reason, why_stopped = _first_trial_payload(ct_row if isinstance(ct_row, dict) else {})

        kg_relation = str(candidate.get("kg_relation", "")).strip()
        kg_targets = [kg_relation] if kg_relation else []

        sim_info = mol_row.get("similarity_to_approved", {}) if isinstance(mol_row, dict) else {}
        dock_target = None
        dock_conf = None
        if isinstance(sim_info, dict):
            dock_target = sim_info.get("max_similar_drug")
            try:
                dock_conf = float(sim_info.get("max_tanimoto")) if sim_info.get("max_tanimoto") is not None else None
            except Exception:  # noqa: BLE001
                dock_conf = None

        safety_flags: list[str] = []
        if isinstance(verdict_row, dict):
            risks = verdict_row.get("risks", [])
            if isinstance(risks, list):
                safety_flags.extend(str(x) for x in risks[:3])
        if isinstance(ct_row, dict) and int(ct_row.get("safety_flags", 0) or 0) > 0:
            safety_flags.append("safety_flags_in_trials")
        safety_flags = [x for x in dict.fromkeys(safety_flags) if x]

        ranked_candidates.append(
            RankedCandidate(
                drug=drug_key.title(),
                overallScore=round(score, 2),
                signals=Signals(
                    trials=TrialSignal(
                        terminationReason=(termination_reason or None),
                        whyStopped=(why_stopped or None),
                    ),
                    kg=KGSignal(
                        score=float(candidate.get("kg_normalized", 0.0) or 0.0) if candidate else None,
                        topTargets=kg_targets,
                    ),
                    faers=FAERSSignal(
                        inverseSignal=(
                            bool(faers_row.get("has_inverse_signal"))
                            if isinstance(faers_row, dict)
                            else None
                        ),
                        ror=(
                            float(faers_row.get("ror"))
                            if isinstance(faers_row, dict) and faers_row.get("ror") is not None
                            else None
                        ),
                        ci95=[
                            faers_row.get("ci_lower") if isinstance(faers_row, dict) else None,
                            faers_row.get("ci_upper") if isinstance(faers_row, dict) else None,
                        ],
                    ),
                    dock=DockSignal(target=str(dock_target) if dock_target else None, confidence=dock_conf),
                ),
                safetyFlags=safety_flags,
                citations=_extract_citations(
                    lit_row if isinstance(lit_row, dict) else None,
                    ct_row if isinstance(ct_row, dict) else None,
                ),
            )
        )

    meta: dict[str, Any] = {
        "source": source,
        "bundleRoot": str(bundle_root),
        "missingArtifacts": missing,
    }
    if warnings:
        meta["warnings"] = warnings

    return Artifacts(
        query=QueryArtifact(disease=disease, subtype=subtype),
        rankedCandidates=ranked_candidates,
        meta=meta,
    )


def build_chat_response(
    *,
    conversation_id: str,
    disease: str,
    subtype: str | None,
    artifacts: Artifacts,
    source: str,
) -> ChatResponse:
    return ChatResponse(
        conversationId=conversation_id,
        assistantMessage=_build_assistant_message(disease=disease, ranked=artifacts.rankedCandidates, source=source),
        artifacts=artifacts,
    )


def build_followup_response(conversation_id: str, reason: str) -> ChatResponse:
    return ChatResponse(
        conversationId=conversation_id,
        assistantMessage=(
            "I'd love to help you explore drug repurposing candidates. "
            "Tell me the disease/condition and optional subtype/markers."
        ),
        artifacts=Artifacts(
            query=QueryArtifact(disease="unknown"),
            rankedCandidates=[],
            meta={"reason": reason},
        ),
    )
