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

    print(f"\n{'='*60}")
    print(f"  DrugRescue — Standalone Mode (no Claude)")
    print(f"  Disease: {disease}")
    print(f"{'='*60}\n")

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
        "max_candidates": 20,
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

    # ── Table ──
    print(f"  {'#':<3} {'Drug':<28} {'Status':<10} {'Phase':<6} "
          f"{'Pctl':<7} {'Z':<7} {'Score':<6} {'SMILES'}")
    print(f"  {'─'*3} {'─'*28} {'─'*10} {'─'*6} {'─'*7} {'─'*7} {'─'*6} {'─'*5}")

    for c in data["candidates"]:
        smiles = "✓" if c.get("smiles") else "—"
        phase = str(c.get("max_phase") or "—")
        print(f"  {c['kg_rank']:<3} {c['drug_name'][:26]:<28} {c['status']:<10} "
              f"{phase:<6} {c['kg_percentile']:<7.1f} {c['kg_z_score']:<7.2f} "
              f"{c['kg_normalized']:<6.2f} {smiles}")

    # ── Summary ──
    dropped = [c for c in data["candidates"] if c["status"] == "dropped"]
    if dropped:
        print(f"\n  🎯 Top dropped drugs (prime repurposing targets):")
        for c in dropped[:5]:
            phase = f"Phase {c['max_phase']}" if c.get("max_phase") else "?"
            print(f"     • {c['drug_name']} ({phase}, "
                  f"KG {c['kg_percentile']:.0f}th pctl)")

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
