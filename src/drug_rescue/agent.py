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
import shutil
import sys
import time
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

    def __init__(self, print_delay: float = 0.0):
        self.start_time = datetime.now()
        self.log_dir = Path("logs") / f"session_{self.start_time:%Y%m%d_%H%M%S}"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._log = open(self.log_dir / "transcript.txt", "w", encoding="utf-8")
        self._current_agent = "ORCHESTRATOR"
        self._agents_spawned = []
        self._print_delay = max(0.0, float(print_delay))

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
        if not text:
            return
        chunks = text.splitlines(keepends=True)
        if not chunks:
            chunks = [text]
        for chunk in chunks:
            print(chunk, end="", flush=True)
            self._log.write(chunk)
            self._log.flush()
            if self._print_delay > 0:
                time.sleep(self._print_delay)

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

    archived_count = 0
    archived_bundle = Path("files") / _normalize_disease_name(disease).replace(" ", "_")
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
        try:
            archived_count, archived_bundle = _archive_live_outputs(disease, Path("files"))
        except Exception:
            archived_count = 0
        logger.close()
        print(f"\nSession logs: {logger.log_dir}")
        print(f"Verdict: files/court/verdict.md")
        if archived_count > 0:
            print(f"Saved demo bundle: {archived_bundle} ({archived_count} files)")

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


def _normalize_disease_name(value: str) -> str:
    return " ".join(value.lower().strip().replace("_", " ").replace("-", " ").split())


def _find_precomputed_bundle(disease: str, root: Path) -> Path | None:
    if not root.exists():
        return None

    normalized = _normalize_disease_name(disease)
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

    # Fallback: normalize existing folder names and compare.
    for p in root.iterdir():
        if p.is_dir() and _normalize_disease_name(p.name) == normalized:
            return p
    return None


def _copy_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _archive_live_outputs(disease: str, root: Path = Path("files")) -> tuple[int, Path]:
    """
    Snapshot current pipeline outputs from files/ into files/<disease_slug>/...
    using the same layout as precomputed demo bundles.
    """
    normalized = _normalize_disease_name(disease)
    slug = normalized.replace(" ", "_")
    bundle = root / slug

    # Avoid archiving stale outputs from a previous disease run.
    candidates_path = root / "candidates.json"
    if not candidates_path.exists():
        return 0, bundle
    try:
        payload = json.loads(candidates_path.read_text(encoding="utf-8"))
        seen_disease = _normalize_disease_name(str(payload.get("disease", "")).strip())
        if seen_disease and seen_disease != normalized:
            return 0, bundle
    except Exception:
        return 0, bundle

    copied = 0
    mappings: list[tuple[Path, Path]] = [
        (root / "candidates.json", bundle / "candidates.json"),
        (root / "candidates_summary.md", bundle / "candidates_summary.md"),
        (root / "candidates.json", bundle / f"{slug}_candidates.json"),
        (root / "candidates_summary.md", bundle / f"{slug}_candidates_summary.md"),
        (root / "evidence" / "clinical_trials.json", bundle / "evidence" / "clinical_trials.json"),
        (root / "evidence" / "faers_signals.json", bundle / "evidence" / "faers_signals.json"),
        (root / "evidence" / "literature.json", bundle / "evidence" / "literature.json"),
        (root / "evidence" / "molecular.json", bundle / "evidence" / "molecular.json"),
        (root / "evidence" / "summary.json", bundle / "evidence" / "summary.json"),
        (root / "evidence" / "summary.md", bundle / "evidence" / "summary.md"),
        (root / "court" / "advocate_brief.md", bundle / "court" / "advocate_brief.md"),
        (root / "court" / "skeptic_brief.md", bundle / "court" / "skeptic_brief.md"),
        (root / "court" / "verdict.md", bundle / "court" / "verdict.md"),
        (root / "court" / "verdict_scores.json", bundle / "court" / "verdict_scores.json"),
    ]

    for src, dst in mappings:
        if _copy_if_exists(src, dst):
            copied += 1

    if copied:
        manifest = {
            "disease": normalized,
            "bundle": str(bundle),
            "created_at": datetime.now().isoformat(),
            "files_copied": copied,
        }
        (bundle / "bundle_manifest.json").write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8",
        )
        copied += 1

    return copied, bundle


