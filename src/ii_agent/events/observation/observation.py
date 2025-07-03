"""Base observation class for ii-agent events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ii_agent.events.event import Event, EventSource


@dataclass
class Observation(Event):
    """Base class for all observations from the environment."""
    content: str = ""
    cause: Optional[int] = None  # ID of the action that caused this observation
    tool_call_metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.source is None:
            self.source = EventSource.ENVIRONMENT