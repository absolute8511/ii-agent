from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from .event import Event, EventSource


class ActionConfirmationStatus(Enum):
    """Status of action confirmation."""
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    AWAITING_CONFIRMATION = "awaiting_confirmation"


@dataclass
class Action(Event):
    """Base class for all actions that can be performed by agents."""
    runnable: bool = True  # Whether this action can be executed
    confirmation_state: Optional[ActionConfirmationStatus] = None
    tool_call_metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.source is None:
            self.source = EventSource.AGENT


@dataclass
class MessageAction(Action):
    """Action representing a message."""
    content: str = ""
    wait_for_response: bool = False
    runnable: bool = False
    files: list = field(default_factory=list)
    resume: bool = False
    
    def __str__(self) -> str:
        return f"MessageAction(content='{self.content[:50]}...')"


@dataclass
class ToolCallAction(Action):
    """Action representing a tool call."""
    tool_name: str = ""
    tool_input: Dict[str, Any] = field(default_factory=dict)
    tool_call_id: str = ""
    
    def __str__(self) -> str:
        return f"ToolCallAction(tool_name='{self.tool_name}', tool_call_id='{self.tool_call_id}')"


@dataclass 
class CompleteAction(Action):
    """Action indicating the agent has completed its task."""
    final_answer: str = ""
    runnable: bool = False
    
    def __str__(self) -> str:
        return f"CompleteAction(final_answer='{self.final_answer[:50]}...')"