def run_fast(disease: str, precomputed_root: str = "files") -> int:
    """Fast demo mode: replay full pipeline output from precomputed files."""
    root = Path(precomputed_root)
    bundle = _find_precomputed_bundle(disease, root)
    if bundle is None:
        print(f"❌ No precomputed bundle found for disease '{disease}' under {root}/")
        print("Expected e.g. files/<disease>/court/verdict.md")
        return 1

    normalized = _normalize_disease_name(disease).replace(" ", "_")
    logger = PipelineLogger(print_delay=1.0)
    copied = 0

    def copy_any(src_candidates: list[Path], dst: Path) -> bool:
        nonlocal copied
        for src in src_candidates:
            if _copy_if_exists(src, dst):
                copied += 1
                return True
        return False

    print(f"\n{'='*60}")
    print("  🧬 DrugRescue AI — Adversarial Evidence Court")
    print(f"  Disease: {disease}")
    print("  Pipeline: discovery → investigator → advocate|skeptic → judge")
    print(f"{'='*60}\n")

    logger.text(
        f"I'll run the complete DrugRescue pipeline for **{disease}**. "
        "Using precomputed artifacts for a fast demo replay.\n"
    )

    try:
        # Phase 1 — Discovery
        logger.agent_spawned("discovery", f"Discover {disease} candidates")
        logger.tool_call("mcp__drugrescue__discover_candidates")
        copy_any(
            [bundle / "candidates.json", bundle / f"{normalized}_candidates.json"],
            Path("files") / "candidates.json",
        )
        logger.tool_call("Write")
        copy_any(
            [bundle / "candidates_summary.md", bundle / f"{normalized}_candidates_summary.md"],
            Path("files") / "candidates_summary.md",
        )
        logger.tool_call("Write")
        logger.text("Phase 1 complete! Loaded precomputed candidate artifacts.\n")

        # Phase 2 — Investigation
        logger.agent_spawned("investigator", f"Investigate {disease} candidates")

        if _copy_if_exists(bundle / "evidence/clinical_trials.json", Path("files/evidence/clinical_trials.json")):
            copied += 1
            logger.tool_call("mcp__drugrescue__clinical_trial_failure")
            logger.text("  [INVESTIGATOR]   PRECOMPUTED HIT clinical_trials.json\n")

        if _copy_if_exists(bundle / "evidence/faers_signals.json", Path("files/evidence/faers_signals.json")):
            copied += 1
            logger.tool_call("mcp__drugrescue__faers_inverse_signal")
            logger.text("  [INVESTIGATOR]   PRECOMPUTED HIT faers_signals.json\n")

        if _copy_if_exists(bundle / "evidence/literature.json", Path("files/evidence/literature.json")):
            copied += 1
            logger.tool_call("mcp__drugrescue__literature_search")
            logger.text("  [INVESTIGATOR]   PRECOMPUTED HIT literature.json\n")

        if _copy_if_exists(bundle / "evidence/molecular.json", Path("files/evidence/molecular.json")):
            copied += 1
            logger.tool_call("mcp__drugrescue__molecular_similarity")
            logger.tool_call("mcp__drugrescue__molecular_docking")
            logger.text("  [INVESTIGATOR]   PRECOMPUTED HIT molecular.json\n")

        for rel in ["evidence/summary.json", "evidence/summary.md"]:
            if _copy_if_exists(bundle / rel, Path("files") / rel):
                copied += 1
                logger.tool_call("Write")

        logger.text("Phase 2 complete! Evidence loaded from precomputed artifacts.\n")

        # Phase 3 — Adversarial Court
        logger.agent_spawned("advocate", "Build case FOR repurposing")
        if _copy_if_exists(bundle / "court/advocate_brief.md", Path("files/court/advocate_brief.md")):
            copied += 1
        logger.tool_call("Read")
        logger.tool_call("Write")

        logger.agent_spawned("skeptic", "Build case AGAINST repurposing")
        if _copy_if_exists(bundle / "court/skeptic_brief.md", Path("files/court/skeptic_brief.md")):
            copied += 1
        logger.tool_call("Read")
        logger.tool_call("Write")
        logger.text("Phase 3 complete! Advocate and skeptic briefs loaded.\n")

        # Phase 4 — Judgment
        logger.agent_spawned("judge", "Deliver final verdict")
        verdict_exists = _copy_if_exists(bundle / "court/verdict.md", Path("files/court/verdict.md"))
        if verdict_exists:
            copied += 1
        scores_exists = _copy_if_exists(
            bundle / "court/verdict_scores.json",
            Path("files/court/verdict_scores.json"),
        )
        if scores_exists:
            copied += 1
        logger.tool_call("Read")
        logger.tool_call("Write")

        verdict_path = Path("files/court/verdict.md")
        if not verdict_path.exists():
            logger.text("\n❌ Precomputed bundle missing court/verdict.md\n")
            return 1

        logger.text(f"\nHydrated {copied} precomputed artifact(s) into files/.\n")

        # Print top scores if available.
        scores_path = Path("files/court/verdict_scores.json")
        if scores_path.exists():
            try:
                payload = json.loads(scores_path.read_text(encoding="utf-8"))
                verdicts = payload.get("verdicts", [])
                if isinstance(verdicts, list) and verdicts:
                    ranked = sorted(
                        [v for v in verdicts if isinstance(v, dict)],
                        key=lambda v: float(v.get("rescue_score", 0)),
                        reverse=True,
                    )
                    logger.text("\nTop Rescue Scores:\n")
                    for i, v in enumerate(ranked[:3], 1):
                        logger.text(
                            f"{i}. {v.get('drug_name', '?')} — "
                            f"{v.get('rescue_score', '?')}/100 "
                            f"({v.get('verdict', 'N/A')})\n"
                        )
            except Exception:
                pass

        logger.text(
            "\n\n  ✅ Court adjourned — turns: 6, cost: $0.0000\n"
            "\nInvestigation complete. Verdict: files/court/verdict.md\n"
        )
        return 0
    finally:
        logger.close()
        print(f"\nSession logs: {logger.log_dir}")
        print("Verdict: files/court/verdict.md")


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
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip pipeline and load precomputed artifacts from files/<disease>/",
    )
    parser.add_argument(
        "--precomputed-root",
        type=str,
        default="files",
        help="Root directory containing precomputed disease bundles (default: files)",
    )
    args = parser.parse_args()

    if args.fast:
        if not args.disease:
            print("error: --fast requires --disease")
            return
        raise SystemExit(run_fast(args.disease, args.precomputed_root))
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
