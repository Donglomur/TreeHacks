"""
DrugRescue Agent
================
TreeHacks 2026

The brain. Wires all tools to Claude via the Agent SDK.

Usage:
    python -m drug_rescue --disease glioblastoma            # full agent
    python -m drug_rescue --disease glioblastoma --standalone  # no SDK needed
    python -m drug_rescue                                    # interactive chat

From Python:
    from drug_rescue.agent import run_agent
    report = await run_agent("glioblastoma", data_dir="./data")
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

try:
    from claude_agent_sdk import (
        ClaudeAgentOptions,
        ClaudeSDKClient,
        AssistantMessage,
        ResultMessage,
        TextBlock,
        create_sdk_mcp_server,
    )
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

from .tools import ALL_TOOLS, ALL_TOOL_NAMES, configure_tools
from .prompts import SYSTEM_PROMPT


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AGENT SETUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_options(data_dir: str = "./data") -> ClaudeAgentOptions:
    """
    Build ClaudeAgentOptions with all tools registered.

    This creates an in-process MCP server (no subprocess, no IPC overhead)
    and registers all tools under the server key "drugrescue".

    Tools become callable as: mcp__drugrescue__{tool_name}
    """
    configure_tools(data_dir=data_dir)

    server = create_sdk_mcp_server(
        name="drugrescue",
        version="1.0.0",
        tools=ALL_TOOLS,
    )

    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"drugrescue": server},
        allowed_tools=[*ALL_TOOL_NAMES, "Read", "Write"],
        permission_mode="acceptEdits",
        max_turns=30,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  RUN MODES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def run_agent(disease: str, data_dir: str = "./data") -> str:
    """
    One-shot: investigate a disease and return the report.

    Args:
        disease: Disease name (e.g. "glioblastoma")
        data_dir: Path to data/ directory with embeddings + database

    Returns:
        Final report text from Claude
    """
    if not SDK_AVAILABLE:
        raise ImportError("pip install 'drug-rescue[agent]'")

    options = create_options(data_dir)
    result_text = ""

    prompt = (
        f"Investigate drug repurposing candidates for **{disease}**.\n\n"
        f"Start by discovering candidates from the knowledge graph, then "
        f"analyze the top results and provide a ranked recommendation."
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(block.text, end="", flush=True)
                        result_text += block.text
            elif isinstance(msg, ResultMessage):
                print(f"\n\n[Done — turns: {msg.num_turns}, "
                      f"cost: ${msg.total_cost_usd:.4f}]")

    return result_text


async def run_interactive(data_dir: str = "./data"):
    """Multi-turn chat with the researcher agent."""
    if not SDK_AVAILABLE:
        raise ImportError("pip install 'drug-rescue[agent]'")

    options = create_options(data_dir)

    print("\n" + "=" * 60)
    print("  DrugRescue AI — Drug Repurposing Researcher")
    print("=" * 60)
    print('\nExamples:')
    print('  "Investigate glioblastoma"')
    print('  "What drugs might work for Alzheimer\'s?"')
    print('  "Score metformin and aspirin against breast cancer"')
    print('\nType "quit" to exit.\n')

    async with ClaudeSDKClient(options=options) as client:
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break
            if user_input.lower() in ("quit", "exit", "q"):
                break
            if not user_input:
                continue

            await client.query(user_input)
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            print(block.text, end="", flush=True)
                elif isinstance(msg, ResultMessage):
                    print(f"\n[turns: {msg.num_turns}, "
                          f"cost: ${msg.total_cost_usd:.4f}]")
            print()


async def run_standalone(disease: str, data_dir: str = "./data"):
    """
    Run the KG tool directly without Claude.
    No SDK needed. Useful for testing and demos.
    """
    configure_tools(data_dir)
    from .tools.kg_discovery import discover_candidates_tool, kg_info_tool
    from pathlib import Path

    print(f"\n{'='*60}")
    print(f"  DrugRescue — Standalone Mode (no Claude)")
    print(f"  Disease: {disease}")
    print(f"{'='*60}\n")

    # ── Load name lookup files (belt + suspenders for display) ──
    name_lookup: dict[str, str] = {}  # "Compound::DB00515" → "CISPLATIN"

    # Source 1: kg_entity_lookup.json (from resolve_all_compounds.py)
    kg_lookup_path = Path(data_dir) / "database" / "kg_entity_lookup.json"
    if kg_lookup_path.exists():
        with open(kg_lookup_path) as f:
            kg_lookup = json.load(f)
        for entity, info in kg_lookup.items():
            if info.get("drug_name"):
                name_lookup[entity] = info["drug_name"]

    # Source 2: drugbank_to_name.json (from populate_drugbank_ids_modal.py)
    db_name_path = Path(data_dir) / "drugbank_to_name.json"
    if db_name_path.exists():
        with open(db_name_path) as f:
            db_names = json.load(f)
        for db_id, name in db_names.items():
            entity = f"Compound::{db_id}"
            if entity not in name_lookup:
                name_lookup[entity] = name

    if name_lookup:
        print(f"📝 Loaded {len(name_lookup)} drug name lookups\n")

    # ── Graph info ──
    info_result = await kg_info_tool({})
    info = json.loads(info_result["content"][0]["text"])
    print(f"📊 Graph: {info.get('compounds', '?')} compounds, "
          f"{info.get('diseases', '?')} diseases, "
          f"{info.get('genes', '?')} genes")
    print(f"   Method: {info.get('method', '?')}, "
          f"Dim: {info.get('embedding_shape', '?')}")
    print(f"   Relations: {', '.join(info.get('treatment_relations', []))}\n")

    # ── Discover ──
    print(f"🔬 Scoring all compounds against '{disease}'...")
    result = await discover_candidates_tool({
        "disease": disease,
        "max_candidates": 30,
        "min_percentile": 75.0,
        "include_novel": True,
    })

    data = json.loads(result["content"][0]["text"])

    if "error" in data and "candidates" not in data:
        print(f"  ❌ {data['error']}")
        if "hint" in data:
            print(f"  💡 {data['hint']}")
        return

    print(f"  ✅ Scored {data['total_compounds_scored']:,} compounds "
          f"in {data['timing_ms']:.0f}ms ({data['method']})")
    print(f"  📊 {data['candidates_returned']} candidates: "
          f"{data['stats'].get('dropped', 0)} dropped, "
          f"{data['stats'].get('withdrawn', 0)} withdrawn, "
          f"{data['stats'].get('novel', 0)} novel\n")

    # ── Helper: resolve display name ──
    # Fix PubChem/MeSH naming errors
    ENTITY_NAME_FIXES = {
        "Compound::DB00515": "CISPLATIN",
        "Compound::DB00853": "TEMOZOLOMIDE",
        "Compound::DB00112": "BEVACIZUMAB",
    }

    def resolve_name(c: dict) -> str:
        entity = c.get("drkg_entity", "")

        # 1. Manual fixes (highest priority)
        if entity in ENTITY_NAME_FIXES:
            return ENTITY_NAME_FIXES[entity]

        display_name = c["drug_name"]

        # 2. If name is still a raw ID, try lookup
        if display_name == entity.replace("Compound::", ""):
            resolved = name_lookup.get(entity)
            if resolved:
                display_name = resolved

        # 3. Strip MeSH "[OBSOLETE]" tag
        if display_name.startswith("[OBSOLETE]"):
            display_name = display_name.replace("[OBSOLETE]", "").strip()

        return display_name

    # ── Table ──
    print(f"  {'#':<3} {'Drug':<28} {'Status':<10} {'Phase':<6} "
          f"{'Pctl':<7} {'Z':<7} {'Score':<6} {'SMILES'}")
    print(f"  {'─'*3} {'─'*28} {'─'*10} {'─'*6} {'─'*7} {'─'*7} {'─'*6} {'─'*5}")

    # Sort: dropped first, then named novel, then unknown
    candidates = data["candidates"]
    dropped = [c for c in candidates if c["status"] == "dropped"]
    withdrawn = [c for c in candidates if c["status"] == "withdrawn"]
    named_novel = [c for c in candidates if c["status"] == "novel"
                   and resolve_name(c) != c.get("drkg_entity", "").replace("Compound::", "")]
    unknown = [c for c in candidates if c["status"] == "novel"
               and resolve_name(c) == c.get("drkg_entity", "").replace("Compound::", "")]

    rank = 1
    for section, label in [
        (dropped, "🎯 DROPPED — Prime repurposing targets"),
        (withdrawn, "⚠️  WITHDRAWN"),
        (named_novel, "💊 KNOWN DRUGS — Approved/researched for other indications"),
        (unknown, "🔬 UNRESOLVED — Need manual ID lookup"),
    ]:
        if not section:
            continue
        print(f"\n  {label}")
        for c in section:
            smiles = "✓" if c.get("smiles") else "—"
            phase = str(c.get("max_phase") or "—")
            display_name = resolve_name(c)
            print(f"  {rank:<3} {display_name[:26]:<28} {c['status']:<10} "
                  f"{phase:<6} {c['kg_percentile']:<7.1f} {c['kg_z_score']:<7.2f} "
                  f"{c['kg_normalized']:<6.2f} {smiles}")
            rank += 1

    # ── Summary ──
    if dropped:
        print(f"\n  {'='*56}")
        print(f"  REPURPOSING CANDIDATES — Dropped Phase II/III drugs")
        print(f"  {'='*56}")
        for c in dropped:
            phase = f"Phase {c['max_phase']}" if c.get("max_phase") else "?"
            name = resolve_name(c)
            print(f"  • {name} ({phase}, z={c['kg_z_score']:.2f}, "
                  f"pctl={c['kg_percentile']:.1f})")

    print(f"\n{'='*60}\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    parser = argparse.ArgumentParser(
        description="DrugRescue AI — Drug Repurposing Researcher"
    )
    parser.add_argument("--disease", "-d", type=str,
                        help="Disease to investigate (one-shot mode)")
    parser.add_argument("--data-dir", type=str, default="./data",
                        help="Path to data/ directory")
    parser.add_argument("--standalone", "-s", action="store_true",
                        help="Run KG tool directly (no Claude SDK)")
    args = parser.parse_args()

    if args.standalone or not SDK_AVAILABLE:
        if not SDK_AVAILABLE and not args.standalone:
            print("⚠️  claude-agent-sdk not installed — using standalone mode")
            print("   pip install 'drug-rescue[agent]' for full agent\n")
        asyncio.run(run_standalone(args.disease or "glioblastoma",
                                   data_dir=args.data_dir))
    elif args.disease:
        asyncio.run(run_agent(args.disease, data_dir=args.data_dir))
    else:
        asyncio.run(run_interactive(data_dir=args.data_dir))


if __name__ == "__main__":
    main()
