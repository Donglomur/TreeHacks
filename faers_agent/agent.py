"""Claude-facing wrapper for the FAERS detector."""

from __future__ import annotations

import asyncio
from typing import Any

from .client import OpenFDAClient
from .detector import FAERSDetector


class ClaudeFAERSAgent:
    """Tool-style wrapper designed to plug into a Claude SDK orchestrator."""

    SCREEN_TOOL_NAME = "faers_inverse_signal_detector"
    SUGGEST_EVENTS_TOOL_NAME = "faers_suggest_events"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        timeout: float = 20.0,
        max_concurrent: int = 5,
        delay_between_calls: float = 0.25,
    ) -> None:
        client = OpenFDAClient(
            api_key=api_key,
            timeout=timeout,
            delay_between_calls=delay_between_calls,
        )
        self.detector = FAERSDetector(client=client, max_concurrent=max_concurrent)

    @classmethod
    def screen_tool_definition(cls) -> dict[str, Any]:
        return {
            "name": cls.SCREEN_TOOL_NAME,
            "description": (
                "Screen candidate drugs against a disease in FAERS and detect inverse "
                "signals (protective association) using Reporting Odds Ratio (ROR)."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "disease": {"type": "string"},
                    "candidate_drugs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                    },
                    "disease_events": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "alpha": {"type": "number", "default": 0.05},
                    "correction": {
                        "type": "string",
                        "enum": ["none", "bonferroni", "fdr"],
                        "default": "none",
                    },
                },
                "required": ["disease", "candidate_drugs"],
                "additionalProperties": False,
            },
        }

    @classmethod
    def suggest_events_tool_definition(cls) -> dict[str, Any]:
        return {
            "name": cls.SUGGEST_EVENTS_TOOL_NAME,
            "description": (
                "Fetch top MedDRA Preferred Terms from OpenFDA FAERS for a given drug "
                "or globally when no drug is provided."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "drug": {"type": ["string", "null"]},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 10},
                },
                "additionalProperties": False,
            },
        }

    @classmethod
    def tool_definitions(cls) -> list[dict[str, Any]]:
        return [cls.screen_tool_definition(), cls.suggest_events_tool_definition()]

    @classmethod
    def tool_definition(cls) -> dict[str, Any]:
        """Backward-compatible single tool definition."""
        return cls.screen_tool_definition()

    async def arun_screen(self, payload: dict[str, Any]) -> dict[str, Any]:
        disease = payload["disease"]
        drugs = payload["candidate_drugs"]
        disease_events = payload.get("disease_events")
        alpha = float(payload.get("alpha", 0.05))
        correction = payload.get("correction", "none")

        result = await self.detector.screen_drugs(
            drug_names=drugs,
            disease=disease,
            disease_events=disease_events,
            alpha=alpha,
            correction=correction,
        )
        return result.to_dict()

    async def arun_suggest_events(self, payload: dict[str, Any]) -> dict[str, Any]:
        drug = payload.get("drug")
        limit = int(payload.get("limit", 10))
        terms = await self.detector.client.top_event_terms(drug=drug, limit=limit)
        return {
            "drug": drug,
            "limit": max(1, min(limit, 1000)),
            "events": [{"term": term, "count": count} for term, count in terms],
        }

    async def arun(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Backward-compatible runner for screening."""
        return await self.arun_screen(payload)

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return asyncio.run(self.arun(payload))

    async def handle_tool_call(self, name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        if name == self.SCREEN_TOOL_NAME:
            return await self.arun_screen(tool_input)
        if name == self.SUGGEST_EVENTS_TOOL_NAME:
            return await self.arun_suggest_events(tool_input)
        raise ValueError(f"Unknown tool: {name}")
