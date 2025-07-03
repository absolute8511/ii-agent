"""Base Action class for ii-agent events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Optional

from ii_agent.core.schema import ConfirmationStatus, SecurityRisk
from ii_agent.events.event import Event, EventSource


@dataclass
class Action(Event):
    """Base class for all actions that can be performed by agents."""
    
    runnable: ClassVar[bool] = False  # Whether this action type can be executed
    confirmation_state: ConfirmationStatus = ConfirmationStatus.CONFIRMED
    security_risk: Optional[SecurityRisk] = None
    thought: str = ""  # Agent's reasoning for this action
    
    def __post_init__(self):
        super().__post_init__()
        # Actions are always from agents by default
        if self.source is None:
            self.source = EventSource.AGENT

    @property
    def message(self) -> str:
        """Get a human-readable message describing this action."""
        return f"Action: {self.__class__.__name__}"