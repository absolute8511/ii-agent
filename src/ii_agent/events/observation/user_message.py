"""User message observations for ii-agent."""

from dataclasses import dataclass, field
from typing import Any, Dict

from ii_agent.core.schema import ObservationType
from ii_agent.events.observation.observation import Observation
from ii_agent.events.event import EventSource


@dataclass
class UserMessageObservation(Observation):
    """Observation representing a user message."""
    
    message: str = ""
    files: list = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    observation: str = ObservationType.USER_MESSAGE
    
    def __post_init__(self):
        super().__post_init__()
        self.source = EventSource.USER
    
    @property
    def message_text(self) -> str:
        return self.message
        
    @property
    def message(self) -> str:
        return f"User message: {self.message[:50]}{'...' if len(self.message) > 50 else ''}"
    
    def __str__(self) -> str:
        header = "[👤 User Message]"
        file_info = f" (with {len(self.files)} files)" if self.files else ""
        return f"{header}{file_info}\n{self.message}"