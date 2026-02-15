import importlib
from typing import Any

import pytest


fastapi = pytest.importorskip("fastapi")
pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient


def _load_server_module():
    import drug_rescue.server as server

    return importlib.reload(server)


def test_health_endpoint(monkeypatch):
    monkeypatch.setenv("DRUGRESCUE_PRECOMPUTED_ROOT", "files")
    monkeypatch.setenv("DRUGRESCUE_ALLOW_LIVE_FALLBACK", "false")
    server = _load_server_module()
    client = TestClient(server.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_artifacts_endpoint_glioblastoma(monkeypatch):
    monkeypatch.setenv("DRUGRESCUE_PRECOMPUTED_ROOT", "files")
    monkeypatch.setenv("DRUGRESCUE_ALLOW_LIVE_FALLBACK", "false")
    server = _load_server_module()
    client = TestClient(server.app)
    resp = client.get("/v1/artifacts", params={"disease": "glioblastoma"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["query"]["disease"] == "glioblastoma"
    assert len(payload["rankedCandidates"]) > 0


def test_chat_endpoint_uses_precomputed(monkeypatch):
    monkeypatch.setenv("DRUGRESCUE_PRECOMPUTED_ROOT", "files")
    monkeypatch.setenv("DRUGRESCUE_ALLOW_LIVE_FALLBACK", "false")
    monkeypatch.setenv("DRUGRESCUE_DEFAULT_CONVERSATION_ID", "c_test")
    server = _load_server_module()
    client = TestClient(server.app)
    resp = client.post(
        "/v1/chat",
        json={
            "conversationId": "c_abc",
            "message": "show me repurposing candidates for glioblastoma",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["conversationId"] == "c_abc"
    assert "assistantMessage" in payload
    assert payload["artifacts"]["query"]["disease"] == "glioblastoma"


def test_chat_endpoint_requires_detectable_disease(monkeypatch):
    monkeypatch.setenv("DRUGRESCUE_PRECOMPUTED_ROOT", "files")
    monkeypatch.setenv("DRUGRESCUE_ALLOW_LIVE_FALLBACK", "true")
    server = _load_server_module()
    client = TestClient(server.app)
    resp = client.post(
        "/v1/chat",
        json={
            "conversationId": "c_abc",
            "message": "help me with repurposing",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["artifacts"]["query"]["disease"] == "unknown"
    assert payload["artifacts"]["meta"]["reason"] == "disease_not_detected"


def test_chat_endpoint_live_fallback_uses_requested_disease(monkeypatch):
    monkeypatch.setenv("DRUGRESCUE_PRECOMPUTED_ROOT", "files")
    monkeypatch.setenv("DRUGRESCUE_ALLOW_LIVE_FALLBACK", "true")
    server = _load_server_module()

    seen: dict[str, Any] = {}

    async def _fake_live(message: str, disease_hint: str | None, subtype: str | None):
        seen["message"] = message
        seen["disease_hint"] = disease_hint
        seen["subtype"] = subtype
        return server.Artifacts(
            query={"disease": "pancreatic cancer", "subtype": subtype},
            rankedCandidates=[],
            meta={"source": "live"},
        )

    monkeypatch.setattr(server, "_live_artifacts_for", _fake_live)

    client = TestClient(server.app)
    resp = client.post(
        "/v1/chat",
        json={
            "conversationId": "c_live",
            "message": "show repurposing candidates for pancreatic cancer",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert seen["disease_hint"] == "pancreatic cancer"
    assert payload["artifacts"]["query"]["disease"] == "pancreatic cancer"
