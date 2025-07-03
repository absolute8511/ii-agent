"""Empty/null observations for ii-agent."""

from dataclasses import dataclass

from ii_agent.core.schema import ObservationType
from ii_agent.events.observation.observation import Observation


@dataclass
class NullObservation(Observation):
    """A null observation that represents no meaningful result."""
    
    observation: str = ObservationType.NULL
    
    @property
    def message(self) -> str:
        return "No result"
    
    def __str__(self) -> str:
        return "[No output]"