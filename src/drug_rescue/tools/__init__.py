"""
DrugRescue Tools
=================
All custom MCP tools for the DrugRescue agent.

This module aggregates tools from all submodules and provides:
    ALL_TOOLS      — list of @tool-decorated functions (for create_sdk_mcp_server)
    ALL_TOOL_NAMES — list of "mcp__drugrescue__*" strings (for allowed_tools)
    configure_tools(data_dir) — point all tools at the data directory

Usage in agent.py:
    from .tools import ALL_TOOLS, ALL_TOOL_NAMES, configure_tools
    configure_tools(data_dir="./data")
    server = create_sdk_mcp_server(name="drugrescue", tools=ALL_TOOLS)
"""

from __future__ import annotations

from .kg_discovery import (
    KG_TOOLS, KG_TOOL_NAMES,
    set_data_dir as _kg_set_data,
)
from .clinical_trials import CT_TOOLS, CT_TOOL_NAMES
from .faers_safety import FAERS_TOOLS, FAERS_TOOL_NAMES
from .literature import LIT_TOOLS, LIT_TOOL_NAMES
from .similarity import (
    SIM_TOOLS, SIM_TOOL_NAMES,
    set_data_dir as _sim_set_data,
)
from .docking import DOCK_TOOLS, DOCK_TOOL_NAMES


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AGGREGATED EXPORTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ALL_TOOLS = [
    *KG_TOOLS,       # discover_candidates, score_specific_drugs, kg_info
    *CT_TOOLS,       # clinical_trial_failure
    *FAERS_TOOLS,    # faers_inverse_signal, faers_suggest_events
    *LIT_TOOLS,      # literature_search
    *SIM_TOOLS,      # molecular_similarity
    *DOCK_TOOLS,     # molecular_docking
]

ALL_TOOL_NAMES = [
    *KG_TOOL_NAMES,
    *CT_TOOL_NAMES,
    *FAERS_TOOL_NAMES,
    *LIT_TOOL_NAMES,
    *SIM_TOOL_NAMES,
    *DOCK_TOOL_NAMES,
]


def configure_tools(data_dir: str = "./data"):
    """
    Point all tools at the data directory. Call once before first invocation.

    Tools that need data_dir:
        kg_discovery  — embeddings + dropped_drugs.db
        similarity    — pre-computed fingerprint matrix
    """
    _kg_set_data(data_dir)
    _sim_set_data(data_dir)
