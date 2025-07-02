from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import uuid


class EventSource(Enum):
    """Source of an event."""
    USER = "user"
    AGENT = "agent"
    ENVIRONMENT = "environment"


@dataclass
class Event:
    """Base class for all events in the system."""
    id: int = field(default_factory=lambda: int(time.time() * 1000000))  # microsecond timestamp as ID
    timestamp: float = field(default_factory=time.time)
    source: Optional[EventSource] = None
    hidden: bool = False  # Whether this event should be hidden from logs/UI
    
    def __post_init__(self):
        """Post-initialization to ensure consistent state."""
        if self.source is None:
            self.source = EventSource.ENVIRONMENT