from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from .tool import ToolCallMetadata


class EventSource(Enum):
    """Source of an event."""
    USER = "user"
    AGENT = "agent"
    ENVIRONMENT = "environment"


@dataclass
class Event:
    """Base class for all events in the system."""
    # Core fields - using underscore prefix for property-based access
    _id: Optional[int] = field(default=None, init=False)
    _timestamp: Optional[str] = field(default=None, init=False)
    _source: Optional[str] = field(default=None, init=False)
    _cause: Optional[int] = field(default=None, init=False)
    _tool_call_metadata: Optional[ToolCallMetadata] = field(default=None, init=False)
    _response_id: Optional[str] = field(default=None, init=False)
    
    # Direct fields
    hidden: bool = False  # Whether this event should be hidden from logs/UI
    
    def __post_init__(self):
        """Post-initialization to ensure consistent state."""
        # Set default ID if not provided
        if self._id is None:
            self._id = int(time.time() * 1000000)  # microsecond timestamp as ID
        
        # Set default timestamp if not provided
        if self._timestamp is None:
            self._timestamp = datetime.now().isoformat()
        
        # Set default source if not provided
        if self._source is None:
            self._source = EventSource.ENVIRONMENT.value
    
    @property
    def id(self) -> int:
        """Get the event ID."""
        return self._id if self._id is not None else -1
    
    @property
    def timestamp(self) -> str:
        """Get the event timestamp as ISO format string."""
        return self._timestamp if self._timestamp is not None else ""
    
    @timestamp.setter
    def timestamp(self, value: datetime) -> None:
        """Set timestamp from datetime object."""
        if isinstance(value, datetime):
            self._timestamp = value.isoformat()
        elif isinstance(value, str):
            self._timestamp = value
    
    @property
    def source(self) -> Optional[EventSource]:
        """Get the event source."""
        if self._source is not None:
            return EventSource(self._source)
        return None
    
    @source.setter
    def source(self, value: Optional[EventSource]) -> None:
        """Set the event source."""
        if value is not None:
            self._source = value.value if isinstance(value, EventSource) else str(value)
        else:
            self._source = None
    
    @property
    def cause(self) -> Optional[int]:
        """Get the ID of the event that caused this event."""
        return self._cause
    
    @cause.setter
    def cause(self, value: Optional[int]) -> None:
        """Set the cause event ID."""
        self._cause = value
    
    @property
    def tool_call_metadata(self) -> Optional[ToolCallMetadata]:
        """Get tool call metadata if this event involves a tool call."""
        return self._tool_call_metadata
    
    @tool_call_metadata.setter
    def tool_call_metadata(self, value: ToolCallMetadata) -> None:
        """Set tool call metadata."""
        self._tool_call_metadata = value
    
    @property
    def response_id(self) -> Optional[str]:
        """Get the ID of the LLM response that generated this event."""
        return self._response_id
    
    @response_id.setter
    def response_id(self, value: str) -> None:
        """Set the response ID."""
        self._response_id = value
    
    @property
    def message(self) -> str:
        """Get a human-readable message for this event.
        
        Subclasses should override this to provide specific messages.
        """
        return f"Event {self.__class__.__name__}"