"""DrugRescue multi-agent prompts — court architecture."""

from .orchestrator import ORCHESTRATOR_PROMPT
from .discovery import DISCOVERY_PROMPT
from .investigator import INVESTIGATOR_PROMPT
from .advocate import ADVOCATE_PROMPT
from .skeptic import SKEPTIC_PROMPT
from .judge import JUDGE_PROMPT

__all__ = [
    "ORCHESTRATOR_PROMPT",
    "DISCOVERY_PROMPT",
    "INVESTIGATOR_PROMPT",
    "ADVOCATE_PROMPT",
    "SKEPTIC_PROMPT",
    "JUDGE_PROMPT",
]
