"""Agent executor for running agent queries with tool execution."""

import asyncio
import time
from typing import AsyncGenerator, List, Dict, Any, Optional, Set
from uuid import uuid4

from .messages import (
    Message, UserMessage, AssistantMessage, ProgressMessage,
    ToolUseBlock, ToolResultBlock, TextBlock,
    create_user_message, create_assistant_message, create_progress_message,
    create_tool_result_stop_message, normalize_messages, normalize_messages_for_api,
    INTERRUPT_MESSAGE, INTERRUPT_MESSAGE_FOR_TOOL_USE
)
from .client import get_client
from .tool_registry import get_registry, get_tools_for_api


MAX_TOOL_USE_CONCURRENCY = 5


class AgentExecutor:
    """Executes agent queries with tool support."""
    
    def __init__(self, dangerous_skip_permissions: bool = False):
        self.dangerous_skip_permissions = dangerous_skip_permissions
        self.client = get_client()
        self.registry = get_registry()
        self.registry.load_tools(dangerous_skip_permissions)
        
        # Load system prompt for agents
        self.system_prompt = self._get_agent_system_prompt()
    
    def _get_agent_system_prompt(self) -> List[str]:
        """Get the system prompt for agent execution."""
        from src.system_prompt import SYSTEM_INSTRUCTION
        return [SYSTEM_INSTRUCTION]
    
    async def execute_agent_task(
        self,
        prompt: str,
        description: str = "",
        max_thinking_tokens: int = 0,
        model: str = "claude-3-5-sonnet-20241022"
    ) -> Dict[str, Any]:
        """
        Execute a complete agent task and return the result.
        
        This is the main entry point for agent execution.
        """
        start_time = time.time()
        
        # Create initial messages
        messages: List[Message] = [create_user_message(prompt)]
        
        # Track execution metrics
        tool_use_count = 0
        final_message = None
        all_messages = []
        
        try:
            # Get available tools for this agent
            tools = get_tools_for_api(self.dangerous_skip_permissions)
            
            # Make initial API call
            api_messages = normalize_messages_for_api(messages)
            assistant_message = await self.client.query(
                api_messages,
                self.system_prompt,
                max_thinking_tokens,
                tools,
                model
            )
            
            all_messages.extend(messages + [assistant_message])
            final_message = assistant_message
            
            # Check for tool use and execute if needed
            while True:
                tool_use_messages = []
                for content in assistant_message.message.get("content", []):
                    if content.get("type") == "tool_use":
                        tool_use_messages.append(ToolUseBlock(
                            id=content["id"],
                            name=content["name"],
                            input=content["input"]
                        ))
                        tool_use_count += 1
                
                # If no tool use, we're done
                if not tool_use_messages:
                    break
                
                # Execute tools and collect results
                tool_results = []
                for tool_use in tool_use_messages:
                    try:
                        result = await asyncio.to_thread(
                            self.registry.execute_tool,
                            tool_use.name,
                            tool_use.input
                        )
                        
                        if result is None:
                            result_content = "Tool executed successfully (no output)"
                        else:
                            result_content = str(result)
                        
                        tool_result = create_user_message([
                            ToolResultBlock(
                                tool_use_id=tool_use.id,
                                content=result_content,
                                is_error=False
                            ).model_dump()
                        ])
                        tool_results.append(tool_result)
                        
                    except Exception as e:
                        error_result = create_user_message([
                            ToolResultBlock(
                                tool_use_id=tool_use.id,
                                content=f"Tool execution error: {str(e)}",
                                is_error=True
                            ).model_dump()
                        ])
                        tool_results.append(error_result)
                
                # Continue conversation with tool results
                new_messages = all_messages + tool_results
                api_messages = normalize_messages_for_api(new_messages)
                
                assistant_message = await self.client.query(
                    api_messages,
                    self.system_prompt,
                    max_thinking_tokens,
                    tools,
                    model
                )
                
                all_messages.extend(tool_results + [assistant_message])
                final_message = assistant_message
                
                # Safety check to prevent infinite loops
                if len(all_messages) > 50:
                    break
            
            # Calculate final metrics
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Extract final result
            if final_message:
                result_text = ""
                for content in final_message.message.get("content", []):
                    if content.get("type") == "text":
                        result_text += content.get("text", "")
                
                tokens_used = (
                    final_message.message.get("usage", {}).get("input_tokens", 0) +
                    final_message.message.get("usage", {}).get("output_tokens", 0)
                )
                
                return {
                    "status": "completed",
                    "result": result_text,
                    "tool_use_count": tool_use_count,
                    "duration_ms": duration_ms,
                    "tokens_used": tokens_used,
                    "cost_usd": final_message.cost_usd,
                    "final_message": result_text,
                    "execution_details": {
                        "model": model,
                        "message_count": len(all_messages),
                        "thinking_tokens": max_thinking_tokens
                    }
                }
            else:
                return {
                    "status": "error",
                    "error": "No final message received",
                    "duration_ms": duration_ms
                }
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "status": "error",
                "error": str(e),
                "duration_ms": duration_ms,
                "tool_use_count": tool_use_count
            } 