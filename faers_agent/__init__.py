"""FAERS inverse-signal detection package."""

from .agent import ClaudeFAERSAgent
from .client import OpenFDAClient
from .detector import FAERSDetector
from .models import InverseSignal, ScreeningResult

__all__ = [
    "ClaudeFAERSAgent",
    "FAERSDetector",
    "OpenFDAClient",
    "InverseSignal",
    "ScreeningResult",
]
