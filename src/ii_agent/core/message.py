"""Message system for LLM communication."""

from dataclasses import dataclass, field
from typing import Any, List, Optional, Literal, Dict
from abc import ABC, abstractmethod


class Content(ABC):
    """Abstract base class for message content."""
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert content to dictionary representation."""
        pass


@dataclass
class TextContent(Content):
    """Text content for messages."""
    text: str
    cache_prompt: bool = False  # For Anthropic caching
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"type": "text", "text": self.text}
        if self.cache_prompt:
            result["cache_control"] = {"type": "ephemeral"}
        return result


@dataclass
class ImageContent(Content):
    """Image content for messages."""
    image_urls: List[str]
    cache_prompt: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": "image", 
            "source": {
                "type": "url",
                "url": self.image_urls[0] if self.image_urls else ""
            }
        }
        if self.cache_prompt:
            result["cache_control"] = {"type": "ephemeral"}
        return result


@dataclass
class ToolCall:
    """Represents a tool call in a message."""
    id: str
    type: str = "function"
    function: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "function": self.function
        }


@dataclass
class Message:
    """Represents a message in LLM conversation."""
    role: Literal["system", "user", "assistant", "tool"]
    content: List[Content]
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None  # For tool response messages
    name: Optional[str] = None  # Tool name for tool response messages
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format for LLM APIs."""
        result = {
            "role": self.role,
            "content": [content.to_dict() for content in self.content]
        }
        
        if self.tool_calls:
            result["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
            
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
            
        if self.name:
            result["name"] = self.name
            
        return result
    
    def model_copy(self, update: Optional[Dict[str, Any]] = None) -> "Message":
        """Create a copy of the message with optional updates."""
        # Simple implementation - could be enhanced with deep copy if needed
        new_msg = Message(
            role=self.role,
            content=self.content.copy(),
            tool_calls=self.tool_calls.copy() if self.tool_calls else None,
            tool_call_id=self.tool_call_id,
            name=self.name
        )
        
        if update:
            for key, value in update.items():
                setattr(new_msg, key, value)
                
        return new_msg