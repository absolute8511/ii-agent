"""Text response parser for plain text LLM responses."""

import re
from typing import Any

from ii_agent.controller.action_parser import ResponseParser, ActionParseError
from ii_agent.events.action import Action, MessageAction, CompleteAction
from ii_agent.events.event import EventSource


class TextResponseParser(ResponseParser):
    """Parser for plain text LLM responses.
    
    Handles responses from LLMs that don't use function calling,
    converting text responses into appropriate Action objects.
    """

    def __init__(self):
        super().__init__()
        # Patterns for detecting different action types in text
        self.completion_patterns = [
            r"(?i)(?:task|work|job)\s+(?:is\s+)?(?:completed?|finished?|done)",
            r"(?i)(?:i\s+(?:have\s+)?)?(?:completed?|finished?)\s+(?:the\s+)?task",
            r"(?i)no\s+(?:further|more)\s+(?:action|work)\s+(?:is\s+)?(?:needed|required)",
            r"(?i)(?:all\s+)?(?:done|finished|complete)\.?\s*$",
        ]
        
        self.thinking_patterns = [
            r"(?i)(?:let\s+me\s+)?think(?:ing)?(?:\s+about)?",
            r"(?i)(?:i\s+)?(?:need\s+to\s+)?(?:consider|analyze|figure\s+out)",
            r"(?i)(?:my\s+)?(?:thought|reasoning|analysis)\s*:?",
        ]

    def parse(self, response: Any) -> Action:
        """Parse text response into an Action.

        Args:
            response: LLM response (string, dict, or response object)

        Returns:
            Action: Parsed action object

        Raises:
            ActionParseError: If parsing fails
        """
        try:
            text_content = self.parse_response(response)
            return self.parse_action(text_content)
        except Exception as e:
            raise ActionParseError(f"Failed to parse text response: {e}")

    def parse_response(self, response: Any) -> str:
        """Extract text content from response.

        Args:
            response: LLM response object

        Returns:
            str: Extracted text content
        """
        if isinstance(response, str):
            return response
            
        # Handle OpenAI-style response objects
        if hasattr(response, 'choices') and response.choices:
            choice = response.choices[0]
            if hasattr(choice, 'message'):
                return getattr(choice.message, 'content', '') or ''
            elif hasattr(choice, 'text'):
                return choice.text
                
        # Handle dictionary responses
        if isinstance(response, dict):
            # Try different possible keys
            for key in ['content', 'text', 'message', 'response']:
                if key in response:
                    value = response[key]
                    if isinstance(value, str):
                        return value
                    elif isinstance(value, dict) and 'content' in value:
                        return value['content']
                        
        # Fall back to string conversion
        return str(response)

    def parse_action(self, action_str: str) -> Action:
        """Parse action string into an Action object.

        Args:
            action_str: The text content to parse

        Returns:
            Action: Appropriate action based on text content
        """
        if not action_str or not action_str.strip():
            action = CompleteAction(final_answer="")
            action.source = EventSource.AGENT
            return action
        
        action_str = action_str.strip()
        
        # Check for completion patterns
        if self._is_completion(action_str):
            action = CompleteAction(final_answer=action_str)
            action.source = EventSource.AGENT
            return action
        
        # Check for thinking patterns
        if self._is_thinking(action_str):
            action = MessageAction(content=action_str)
            action.source = EventSource.AGENT
            return action
        
        # Default to message action
        action = MessageAction(content=action_str)
        action.source = EventSource.AGENT
        return action

    def _is_completion(self, text: str) -> bool:
        """Check if text indicates task completion.

        Args:
            text: Text to check

        Returns:
            bool: True if text indicates completion
        """
        for pattern in self.completion_patterns:
            if re.search(pattern, text):
                return True
        return False

    def _is_thinking(self, text: str) -> bool:
        """Check if text indicates thinking/reasoning.

        Args:
            text: Text to check

        Returns:
            bool: True if text indicates thinking
        """
        for pattern in self.thinking_patterns:
            if re.search(pattern, text):
                return True
        
        # Also check for common thinking indicators
        thinking_keywords = [
            "reasoning", "analysis", "plan", "strategy", 
            "approach", "consideration", "evaluation"
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in thinking_keywords)