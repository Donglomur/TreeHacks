"""File-backed cache helpers for tool call outputs."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CACHE_ROOT = Path("files") / "tool_cache"


def _canonical_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _cache_path(tool_name: str, args: dict[str, Any]) -> Path:
    digest = hashlib.sha256(_canonical_payload(args).encode("utf-8")).hexdigest()
    return _CACHE_ROOT / tool_name / f"{digest}.json"


def load_cached_output(tool_name: str, args: dict[str, Any]) -> dict[str, Any] | None:
    path = _cache_path(tool_name, args)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read cache for %s: %s", tool_name, exc)
        return None
    if not isinstance(payload, dict) or "output" not in payload:
        return None
    output = payload["output"]
    if isinstance(output, dict):
        logger.info("CACHE HIT %s -> %s", tool_name, path)
        print(f"CACHE HIT {tool_name} -> {path}", flush=True)
        output = dict(output)
        output.setdefault("_cache", {})
        output["_cache"]["hit"] = True
        output["_cache"]["path"] = str(path)
        output["_cache"]["created_at"] = payload.get("created_at")
    return output if isinstance(output, dict) else None


def save_cached_output(tool_name: str, args: dict[str, Any], output: dict[str, Any]) -> None:
    path = _cache_path(tool_name, args)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "tool": tool_name,
        "args": args,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "output": output,
    }
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    logger.info("CACHE SAVE %s -> %s", tool_name, path)
    print(f"CACHE SAVE {tool_name} -> {path}", flush=True)


def load_latest_by_field(
    tool_name: str,
    field: str,
    expected_value: Any,
) -> dict[str, Any] | None:
    """Fallback lookup: latest cache entry with args[field] == expected_value."""
    folder = _CACHE_ROOT / tool_name
    if not folder.exists():
        return None

    candidates = sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        args = payload.get("args", {})
        if not isinstance(args, dict):
            continue
        if args.get(field) != expected_value:
            continue
        output = payload.get("output")
        if not isinstance(output, dict):
            continue
        logger.info("CACHE HIT %s (%s match) -> %s", tool_name, field, path)
        print(f"CACHE HIT {tool_name} ({field} match) -> {path}", flush=True)
        output = dict(output)
        output.setdefault("_cache", {})
        output["_cache"]["hit"] = True
        output["_cache"]["path"] = str(path)
        output["_cache"]["created_at"] = payload.get("created_at")
        output["_cache"]["fallback"] = f"{field}_match"
        return output
    return None
