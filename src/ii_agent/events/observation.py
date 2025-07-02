from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .event import Event, EventSource


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


@dataclass
class ToolResultObservation(Observation):
    """Observation from a tool execution."""
    tool_name: str = ""
    tool_call_id: str = ""
    tool_output: Any = None
    success: bool = True
    error_message: Optional[str] = None
    
    def __str__(self) -> str:
        status = "success" if self.success else "error"
        return f"ToolResultObservation(tool_name='{self.tool_name}', status='{status}')"


@dataclass
class UserMessageObservation(Observation):
    """Observation representing a user message."""
    message: str = ""
    files: list = field(default_factory=list)
    
    def __post_init__(self):
        super().__post_init__()
        self.source = EventSource.USER
        
    def __str__(self) -> str:
        return f"UserMessageObservation(message='{self.message[:50]}...')"


@dataclass
class SystemObservation(Observation):
    """Observation from the system (e.g., interruptions, status changes)."""
    event_type: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"SystemObservation(event_type='{self.event_type}')"