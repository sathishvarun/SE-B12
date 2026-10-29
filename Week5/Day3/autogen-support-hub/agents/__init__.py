"""Multi-agent customer support package (AutoGen)."""

from .config import AVAILABLE_MODELS, DEFAULT_MODEL, DEPARTMENTS, get_api_key
from .orchestrator import HEAD_AGENT_NAME, RunResult, SupportOrchestrator, TraceEvent

__all__ = [
    "AVAILABLE_MODELS",
    "DEFAULT_MODEL",
    "DEPARTMENTS",
    "HEAD_AGENT_NAME",
    "RunResult",
    "SupportOrchestrator",
    "TraceEvent",
    "get_api_key",
]
