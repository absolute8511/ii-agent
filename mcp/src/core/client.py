"""API client for making calls to Anthropic and OpenAI."""

import os
import time
import json
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
from uuid import uuid4

import anthropic
from anthropic import Anthropic
import openai
from openai import OpenAI

from .messages import (
    AssistantMessage, Usage, create_assistant_message, 
    create_assistant_api_error_message, normalize_messages_for_api
)


class APIClient:
    """Client for making API calls to language models."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        self.anthropic_client = None
        self.openai_client = None
        self.model = model
        
        # Initialize clients based on available API keys
        anthropic_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if anthropic_key:
            self.anthropic_client = Anthropic(api_key=anthropic_key)
        if openai_key:
            self.openai_client = OpenAI(api_key=openai_key)
    
    def _calculate_cost(self, model: str, usage: Usage) -> float:
        """Calculate the cost of API usage based on token counts."""
        # Simplified cost calculation - would need to be updated with current pricing
        cost_per_million_input = 3.0
        cost_per_million_output = 15.0
        
        if "haiku" in model.lower():
            cost_per_million_input = 0.8
            cost_per_million_output = 4.0
        elif "gpt" in model.lower():
            cost_per_million_input = 1.0
            cost_per_million_output = 3.0
        
        input_cost = (usage.input_tokens / 1_000_000) * cost_per_million_input
        output_cost = (usage.output_tokens / 1_000_000) * cost_per_million_output
        
        # Add cache costs if available
        cache_cost = 0.0
        if usage.cache_creation_input_tokens:
            cache_cost += (usage.cache_creation_input_tokens / 1_000_000) * (cost_per_million_input * 1.25)
        if usage.cache_read_input_tokens:
            cache_cost += (usage.cache_read_input_tokens / 1_000_000) * (cost_per_million_input * 0.1)
        
        return input_cost + output_cost + cache_cost
    
    async def query_anthropic(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: List[str],
        max_thinking_tokens: int = 0,
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None
    ) -> AssistantMessage:
        """Make a query to Anthropic's API."""
        if not self.anthropic_client:
            return create_assistant_api_error_message("Anthropic API key not configured")
        
        start_time = time.time()
        model_name = model or self.model
        
        try:
            # Prepare system prompt
            system = "\n".join(system_prompt) if system_prompt else ""
            
            # Prepare tool definitions for Anthropic
            anthropic_tools = []
            if tools:
                for tool in tools:
                    anthropic_tools.append({
                        "name": tool["function"]["name"],
                        "description": tool["function"]["description"],
                        "input_schema": tool["function"]["parameters"]
                    })
            
            # Make the API call
            kwargs = {
                "model": model_name,
                "max_tokens": 8192,
                "messages": messages,
                "temperature": 1.0
            }
            
            if system:
                kwargs["system"] = system
            if anthropic_tools:
                kwargs["tools"] = anthropic_tools
            if max_thinking_tokens > 0:
                kwargs["max_thinking_tokens"] = max_thinking_tokens
            
            response = await asyncio.to_thread(
                self.anthropic_client.messages.create,
                **kwargs
            )
            
            # Calculate duration and cost
            duration_ms = int((time.time() - start_time) * 1000)
            usage = Usage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cache_creation_input_tokens=getattr(response.usage, 'cache_creation_input_tokens', None),
                cache_read_input_tokens=getattr(response.usage, 'cache_read_input_tokens', None)
            )
            cost_usd = self._calculate_cost(model_name, usage)
            
            # Convert response to our message format
            content_blocks = []
            for block in response.content:
                if block.type == "text":
                    content_blocks.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    content_blocks.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })
            
            message_data = {
                "role": "assistant",
                "content": content_blocks,
                "id": response.id,
                "usage": {
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "cache_creation_input_tokens": usage.cache_creation_input_tokens,
                    "cache_read_input_tokens": usage.cache_read_input_tokens
                }
            }
            
            assistant_msg = AssistantMessage(
                message=message_data,
                cost_usd=cost_usd,
                duration_ms=duration_ms
            )
            
            return assistant_msg
            
        except Exception as e:
            error_msg = f"API Error: {str(e)}"
            return create_assistant_api_error_message(error_msg)
    
    async def query_openai(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: List[str],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: str = "gpt-4"
    ) -> AssistantMessage:
        """Make a query to OpenAI's API."""
        if not self.openai_client:
            return create_assistant_api_error_message("OpenAI API key not configured")
        
        start_time = time.time()
        
        try:
            # Prepare messages with system prompt
            openai_messages = []
            if system_prompt:
                openai_messages.append({
                    "role": "system",
                    "content": "\n".join(system_prompt)
                })
            openai_messages.extend(messages)
            
            # Prepare API call parameters
            kwargs = {
                "model": model,
                "messages": openai_messages,
                "temperature": 1.0,
                "max_tokens": 8192
            }
            
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            
            # Make the API call
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                **kwargs
            )
            
            # Calculate duration and cost
            duration_ms = int((time.time() - start_time) * 1000)
            usage = Usage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens
            )
            cost_usd = self._calculate_cost(model, usage)
            
            # Convert response to our message format
            choice = response.choices[0]
            content_blocks = []
            
            if choice.message.content:
                content_blocks.append({"type": "text", "text": choice.message.content})
            
            if choice.message.tool_calls:
                for tool_call in choice.message.tool_calls:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "input": json.loads(tool_call.function.arguments)
                    })
            
            message_data = {
                "role": "assistant",
                "content": content_blocks,
                "id": response.id,
                "usage": {
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens
                }
            }
            
            assistant_msg = AssistantMessage(
                message=message_data,
                cost_usd=cost_usd,
                duration_ms=duration_ms
            )
            
            return assistant_msg
            
        except Exception as e:
            error_msg = f"API Error: {str(e)}"
            return create_assistant_api_error_message(error_msg)
    
    async def query(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: List[str],
        max_thinking_tokens: int = 0,
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None
    ) -> AssistantMessage:
        """Query the appropriate API based on model and availability."""
        model_name = model or self.model
        
        # Determine which API to use based on model name
        if "gpt" in model_name.lower() or "openai" in model_name.lower():
            return await self.query_openai(messages, system_prompt, tools, model_name)
        else:
            return await self.query_anthropic(messages, system_prompt, max_thinking_tokens, tools, model_name)


# Global client instance
_global_client: Optional[APIClient] = None


def get_client() -> APIClient:
    """Get the global API client instance."""
    global _global_client
    if _global_client is None:
        _global_client = APIClient()
    return _global_client


def set_client(client: APIClient) -> None:
    """Set the global API client instance."""
    global _global_client
    _global_client = client 