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
    """Context for a Claude Code conversation with build tracking."""
    
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    conversation_summary: str = ""
    file_operations: List[Dict[str, Any]] = field(default_factory=list)
    code_artifacts: Dict[str, str] = field(default_factory=dict)
    turn_count: int = 0
    
    # Enhanced build tracking
    build_attempts: List[Dict[str, Any]] = field(default_factory=list)
    error_patterns: Dict[str, str] = field(default_factory=dict)
    successful_builds: List[Dict[str, Any]] = field(default_factory=list)
    working_commands: Dict[str, str] = field(default_factory=dict)
    
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
        
    def add_build_attempt(self, command: str, success: bool, error_message: Optional[str] = None):
        """Track build attempts and their results."""
        self.build_attempts.append({
            "command": command,
            "success": success,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        })
        
        if success:
            self.successful_builds.append({
                "command": command,
                "timestamp": datetime.now().isoformat()
            })
            # Store working command for future reference
            cmd_type = self._classify_command(command)
            if cmd_type:
                self.working_commands[cmd_type] = command
                
    def add_error_pattern(self, error_type: str, solution: str):
        """Store error patterns and their solutions."""
        self.error_patterns[error_type] = solution
        
    def _classify_command(self, command: str) -> Optional[str]:
        """Classify command type for storage."""
        if "npm" in command or "bun" in command:
            if "install" in command:
                return "frontend_install"
            elif "dev" in command or "start" in command:
                return "frontend_dev"
            elif "build" in command:
                return "frontend_build"
        elif "uvicorn" in command:
            return "backend_start"
        elif "pip install" in command:
            return "backend_install"
        return None


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
    description = """🔧 MANDATORY FINAL PHASE TOOL - Application Builder & Fixer

🎯 WHEN TO USE THIS TOOL:
- After completing frontend and backend development
- When you need to build and test the full application
- When there are build errors, runtime errors, or integration issues
- When the application needs to be made functional and working
- As the FINAL step before considering any development project complete

🚀 WHAT THIS TOOL DOES:
- Builds full-stack applications (React + FastAPI, Next.js + Python, etc.)
- Identifies and fixes ALL build errors, compilation errors, runtime errors
- Resolves integration issues between frontend and backend
- Tests applications thoroughly and fixes functionality issues
- Enhances code to achieve working state (not code quality review)
- Ensures proper deployment and running of both frontend and backend

⚡ AUTOMATIC CAPABILITIES:
- Detects project type (React/Vite frontend, FastAPI backend, etc.)
- Suggests correct build commands (npm/bun install, uvicorn server start)
- Tracks previous build attempts and learns from errors
- Provides workspace-aware context and smart tool selection

🎯 FOCUS: FUNCTIONALITY OVER STYLE
This tool's mission is to MAKE APPLICATIONS WORK, not review code quality. It will make whatever changes are necessary to achieve a fully functional, deployable application.

⚠️ MANDATORY USAGE: Every development project MUST use this tool as the final step to ensure the application actually works before delivery.
    """
    
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
            "max_turns": {
                "type": "integer",
                "description": "Maximum conversation turns (default: 50)",
                "minimum": 1,
                "maximum": 200
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
        self.model = model
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
        """Execute Claude Code task with enhanced workspace detection and build validation."""
        task = tool_input["task"]
        workspace_path = tool_input.get("workspace_path", "")
        provided_context = tool_input.get("context", "")
        context_files = tool_input.get("context_files", [])
        max_turns = tool_input.get("max_turns", 200)
        
        # Get session ID from message history
        session_id = self._get_session_id(message_history)
        session = self.session_manager.get_or_create_session(session_id)
        
        try:
            # Enhanced workspace detection
            workspace_info = await self._detect_workspace_info(workspace_path)
            
            # Build enhanced task with workspace context
            enhanced_task = self._build_enhanced_task(task, workspace_path, workspace_info)
            
            # Generate context if not provided
            if not provided_context and message_history:
                provided_context = await self._generate_context_from_history(message_history, task)
                if provided_context:
                    logger.info("Generated context from message history")
                    
            # Build context prompt with workspace info
            context_prompt = self._build_context_prompt(
                session, provided_context, context_files, workspace_info
            )
            
            # Configure Claude Code options with enhanced tools
            options = ClaudeCodeOptions(
                system_prompt=self._build_system_prompt(),
                append_system_prompt=context_prompt,
                max_turns=max_turns,
                cwd=str(self.workspace_manager.root),
                permission_mode="acceptEdits",  # Auto-accept file edits
                allowed_tools=self._get_enhanced_tools(workspace_info),
            )
    
            # Execute Claude Code query
            messages = await self.run_claude_code(enhanced_task, options)
            
            # Update session with build tracking
            session.turn_count += 1
            if workspace_info:
                session.add_code_artifact("workspace_info", str(workspace_info))
            
            return ToolImplOutput(
                messages[-1].result,
                f"Claude Code completed build/fix task: {task[:50]}...",
                auxiliary_data={
                    "success": True,
                    "session_id": session_id,
                    "turn_count": session.turn_count,
                    "workspace_info": workspace_info,
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
        
    def _build_system_prompt(self) -> str:
        """Build system prompt with comprehensive build and fix guidance."""
        base_prompt = """You are Claude Code, the master application builder and problem solver. Your PRIMARY mission is to MAKE APPLICATIONS WORK.

## CORE MISSION: BUILD, FIX, ENHANCE
- Build the full-stack application and identify ALL build errors
- Fix ALL compilation, runtime, and integration errors
- Enhance existing code to ensure complete functionality
- Test the application thoroughly and resolve any issues
- Make necessary code improvements to achieve working state

## COMMON BUILD COMMANDS BY FRAMEWORK
**Frontend (React/Vite):**
- `npm install` or `bun install` - Install dependencies
- `npm run dev` or `bun run dev` - Start development server
- `npm run build` or `bun run build` - Build for production

**Backend (FastAPI/Python):**
- `pip install -r requirements.txt` - Install dependencies
- `uvicorn main:app --reload --host 0.0.0.0 --port 8000` - Start server
- `python -m pytest` - Run tests

**Full-Stack Detection:**
- Look for `package.json` (frontend), `main.py`/`requirements.txt` (backend)
- Check for `vite.config.js`, `next.config.js`, `app.py`, `main.py`

## ERROR DEBUGGING STRATEGY
1. **Build Errors**: Read error messages carefully, fix imports, dependencies
2. **Runtime Errors**: Check console logs, fix API endpoints, CORS issues
3. **Integration Errors**: Verify frontend-backend communication, port conflicts
4. **Testing**: Run the app, test all functionality, fix what doesn't work

## MANDATORY ACTIONS
- ALWAYS attempt to build and run the application
- Fix errors systematically, starting with dependencies
- Test all functionality after fixes
- Ensure both frontend and backend work together
- Make whatever changes needed for functionality

Focus on FUNCTIONALITY over code style. Make the application work perfectly."""
        return base_prompt
        
    async def _detect_workspace_info(self, workspace_path: str) -> Dict[str, Any]:
        """Detect workspace information for better build context."""
        workspace_info = {
            "type": "unknown",
            "frontend": None,
            "backend": None,
            "build_commands": [],
            "dependencies": []
        }
        
        try:
            base_path = Path(workspace_path) if workspace_path else self.workspace_manager.root
            
            # Check for frontend indicators
            if (base_path / "package.json").exists():
                workspace_info["frontend"] = "react"
                workspace_info["build_commands"].extend([
                    "npm install or bun install",
                    "npm run dev or bun run dev"
                ])
                
            if (base_path / "vite.config.js").exists() or (base_path / "vite.config.ts").exists():
                workspace_info["frontend"] = "react-vite"
                
            # Check for backend indicators
            if (base_path / "main.py").exists():
                workspace_info["backend"] = "fastapi"
                workspace_info["build_commands"].extend([
                    "pip install -r requirements.txt",
                    "uvicorn main:app --reload --host 0.0.0.0 --port 8000"
                ])
                
            if (base_path / "requirements.txt").exists():
                workspace_info["backend"] = "python"
                workspace_info["dependencies"].append("requirements.txt")
                
            # Determine overall type
            if workspace_info["frontend"] and workspace_info["backend"]:
                workspace_info["type"] = "fullstack"
            elif workspace_info["frontend"]:
                workspace_info["type"] = "frontend"
            elif workspace_info["backend"]:
                workspace_info["type"] = "backend"
                
        except Exception as e:
            logger.warning(f"Failed to detect workspace info: {e}")
            
        return workspace_info
    
    def _build_enhanced_task(self, task: str, workspace_path: str, workspace_info: Dict[str, Any]) -> str:
        """Build enhanced task with workspace context."""
        parts = []
        
        if workspace_path:
            parts.append(f"## Current Workspace: {workspace_path}")
            
        if workspace_info.get("type") != "unknown":
            parts.append(f"## Detected Project Type: {workspace_info['type']}")
            
            if workspace_info.get("frontend"):
                parts.append(f"Frontend: {workspace_info['frontend']}")
                
            if workspace_info.get("backend"):
                parts.append(f"Backend: {workspace_info['backend']}")
                
            if workspace_info.get("build_commands"):
                parts.append("## Suggested Build Commands:")
                for cmd in workspace_info["build_commands"]:
                    parts.append(f"- {cmd}")
                    
        parts.append(f"## TASK: {task}")
        parts.append("\n## MANDATORY: Build and test the application to ensure it works!")
        
        return "\n".join(parts)
    
    def _get_enhanced_tools(self, workspace_info: Dict[str, Any]) -> List[str]:
        """Get enhanced tool list based on workspace type."""
        base_tools = ["Read", "Write", "Edit", "MultiEdit", "Bash", "WebSearch", "Glob", "Grep"]
        
        # Add project-specific tools based on detection
        if workspace_info.get("frontend"):
            base_tools.extend(["LS"])  # For frontend file navigation
            
        if workspace_info.get("backend"):
            base_tools.extend(["LS"])  # For backend file navigation
            
        return list(set(base_tools))  # Remove duplicates
    
    def _build_context_prompt(
        self,
        session: ClaudeCodeContext,
        provided_context: str,
        context_files: List[str],
        workspace_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build context prompt with session information and provided context."""
        parts = []
        
        # Add workspace information first
        if workspace_info and workspace_info.get("type") != "unknown":
            parts.append("## Workspace Information")
            parts.append(f"Project Type: {workspace_info['type']}")
            
            if workspace_info.get("frontend"):
                parts.append(f"Frontend: {workspace_info['frontend']}")
            if workspace_info.get("backend"):
                parts.append(f"Backend: {workspace_info['backend']}")
                
            if workspace_info.get("build_commands"):
                parts.append("Build Commands Available:")
                for cmd in workspace_info["build_commands"]:
                    parts.append(f"  - {cmd}")
        
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
                
            # Add build tracking information
            if session.working_commands:
                parts.append("\n## Previously Working Commands:")
                for cmd_type, command in session.working_commands.items():
                    parts.append(f"- {cmd_type}: {command}")
                    
            if session.error_patterns:
                parts.append("\n## Known Error Patterns & Solutions:")
                for error_type, solution in list(session.error_patterns.items())[-5:]:  # Last 5 patterns
                    parts.append(f"- {error_type}: {solution}")
                    
            if session.build_attempts:
                recent_attempts = session.build_attempts[-3:]  # Last 3 attempts
                parts.append(f"\n## Recent Build Attempts:")
                for attempt in recent_attempts:
                    status = "✓" if attempt["success"] else "✗"
                    parts.append(f"- {status} {attempt['command']}")
                    if not attempt["success"] and attempt.get("error_message"):
                        parts.append(f"  Error: {attempt['error_message'][:100]}...")
                
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
