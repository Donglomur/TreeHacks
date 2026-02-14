"""
DrugRescue AI — Adversarial Evidence Court
===========================================
TreeHacks 2026

5-agent architecture with adversarial synthesis:

    Orchestrator (Task only)
    ├── Phase 1: Discovery      → KG scoring → files/candidates.json
    ├── Phase 2: Investigator   → ALL evidence tools → files/evidence/
    ├── Phase 3: Advocate ┐     → files/court/advocate_brief.md
    │            Skeptic  ┘     → files/court/skeptic_brief.md     (PARALLEL)
    └── Phase 4: Judge          → files/court/verdict.md + verdict_scores.json

The adversarial court is the showpiece:
    - Advocate builds the strongest case FOR repurposing
    - Skeptic builds the strongest case AGAINST repurposing
    - Judge weighs both sides and assigns Rescue Scores (0-100)

Usage:
    python -m drug_rescue --disease glioblastoma
    python -m drug_rescue
    python -m drug_rescue --disease glioblastoma --standalone
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    from claude_agent_sdk import (
        ClaudeAgentOptions,
        ClaudeSDKClient,
        AgentDefinition,
        HookMatcher,
        AssistantMessage,
        ResultMessage,
        TextBlock,
        create_sdk_mcp_server,
    )
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

from .tools import ALL_TOOLS, ALL_TOOL_NAMES, configure_tools
from .prompts import (
    ORCHESTRATOR_PROMPT,
    DISCOVERY_PROMPT,
    INVESTIGATOR_PROMPT,
    ADVOCATE_PROMPT,
    SKEPTIC_PROMPT,
    JUDGE_PROMPT,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TOOL SUBSETS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DISCOVERY_TOOLS = [
    "mcp__drugrescue__discover_candidates",
    "mcp__drugrescue__score_specific_drugs",
    "mcp__drugrescue__kg_info",
    "Write",
]

INVESTIGATOR_TOOLS = [
    "mcp__drugrescue__clinical_trial_failure",
    "mcp__drugrescue__faers_inverse_signal",
    "mcp__drugrescue__faers_suggest_events",
    "mcp__drugrescue__literature_search",
    "mcp__drugrescue__molecular_similarity",
    "mcp__drugrescue__molecular_docking",
    "Read", "Write", "Glob",
]

# Court agents: READ-ONLY evidence access + write their briefs
COURT_TOOLS = ["Read", "Write", "Glob"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AGENT DEFINITIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_agents() -> dict[str, AgentDefinition]:
    """Define all 5 subagents for the court architecture."""
    return {
        # Phase 1: Discovery
        "discovery": AgentDefinition(
            description=(
                "Use FIRST. Scores all ~24,000 compounds in DRKG against the "
                "target disease. Writes ranked candidates with drug names, SMILES, "
                "status, and KG scores to files/candidates.json. "
                "MUST complete before investigator runs."
            ),
            tools=DISCOVERY_TOOLS,
            prompt=DISCOVERY_PROMPT,
            model="sonnet",
        ),

        # Phase 2: Investigation
        "investigator": AgentDefinition(
            description=(
                "Use AFTER discovery. Reads candidates from files/candidates.json "
                "and gathers evidence using ALL sources: clinical trials (why dropped?), "
                "FAERS (inverse signals?), literature (published support?), and molecular "
                "analysis (structural similarity + docking). Writes structured evidence "
                "to files/evidence/. MUST complete before court phase."
            ),
            tools=INVESTIGATOR_TOOLS,
            prompt=INVESTIGATOR_PROMPT,
            model="sonnet",
        ),

        # Phase 3: Adversarial Court (these two run IN PARALLEL)
        "advocate": AgentDefinition(
            description=(
                "Use AFTER investigator, IN PARALLEL with skeptic. "
                "Reads ALL evidence from files/evidence/ and builds the "
                "strongest possible case FOR repurposing each top candidate. "
                "Writes files/court/advocate_brief.md."
            ),
            tools=COURT_TOOLS,
            prompt=ADVOCATE_PROMPT,
            model="sonnet",
        ),

        "skeptic": AgentDefinition(
            description=(
                "Use AFTER investigator, IN PARALLEL with advocate. "
                "Reads ALL evidence from files/evidence/ and builds the "
                "strongest possible case AGAINST repurposing each top candidate. "
                "Writes files/court/skeptic_brief.md."
            ),
            tools=COURT_TOOLS,
            prompt=SKEPTIC_PROMPT,
            model="sonnet",
        ),

        # Phase 4: Judgment
        "judge": AgentDefinition(
            description=(
                "Use LAST, after both advocate and skeptic complete. "
                "Reads advocate_brief.md, skeptic_brief.md, and raw evidence. "
                "Weighs both arguments, fact-checks claims, and produces a "
                "final verdict with Rescue Scores (0-100) per drug. "
                "Writes files/court/verdict.md and verdict_scores.json."
            ),
            tools=COURT_TOOLS,
            prompt=JUDGE_PROMPT,
            model="sonnet",
        ),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PIPELINE LOGGER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PHASE_MAP = {
    "discovery":    ("🔬", "Phase 1: Discovery"),
    "investigator": ("🔎", "Phase 2: Investigation"),
    "advocate":     ("✅", "Phase 3: Advocate"),
    "skeptic":      ("🔴", "Phase 3: Skeptic"),
    "judge":        ("⚖️", "Phase 4: Judgment"),
}


class PipelineLogger:
    """Logs pipeline progress to console and transcript file."""

    def __init__(self):
        self.start_time = datetime.now()
        self.log_dir = Path("logs") / f"session_{self.start_time:%Y%m%d_%H%M%S}"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._log = open(self.log_dir / "transcript.txt", "w", encoding="utf-8")
        self._current_agent = "ORCHESTRATOR"
        self._agents_spawned = []

    def agent_spawned(self, agent_type: str, description: str):
        emoji, phase = PHASE_MAP.get(agent_type, ("🤖", agent_type))
        self._current_agent = agent_type.upper()
        self._agents_spawned.append(agent_type)
        msg = f"\n{'='*60}\n  {emoji} {self._current_agent} — {phase}\n  {description}\n{'='*60}\n"
        self._write(msg)

    def tool_call(self, tool_name: str):
        display = tool_name.replace("mcp__drugrescue__", "")
        self._write(f"  [{self._current_agent}] → {display}\n")

    def text(self, text: str):
        self._write(text)

    def _write(self, text: str):
        print(text, end="", flush=True)
        self._log.write(text)
        self._log.flush()

    def close(self):
        elapsed = datetime.now() - self.start_time
        footer = (
            f"\n\n{'='*60}\n"
            f"  Pipeline: {' → '.join(self._agents_spawned)}\n"
            f"  Duration: {elapsed.total_seconds():.1f}s\n"
            f"{'='*60}\n"
        )
        self._write(footer)
        self._log.close()


def process_message(msg, logger: PipelineLogger):
    """Process AssistantMessage from SDK stream."""
    for block in msg.content:
        name = type(block).__name__
        if name == "TextBlock":
            logger.text(block.text)
        elif name == "ToolUseBlock":
            if block.name == "Task":
                agent_type = block.input.get("subagent_type", "unknown")
                desc = block.input.get("description", "")
                logger.agent_spawned(agent_type, desc)
            else:
                logger.tool_call(block.name)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CLIENT SETUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_options(data_dir: str = "./data") -> ClaudeAgentOptions:
    """Build options for the court pipeline."""
    configure_tools(data_dir=data_dir)

    server = create_sdk_mcp_server(
        name="drugrescue",
        version="1.0.0",
        tools=ALL_TOOLS,
    )

    return ClaudeAgentOptions(
        system_prompt=ORCHESTRATOR_PROMPT,
        mcp_servers={"drugrescue": server},
        allowed_tools=["Task"],  # Orchestrator delegates only
        agents=build_agents(),
        permission_mode="bypassPermissions",
        max_turns=50,
        model="sonnet",
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  RUN MODES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def run_agent(disease: str, data_dir: str = "./data") -> str:
    """One-shot: full pipeline with adversarial court."""
    if not SDK_AVAILABLE:
        raise ImportError("pip install 'drug-rescue[agent]'")

    options = create_options(data_dir)
    logger = PipelineLogger()
    result_text = ""

    prompt = (
        f"Investigate drug repurposing candidates for **{disease}**.\n\n"
        f"Run the full pipeline:\n"
        f"1. Discover candidates from the knowledge graph\n"
        f"2. Investigate top candidates with all evidence tools\n"
        f"3. Run adversarial court: advocate argues FOR, skeptic argues AGAINST (in parallel)\n"
        f"4. Judge delivers final verdict with Rescue Scores"
    )

    print(f"\n{'='*60}")
    print(f"  🧬 DrugRescue AI — Adversarial Evidence Court")
    print(f"  Disease: {disease}")
    print(f"  Pipeline: discovery → investigator → advocate|skeptic → judge")
    print(f"{'='*60}\n")

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    process_message(msg, logger)
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            result_text += block.text
                elif isinstance(msg, ResultMessage):
                    logger.text(
                        f"\n\n  ✅ Court adjourned — turns: {msg.num_turns}, "
                        f"cost: ${msg.total_cost_usd:.4f}\n"
                    )
    finally:
        logger.close()
        print(f"\nSession logs: {logger.log_dir}")
        print(f"Verdict: files/court/verdict.md")

    return result_text


async def run_interactive(data_dir: str = "./data"):
    """Multi-turn chat with the orchestrator."""
    if not SDK_AVAILABLE:
        raise ImportError("pip install 'drug-rescue[agent]'")

    options = create_options(data_dir)
    logger = PipelineLogger()

    print(f"\n{'='*60}")
    print("  🧬 DrugRescue AI — Adversarial Evidence Court")
    print(f"{'='*60}")
    print("\nExamples:")
    print('  "Investigate glioblastoma"')
    print('  "Find repurposing candidates for Alzheimer\'s"')
    print('\nType "quit" to exit.\n')

    try:
        async with ClaudeSDKClient(options=options) as client:
            while True:
                try:
                    user_input = input("\nYou: ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if user_input.lower() in ("quit", "exit", "q"):
                    break
                if not user_input:
                    continue

                await client.query(user_input)
                async for msg in client.receive_response():
                    if isinstance(msg, AssistantMessage):
                        process_message(msg, logger)
                    elif isinstance(msg, ResultMessage):
                        logger.text(
                            f"\n  [turns: {msg.num_turns}, cost: ${msg.total_cost_usd:.4f}]\n"
                        )
    finally:
        logger.close()
        print(f"\nSession logs: {logger.log_dir}")


async def run_standalone(disease: str, data_dir: str = "./data"):
    """Run KG discovery directly without Claude SDK."""
    configure_tools(data_dir)
    from .tools.kg_discovery import discover_candidates_tool, kg_info_tool

    print(f"\n{'='*60}")
    print(f"  DrugRescue — Standalone (no SDK)")
    print(f"  Disease: {disease}")
    print(f"{'='*60}\n")

    info_result = await kg_info_tool({})
    info = json.loads(info_result["content"][0]["text"])
    print(f"Graph: {info.get('compounds', '?')} compounds, "
          f"{info.get('diseases', '?')} diseases\n")

    print(f"Scoring compounds against '{disease}'...")
    result = await discover_candidates_tool({
        "disease": disease, "max_candidates": 30,
        "min_percentile": 75.0, "include_novel": True,
    })
    data = json.loads(result["content"][0]["text"])

    if "error" in data and "candidates" not in data:
        print(f"  Error: {data['error']}")
        return

    print(f"  Scored {data['total_compounds_scored']:,} in {data['timing_ms']:.0f}ms")
    print(f"  {data['candidates_returned']} candidates\n")

    for i, c in enumerate(data["candidates"][:15], 1):
        smiles = "✓" if c.get("smiles") else "—"
        print(f"  {i:<3} {c['drug_name'][:26]:<28} {c['status']:<10} "
              f"pctl={c['kg_percentile']:.1f}  smiles={smiles}")

    print(f"\nFull pipeline: python -m drug_rescue -d \"{disease}\"\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    parser = argparse.ArgumentParser(
        description="DrugRescue AI — Adversarial Evidence Court"
    )
    parser.add_argument("--disease", "-d", type=str,
                        help="Disease to investigate")
    parser.add_argument("--data-dir", type=str, default="./data")
    parser.add_argument("--standalone", "-s", action="store_true",
                        help="KG only, no SDK")
    args = parser.parse_args()

    if args.standalone or not SDK_AVAILABLE:
        if not SDK_AVAILABLE and not args.standalone:
            print("⚠️  claude-agent-sdk not installed — standalone mode")
        asyncio.run(run_standalone(args.disease or "glioblastoma", args.data_dir))
    elif args.disease:
        asyncio.run(run_agent(args.disease, args.data_dir))
    else:
        asyncio.run(run_interactive(args.data_dir))


if __name__ == "__main__":
    main()
