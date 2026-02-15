"""HTTP API server for frontend integration."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .agent import SDK_AVAILABLE, run_agent
from .api_adapter import (
    build_artifacts_from_bundle,
    build_chat_response,
    build_followup_response,
    find_precomputed_bundle,
    infer_disease_from_message,
    normalize_disease_name,
)
from .api_types import Artifacts, ChatRequest, ChatResponse

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    # Load local .env for API keys when running via uvicorn.
    load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _load_settings() -> dict[str, Any]:
    return {
        "precomputed_root": Path(os.getenv("DRUGRESCUE_PRECOMPUTED_ROOT", "files")),
        "allow_live_fallback": _env_bool("DRUGRESCUE_ALLOW_LIVE_FALLBACK", default=True),
        "default_conversation_id": os.getenv("DRUGRESCUE_DEFAULT_CONVERSATION_ID", "c_123"),
        "data_dir": os.getenv("DRUGRESCUE_DATA_DIR", "./data"),
        "live_timeout_sec": float(os.getenv("DRUGRESCUE_LIVE_TIMEOUT_SEC", "900")),
    }


SETTINGS = _load_settings()
app = FastAPI(title="DrugRescue API", version="1.0.0")

cors = os.getenv("DRUGRESCUE_CORS_ORIGINS", "").strip()
if cors:
    origins = ["*"] if cors == "*" else [x.strip() for x in cors.split(",") if x.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )


def _read_live_disease(root: Path, default: str | None = None) -> str | None:
    path = root / "candidates.json"
    if not path.exists():
        return default
    try:
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
        disease = str(payload.get("disease", "")).strip()
        return normalize_disease_name(disease) if disease else default
    except Exception:  # noqa: BLE001
        return default


def _artifact_stamp(root: Path) -> tuple[int | None, int | None]:
    path = root / "candidates.json"
    if not path.exists():
        return None, None
    try:
        stat = path.stat()
        return stat.st_mtime_ns, stat.st_size
    except Exception:  # noqa: BLE001
        return None, None


def _precomputed_artifacts_for(disease: str, subtype: str | None) -> Artifacts | None:
    bundle = find_precomputed_bundle(disease, SETTINGS["precomputed_root"])
    if bundle is None:
        return None
    return build_artifacts_from_bundle(
        disease=normalize_disease_name(disease),
        subtype=subtype,
        bundle_root=bundle,
        source="precomputed",
    )


async def _live_artifacts_for(message: str, disease_hint: str | None, subtype: str | None) -> Artifacts:
    if not disease_hint:
        raise ValueError("disease_not_detected")
    target_disease = normalize_disease_name(disease_hint)
    artifacts_root = SETTINGS["precomputed_root"]
    before_stamp = _artifact_stamp(artifacts_root)

    run_result = await asyncio.wait_for(
        run_agent(target_disease, SETTINGS["data_dir"]),
        timeout=SETTINGS["live_timeout_sec"],
    )
    if "not logged in" in (run_result or "").lower():
        raise RuntimeError("auth_required")

    after_stamp = _artifact_stamp(artifacts_root)
    if before_stamp == after_stamp:
        raise RuntimeError("live_no_fresh_artifacts")

    live_disease = _read_live_disease(artifacts_root, target_disease) or target_disease
    if normalize_disease_name(live_disease) != target_disease:
        raise RuntimeError("disease_too_broad_or_unsupported")

    return build_artifacts_from_bundle(
        disease=target_disease,
        subtype=subtype,
        bundle_root=artifacts_root,
        source="live",
    )


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/v1/artifacts", response_model=Artifacts)
async def get_artifacts(
    disease: str = Query(..., description="Disease to investigate"),
    subtype: str | None = Query(None, description="Optional subtype/marker"),
) -> Artifacts:
    precomputed = _precomputed_artifacts_for(disease, subtype)
    if precomputed is not None:
        return precomputed

    if SETTINGS["allow_live_fallback"]:
        try:
            return await _live_artifacts_for(
                message=f"Investigate drug repurposing candidates for {disease}.",
                disease_hint=normalize_disease_name(disease),
                subtype=subtype,
            )
        except Exception as exc:  # noqa: BLE001
            out = build_followup_response(
                SETTINGS["default_conversation_id"],
                reason=f"live_fallback_failed:{exc}",
            )
            assert out.artifacts is not None
            return out.artifacts

    out = build_followup_response(
        SETTINGS["default_conversation_id"],
        reason="precomputed_bundle_missing",
    )
    assert out.artifacts is not None
    return out.artifacts


@app.post("/v1/chat", response_model=ChatResponse)
async def post_chat(body: ChatRequest) -> ChatResponse:
    conversation_id = body.conversationId or SETTINGS["default_conversation_id"]
    message = body.message or ""
    subtype = body.subtype

    disease = (
        normalize_disease_name(body.disease)
        if body.disease
        else infer_disease_from_message(message, SETTINGS["precomputed_root"])
    )

    if not disease:
        return build_followup_response(
            conversation_id=conversation_id,
            reason="disease_not_detected",
        )

    if disease:
        precomputed = _precomputed_artifacts_for(disease, subtype)
        if precomputed is not None:
            return build_chat_response(
                conversation_id=conversation_id,
                disease=disease,
                subtype=subtype,
                artifacts=precomputed,
                source="precomputed",
            )

    if SETTINGS["allow_live_fallback"]:
        try:
            live_artifacts = await _live_artifacts_for(
                message=message,
                disease_hint=disease,
                subtype=subtype,
            )
            live_disease = live_artifacts.query.disease
            return build_chat_response(
                conversation_id=conversation_id,
                disease=live_disease,
                subtype=subtype,
                artifacts=live_artifacts,
                source="live",
            )
        except Exception as exc:  # noqa: BLE001
            return build_followup_response(
                conversation_id=conversation_id,
                reason=f"live_fallback_failed:{exc}",
            )

    return build_followup_response(
        conversation_id=conversation_id,
        reason="precomputed_bundle_missing",
    )
