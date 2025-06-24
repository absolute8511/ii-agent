"""Claude Code integration tool for ii-agent."""

import asyncio
import json
import logging
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import anyio
from claude_code_sdk import (
    AssistantMessage,
    ClaudeCodeOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    query,
)

from ii_agent.llm.message_history import MessageHistory
from ii_agent.llm.base import TextPrompt, TextResult
from ii_agent.tools.base import LLMTool, ToolImplOutput
from ii_agent.utils import WorkspaceManager
from ii_agent.core.event import RealtimeEvent

logger = logging.getLogger(__name__)


@dataclass
class ClaudeCodeContext:
    """Context for a Claude Code conversation."""
    
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    conversation_summary: str = ""
    file_operations: List[Dict[str, Any]] = field(default_factory=list)
    code_artifacts: Dict[str, str] = field(default_factory=dict)
    turn_count: int = 0
    
    def update_access_time(self):
        """Update the last accessed time."""
        self.last_accessed = datetime.now()
        
    def add_file_operation(self, operation: str, filepath: str, content: Optional[str] = None):
        """Record a file operation."""
        self.file_operations.append({
            "operation": operation,
            "filepath": filepath,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
    def add_code_artifact(self, name: str, content: str):
        """Store a code artifact."""
        self.code_artifacts[name] = content


class ClaudeCodeSessionManager:
    """Manages Claude Code sessions with memory and context."""
    
    def __init__(self, max_sessions: int = 10, session_ttl_minutes: int = 60):
        self.sessions: OrderedDict[str, ClaudeCodeContext] = OrderedDict()
        self.max_sessions = max_sessions
        self.session_ttl = timedelta(minutes=session_ttl_minutes)
        
    def get_or_create_session(self, session_id: str) -> ClaudeCodeContext:
        """Get existing session or create new one."""
        # Clean up stale sessions
        self._cleanup_stale_sessions()
        
        if session_id in self.sessions:
            # Move to end (LRU)
            self.sessions.move_to_end(session_id)
            session = self.sessions[session_id]
            session.update_access_time()
            return session
            
        # Create new session
        if len(self.sessions) >= self.max_sessions:
            # Remove oldest session
            self.sessions.popitem(last=False)
            
        session = ClaudeCodeContext(session_id=session_id)
        self.sessions[session_id] = session
        return session
        
    def _cleanup_stale_sessions(self):
        """Remove sessions older than TTL."""
        cutoff = datetime.now() - self.session_ttl
        stale_ids = [
            sid for sid, session in self.sessions.items()
            if session.last_accessed < cutoff
        ]
        for sid in stale_ids:
            logger.info(f"Removing stale Claude Code session: {sid}")
            del self.sessions[sid]


class ClaudeCodeTool(LLMTool):
    """Claude Code integration tool."""
    
    name = "claude_code"
    description = """Advanced AI coding assistant that can:
    - Generate complete code implementations
    - Refactor and improve existing code
    - Debug and fix issues
    - Add tests and documentation
    - Perform code reviews
    - Execute complex multi-file operations
    
    Best for complex coding tasks that require understanding context and making multiple related changes.
    
    The 'context' parameter is optional - if not provided, Claude Code will automatically analyze the conversation history to understand the project state.
    
    Note: For very large projects (>10 files), consider breaking down the task into smaller parts to avoid response size limitations."""
    
    input_schema = {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "The coding task to perform"
            },
            "context": {
                "type": "string",
                "description": "Relevant context about previous work, files created, or project state"
            },
            "context_files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of file paths to include as context"
            },
            "mode": {
                "type": "string",
                "enum": ["auto", "generate", "refactor", "debug", "test", "review"],
                "description": "Operation mode (default: auto)"
            },
            "max_turns": {
                "type": "integer",
                "description": "Maximum conversation turns (default: 10)",
                "minimum": 1,
                "maximum": 50
            }
        },
        "required": ["task"]
    }
    
    def __init__(
        self,
        workspace_manager: WorkspaceManager,
        message_queue: Optional[asyncio.Queue] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        session_manager: Optional[ClaudeCodeSessionManager] = None,
        context_llm_client: Optional[Any] = None,
    ):
        self.workspace_manager = workspace_manager
        self.message_queue = message_queue
        self.api_key = api_key
        self.model = model or "claude-3-opus-20240229"
        self.session_manager = session_manager or ClaudeCodeSessionManager()
        self.context_llm_client = context_llm_client
    
    async def run_claude_code(self, task: str, options: ClaudeCodeOptions) -> str:
        """Run Claude Code."""
        messages = []
        async for message in query(prompt=task, options=options):
            print(f"message: {message}")
            messages.append(message)
        return messages
    
    async def run_impl(
        self,
        tool_input: Dict[str, Any],
        message_history: Optional[MessageHistory] = None,
    ) -> ToolImplOutput:
        """Execute Claude Code task."""
        task = tool_input["task"]
        provided_context = tool_input.get("context", "")
        context_files = tool_input.get("context_files", [])
        mode = tool_input.get("mode", "auto")
        max_turns = tool_input.get("max_turns", 10)
        
        # Get session ID from message history
        session_id = self._get_session_id(message_history)
        session = self.session_manager.get_or_create_session(session_id)
        try:
            # Generate context if not provided
            if not provided_context and message_history:
                provided_context = await self._generate_context_from_history(message_history, task)
                if provided_context:
                    logger.info("Generated context from message history")
                    
            # Build context prompt
            context_prompt = self._build_context_prompt(
                session, task, provided_context, context_files, mode
            )
            
            # Configure Claude Code options
            options = ClaudeCodeOptions(
                system_prompt=self._build_system_prompt(mode),
                append_system_prompt=context_prompt,
                max_turns=max_turns,
                cwd=str(self.workspace_manager.root),
                permission_mode="acceptEdits",  # Auto-accept file edits
                allowed_tools=["Read", "Write", "Edit", "MultiEdit", "Bash", "WebSearch"],
            )
    
            # Execute Claude Code query
            messages = await self.run_claude_code(task, options)
            # Update session
            session.turn_count += 1
            return ToolImplOutput(
                messages[-1].result,
                f"Claude Code completed task: {task[:50]}...",
                auxiliary_data={
                    "success": True,
                    "session_id": session_id,
                    "turn_count": session.turn_count,
                }
            )
            
        except Exception as e:
            logger.error(f"Claude Code error: {str(e)}", exc_info=True)
            return ToolImplOutput(
                f"Error executing Claude Code: {str(e)}",
                "Claude Code execution failed",
                auxiliary_data={"success": False, "error": str(e)}
            )
            
    def _get_session_id(self, message_history: Optional[MessageHistory]) -> str:
        """Extract session ID from message history or generate new one."""
        if message_history and hasattr(message_history, "session_id"):
            return message_history.session_id
        return f"claude_code_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def _build_system_prompt(self, mode: str) -> str:
        """Build system prompt based on mode."""
        base_prompt = "You are Claude Code, an advanced AI coding assistant integrated into ii-agent."
        
        mode_prompts = {
            "generate": "Focus on generating new, high-quality code implementations.",
            "refactor": "Focus on improving code structure, readability, and performance.",
            "debug": "Focus on finding and fixing bugs, with clear explanations.",
            "test": "Focus on creating comprehensive test cases and test documentation.",
            "review": "Focus on code review, identifying issues and suggesting improvements.",
            "auto": "Analyze the task and choose the best approach automatically."
        }
        
        return f"{base_prompt} {mode_prompts.get(mode, mode_prompts['auto'])}"
        
    def _build_context_prompt(
        self,
        session: ClaudeCodeContext,
        task: str,
        provided_context: str,
        context_files: List[str],
        mode: str,
    ) -> str:
        """Build context prompt with session information and provided context."""
        parts = []
        
        # Add provided context from the main agent
        if provided_context:
            parts.append("## Context")
            parts.append(provided_context)
        
        # Add session context if this is a continuation
        if session.turn_count > 0:
            parts.append(f"\n## Previous Work in This Session")
            parts.append(f"Session ID: {session.session_id}")
            parts.append(f"Previous turns: {session.turn_count}")
            
            if session.conversation_summary:
                parts.append(f"\nSummary: {session.conversation_summary}")
                
            if session.file_operations:
                parts.append("\n## Recent File Operations:")
                for op in session.file_operations[-10:]:  # Last 10 operations
                    parts.append(f"- {op['operation']}: {op['filepath']}")
                    
            if session.code_artifacts:
                parts.append("\n## Code Artifacts:")
                for name in session.code_artifacts:
                    parts.append(f"- {name}")
                    
        # Add specific context files
        if context_files:
            parts.append(f"\n## Context Files to Consider:")
            for filepath in context_files:
                parts.append(f"- {filepath}")
                
        return "\n".join(parts) if parts else ""
        
    
    async def _generate_context_from_history(self, message_history: MessageHistory, current_task: str) -> str:
        """Generate relevant context from message history using LLM."""
        if not message_history or not self.context_llm_client:
            return ""
            
        # Import at function level to avoid any potential issues
        from ii_agent.llm.base import TextPrompt as TP, TextResult as TR
            
        try:
            # Get recent messages
            messages = message_history.get_messages_for_llm()
            if not messages or len(messages) < 2:  # Need at least some history
                return ""
                
            # Prepare a focused prompt for context generation
            context_prompt = f"""Based on the conversation history below, generate a concise context summary for a coding assistant (Claude Code) that needs to work on this task: "{current_task}"

The context should include:
1. What files have been created or modified (with their purposes)
2. What technologies/frameworks are being used
3. The current state of the project
4. Any relevant implementation details
5. Recent work that relates to the current task

Keep the context concise but informative (2-3 paragraphs max).

Recent conversation (last 10 turns):
"""
            
            # Add recent conversation snippets
            recent_turns = messages[-10:] if len(messages) > 10 else messages
            for i, turn in enumerate(recent_turns):
                for msg in turn:
                    if isinstance(msg, TP):
                        context_prompt += f"\nUser: {msg.text[:300]}"
                    elif isinstance(msg, TR):
                        # Truncate long responses
                        text = msg.text[:500] + "..." if len(msg.text) > 500 else msg.text
                        context_prompt += f"\nAssistant: {text}"
                    elif hasattr(msg, "tool_name"):
                        context_prompt += f"\nTool used: {msg.tool_name}"
                        
            context_prompt += "\n\nGenerate a concise context summary for the coding task:"
            
            # Use the LLM to generate context
            # Format messages for the LLM client
            context_messages = [[TP(text=context_prompt)]]
            
            # Generate using the client's generate method
            response = self.context_llm_client.generate(
                messages=context_messages,
                max_tokens=8192,
                temperature=0.3,  # Lower temperature for more focused summaries
                tools=[]  # No tools needed for context generation
            )
            
            # Extract text from response
            if response and len(response) > 0:
                for item in response:
                    if isinstance(item, TR):
                        return item.text.strip()
            return ""
                
        except Exception as e:
            logger.warning(f"Failed to generate context from history: {e}")
            return ""
        
    async def _process_message(
        self,
        message: Union[UserMessage, AssistantMessage, SystemMessage, ResultMessage],
        session: ClaudeCodeContext,
        result_summary: List[str],
    ):
        """Process a message from Claude Code."""
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    # Add text to summary
                    if block.text.strip():
                        result_summary.append(block.text)
                        
                elif isinstance(block, ToolUseBlock):
                    # Track tool usage
                    tool_info = f"Tool: {block.name}"
                    if hasattr(block, "input") and block.input:
                        tool_info += f" - {json.dumps(block.input)[:100]}..."
                    result_summary.append(tool_info)
                    
                    # Track file operations
                    if block.name in ["Write", "Edit", "MultiEdit"]:
                        filepath = block.input.get("file_path", "unknown")
                        session.add_file_operation(block.name, filepath)
                        
                        # Send real-time update
                        if self.message_queue:
                            await self.message_queue.put(
                                RealtimeEvent(
                                    type="claude_code",
                                    subtype="file_operation",
                                    content={
                                        "operation": block.name,
                                        "filepath": filepath,
                                        "session_id": session.session_id
                                    }
                                )
                            )
                            
                elif isinstance(block, ToolResultBlock):
                    # Process tool results
                    if hasattr(block, "output") and block.output:
                        result_summary.append(f"Result: {str(block.output)[:200]}...")
                        
        elif isinstance(message, ResultMessage):
            # Final result
            if hasattr(message, "content"):
                result_summary.append(f"Final: {message.content}")