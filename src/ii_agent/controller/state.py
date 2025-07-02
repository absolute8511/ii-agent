from __future__ import annotations

import pickle
import base64
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Any

from ..events.event import Event
from ..events.action import MessageAction


class AgentState(Enum):
    """State of the agent."""
    INIT = "init"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class State:
    """State of the agent controller."""
    session_id: str = ""
    agent_state: AgentState = AgentState.INIT
    history: List[Event] = field(default_factory=list)
    metrics: Optional[Any] = None
    outputs: dict = field(default_factory=dict)

    @property
    def view(self) -> List[Event]:
        """Returns a view of the history for processing."""
        return self.history

    def save_to_session(self, session_id: str, file_store):
        """Save state to session storage."""
        from ii_agent.core.storage.locations import get_conversation_agent_history_filename
        
        pickled = pickle.dumps(self)
        encoded = base64.b64encode(pickled).decode('utf-8')

        try:
            file_store.write(get_conversation_agent_history_filename(session_id), encoded)
        except Exception as e:
            raise Exception(f"Error saving message history to session: {e}")

    @staticmethod
    def restore_from_session(session_id: str, file_store):
        """Restore state from session storage.""" 
        from ii_agent.core.storage.locations import get_conversation_agent_history_filename
        
        state: State
        try:
            encoded = file_store.read(get_conversation_agent_history_filename(session_id))
            pickled = base64.b64decode(encoded)
            state = pickle.loads(pickled)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Could not restore state from file for session id: {session_id}"
            )
        return state

    def get_last_agent_message(self) -> MessageAction | None:
        for event in reversed(self.view):
            if isinstance(event, MessageAction) and event.source.value == "agent":
                return event
        return None

    def get_last_user_message(self) -> MessageAction | None:
        for event in reversed(self.view):
            if isinstance(event, MessageAction) and event.source.value == "user":
                return event
        return None

    def get_initial_user_message(self) -> MessageAction | None:
        """Finds the initial user message action from the full history."""
        initial_user_message: MessageAction | None = None
        for event in self.history:
            if isinstance(event, MessageAction) and event.source.value == 'user':
                initial_user_message = event
                break

        if initial_user_message is None:
            # Logger import moved to runtime to avoid dependencies
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f'CRITICAL: Could not find the initial user MessageAction in the full {len(self.history)} events history.'
            )
            raise ValueError(
                'Initial user message not found in history. Please report this issue.'
            )
        return initial_user_message

    def to_llm_metadata(self, agent_name: str) -> dict:
        return {
            'session_id': self.session_id,
            'tags': [
                f'agent:{agent_name}',
            ],
        }

    def add_event(self, event: Event):
        """Add an event to the history."""
        self.history.append(event)

    def clear(self):
        """Clear the history and reset state."""
        self.history = []
        self.agent_state = AgentState.INIT
        self.outputs = {}

    def __len__(self) -> int:
        """Returns the number of events in history."""
        return len(self.history)