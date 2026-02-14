"""
DrugRescue Tools
================
Each tool = one file. This module collects them all.

Currently implemented:
    - kg_discovery.py  → discover_candidates, score_specific_drugs, kg_info

To add a new tool:
    1. Create src/drug_rescue/tools/my_tool.py with @tool decorated functions
    2. Import it here, add to ALL_TOOLS and ALL_TOOL_NAMES
    3. That's it — agent.py picks them up automatically
"""

from .kg_discovery import (
    discover_candidates_tool,
    score_specific_drugs_tool,
    kg_info_tool,
    KG_TOOLS,
    KG_TOOL_NAMES,
    set_data_dir as _set_kg_data_dir,
)

# ── All tools in one list — pass to create_sdk_mcp_server() ──
ALL_TOOLS = [*KG_TOOLS]

# ── Tool names under server key "drugrescue" ──
# Format: mcp__{server_key}__{tool_name}
ALL_TOOL_NAMES = [*KG_TOOL_NAMES]


def configure_tools(data_dir: str = "./data"):
    """Point all data-dependent tools at the right directory."""
    _set_kg_data_dir(data_dir)
    # Future: _set_sim_data_dir(data_dir), etc.
