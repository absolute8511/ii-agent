from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, ClassVar

from .event import Event, EventSource


class ActionConfirmationStatus(str, Enum):
    """Status of action confirmation."""
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    AWAITING_CONFIRMATION = "awaiting_confirmation"


class ActionSecurityRisk(int, Enum):
    """Security risk level of an action."""
    UNKNOWN = -1
    LOW = 0
    MEDIUM = 1
    HIGH = 2


@dataclass
class Action(Event):
    """Base class for all actions that can be performed by agents."""
    runnable: ClassVar[bool] = False  # Whether this action type can be executed
    confirmation_state: ActionConfirmationStatus = ActionConfirmationStatus.CONFIRMED
    security_risk: Optional[ActionSecurityRisk] = None
    thought: str = ""  # Agent's reasoning for this action
    
    def __post_init__(self):
        super().__post_init__()
        # Actions are always from agents
        self.source = EventSource.AGENT

    @property
    def message(self) -> str:
        """Get a human-readable message describing this action."""
        return f"Action: {self.__class__.__name__}"


@dataclass
class MessageAction(Action):
    """Action representing a message."""
    content: str = ""
    wait_for_response: bool = False
    runnable: ClassVar[bool] = False
    files: list = field(default_factory=list)
    resume: bool = False
    
    @property
    def message(self) -> str:
        return f"Sending message: {self.content[:50]}{'...' if len(self.content) > 50 else ''}"
    
    def __str__(self) -> str:
        return f"MessageAction(content='{self.content[:50]}...')"


@dataclass
class ToolCallAction(Action):
    """Action representing a tool call."""
    tool_name: str = ""
    tool_input: Dict[str, Any] = field(default_factory=dict)
    tool_call_id: str = ""
    runnable: ClassVar[bool] = True
    
    def __post_init__(self):
        super().__post_init__()
        # Set tool call metadata for this action
        if self.tool_call_id and self.tool_name:
            from .tool import ToolCallMetadata
            self.tool_call_metadata = ToolCallMetadata(
                function_name=self.tool_name,
                tool_call_id=self.tool_call_id
            )
    
    @property
    def message(self) -> str:
        return f"Calling tool: {self.tool_name}"
    
    def __str__(self) -> str:
        return f"ToolCallAction(tool_name='{self.tool_name}', tool_call_id='{self.tool_call_id}')"


@dataclass 
class CompleteAction(Action):
    """Action indicating the agent has completed its task."""
    final_answer: str = ""
    runnable: ClassVar[bool] = False
    
    @property
    def message(self) -> str:
        return f"Task completed: {self.final_answer[:50]}{'...' if len(self.final_answer) > 50 else ''}"
    
    def __str__(self) -> str:
        return f"CompleteAction(final_answer='{self.final_answer[:50]}...')"