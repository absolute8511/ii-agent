"""Message types and handling for agent communication."""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class ToolUseBlock(BaseModel):
    """Represents a tool use block in a message."""
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: Dict[str, Any]


class ToolResultBlock(BaseModel):
    """Represents a tool result block in a message."""
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str
    is_error: bool = False


class TextBlock(BaseModel):
    """Represents a text block in a message."""
    type: Literal["text"] = "text"
    text: str


ContentBlock = Union[TextBlock, ToolUseBlock, ToolResultBlock]


@dataclass
class Usage:
    """Token usage information."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: Optional[int] = None
    cache_read_input_tokens: Optional[int] = None


@dataclass
class UserMessage:
    """User message type."""
    type: Literal["user"] = "user"
    message: Dict[str, Any] = field(default_factory=dict)
    uuid: UUID = field(default_factory=uuid4)
    tool_use_result: Optional[Dict[str, Any]] = None


@dataclass
class AssistantMessage:
    """Assistant message type."""
    type: Literal["assistant"] = "assistant"
    message: Dict[str, Any] = field(default_factory=dict)
    uuid: UUID = field(default_factory=uuid4)
    cost_usd: float = 0.0
    duration_ms: int = 0
    is_api_error_message: bool = False


@dataclass
class ProgressMessage:
    """Progress message for tracking agent execution."""
    type: Literal["progress"] = "progress"
    content: AssistantMessage = field(default_factory=AssistantMessage)
    normalized_messages: List[Union[UserMessage, AssistantMessage]] = field(default_factory=list)
    sibling_tool_use_ids: set = field(default_factory=set)
    tools: List[Any] = field(default_factory=list)
    tool_use_id: str = ""
    uuid: UUID = field(default_factory=uuid4)


Message = Union[UserMessage, AssistantMessage, ProgressMessage]

INTERRUPT_MESSAGE = "⚠️ Task was interrupted"
INTERRUPT_MESSAGE_FOR_TOOL_USE = "⚠️ Tool execution was interrupted"


def create_user_message(content: Union[str, List[ContentBlock]]) -> UserMessage:
    """Create a user message with the given content."""
    if isinstance(content, str):
        message_content = [{"type": "text", "text": content}]
    else:
        message_content = [block.model_dump() if isinstance(block, BaseModel) else block for block in content]
    
    return UserMessage(
        message={
            "role": "user",
            "content": message_content
        }
    )


def create_assistant_message(content: str, cost_usd: float = 0.0, usage: Optional[Usage] = None) -> AssistantMessage:
    """Create an assistant message with the given content."""
    message_data = {
        "role": "assistant",
        "content": [{"type": "text", "text": content}],
        "id": str(uuid4())
    }
    
    if usage:
        message_data["usage"] = {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cache_creation_input_tokens": usage.cache_creation_input_tokens,
            "cache_read_input_tokens": usage.cache_read_input_tokens
        }
    
    return AssistantMessage(
        message=message_data,
        cost_usd=cost_usd,
        duration_ms=0
    )


def create_assistant_api_error_message(error_msg: str) -> AssistantMessage:
    """Create an assistant message for API errors."""
    msg = create_assistant_message(error_msg)
    msg.is_api_error_message = True
    return msg


def create_tool_result_stop_message(tool_use_id: str) -> ToolResultBlock:
    """Create a tool result block for stopped execution."""
    return ToolResultBlock(
        tool_use_id=tool_use_id,
        content="Tool execution was stopped",
        is_error=True
    )


def create_progress_message(
    content: AssistantMessage,
    normalized_messages: List[Message],
    tools: List[Any],
    tool_use_id: str = "",
    sibling_tool_use_ids: Optional[set] = None
) -> ProgressMessage:
    """Create a progress message."""
    return ProgressMessage(
        content=content,
        normalized_messages=normalized_messages,
        tools=tools,
        tool_use_id=tool_use_id,
        sibling_tool_use_ids=sibling_tool_use_ids or set()
    )


def normalize_messages(messages: List[Message]) -> List[Union[UserMessage, AssistantMessage]]:
    """Normalize messages by filtering out progress messages."""
    return [msg for msg in messages if msg.type in ["user", "assistant"]]


def normalize_messages_for_api(messages: List[Message]) -> List[Dict[str, Any]]:
    """Convert messages to API format."""
    normalized = normalize_messages(messages)
    api_messages = []
    
    for msg in normalized:
        if msg.type == "user":
            api_messages.append(msg.message)
        elif msg.type == "assistant":
            api_messages.append(msg.message)
    
    return api_messages 