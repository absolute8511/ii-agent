"""Claude Code integration tool for ii-agent."""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from claude_code_sdk import (
    ClaudeCodeOptions,
    query,
)

from ii_agent.llm.message_history import MessageHistory
from ii_agent.tools.base import LLMTool, ToolImplOutput
from ii_agent.utils import WorkspaceManager

logger = logging.getLogger(__name__)


@dataclass
class SimpleDevSession:
    """Lightweight session tracking for full-stack development."""
    
    session_id: str
    last_task: str = ""
    workspace_info: Dict[str, Any] = field(default_factory=dict)
    context_summary: str = ""
    created_at: datetime = field(default_factory=datetime.now)


class SimpleSessionCache:
    """Simple in-memory session cache."""
    
    def __init__(self):
        self.sessions: Dict[str, SimpleDevSession] = {}
    
    def get_or_create(self, session_id: str) -> SimpleDevSession:
        """Get existing session or create new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = SimpleDevSession(session_id=session_id)
        return self.sessions[session_id]


class FullStackDeveloperTool(LLMTool):
    """Full-stack web development tool."""
    
    name = "fullstack_developer"
    description = """🚀 SIMPLIFIED FULL-STACK DEVELOPER - Zero Configuration Required

Just tell me what you want to build and I'll create it for you!

✨ EXAMPLES:
- "Create a login page" 
- "Build a REST API for users"
- "Add dark mode toggle"
- "Implement a shopping cart"

🛠️ I BUILD:
- React/Next.js frontend applications
- FastAPI/Node.js backend services  
- Database schemas and APIs
- Authentication and authorization
- Responsive, accessible UIs

⚡ SMART AUTO-DETECTION:
- Automatically detects your project structure
- Chooses the right frameworks and patterns
- Generates context from conversation history
- Zero configuration required

🔄 DELEGATION:
I'll clearly indicate when the main agent needs specialized tools for deployment, media generation, or system operations.

Just describe what you want - I'll handle the rest!"""
    
    input_schema = {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "What you want to build or implement (e.g., 'Create a login page', 'Build a REST API for users', 'Add dark mode toggle')"
            }
        },
        "required": ["task"]
    }
    
    def __init__(
        self,
        workspace_manager: WorkspaceManager,
        message_queue: Optional[asyncio.Queue] = None,
        api_key: Optional[str] = None,
        context_llm_client: Optional[Any] = None,
    ):
        self.workspace_manager = workspace_manager
        self.message_queue = message_queue
        self.api_key = api_key
        self.session_cache = SimpleSessionCache()
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
        """Execute full-stack development task with minimal setup."""
        task = tool_input["task"]
        
        # Get session
        session_id = self._get_session_id(message_history)
        session = self.session_cache.get_or_create(session_id)
        
        try:
            # Auto-detect workspace
            workspace_info = await self._auto_detect_workspace()
            session.workspace_info = workspace_info
            
            # Auto-generate context from conversation history
            context = await self._auto_generate_context(message_history, task, session)
            session.context_summary = context[:200] + "..." if len(context) > 200 else context
            
            # Build simple task prompt
            enhanced_task = self._build_simple_task(task, workspace_info, context)
            
            # Configure Claude Code with smart defaults
            options = ClaudeCodeOptions(
                system_prompt=self._build_simple_system_prompt(),
                append_system_prompt=context,
                max_turns=200,
                cwd=str(self.workspace_manager.root),
                permission_mode="acceptEdits",
                allowed_tools=["Read", "Write", "Edit", "MultiEdit", "Bash", "WebSearch", "Glob", "Grep", "LS"],
            )
    
            # Execute Claude Code
            messages = await self.run_claude_code(enhanced_task, options)
            session.last_task = task
            
            # Extract result
            final_result = messages[-1].result if messages else ""
            
            return ToolImplOutput(
                final_result,
                f"Full-Stack Developer: {task[:50]}{'...' if len(task) > 50 else ''}",
                auxiliary_data={
                    "success": True,
                    "session_id": session_id,
                    "workspace_type": workspace_info.get("type", "unknown"),
                    "delegation_detected": self._contains_delegation_indicators(final_result),
                }
            )
            
        except Exception as e:
            logger.error(f"Full-Stack Developer error: {str(e)}", exc_info=True)
            return ToolImplOutput(
                f"Error: {str(e)}",
                "Full-Stack Developer execution failed",
                auxiliary_data={"success": False, "error": str(e)}
            )
            
    def _get_session_id(self, message_history: Optional[MessageHistory]) -> str:
        """Extract session ID from message history or generate new one."""
        if message_history and hasattr(message_history, "session_id"):
            return message_history.session_id
        return f"fullstack_dev_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def _auto_detect_workspace(self) -> Dict[str, Any]:
        """Auto-detect workspace with minimal detection."""
        try:
            base_path = self.workspace_manager.root
            workspace_info = {"type": "unknown"}
            
            # Simple detection
            if (base_path / "package.json").exists():
                workspace_info["type"] = "frontend"
                if (base_path / "next.config.js").exists():
                    workspace_info["framework"] = "nextjs"
                elif (base_path / "vite.config.js").exists():
                    workspace_info["framework"] = "vite"
                else:
                    workspace_info["framework"] = "react"
                    
            if (base_path / "requirements.txt").exists() or (base_path / "main.py").exists():
                workspace_info["type"] = "fullstack" if workspace_info["type"] == "frontend" else "backend"
                workspace_info["backend"] = "python"
                
            return workspace_info
        except Exception:
            return {"type": "unknown"}
    
    async def _auto_generate_context(self, message_history: Optional[MessageHistory], task: str, session: SimpleDevSession) -> str:
        """Auto-generate context from conversation history."""
        context_parts = []
        
        # Add session context if available
        if session.last_task:
            context_parts.append(f"Previous task: {session.last_task}")
            
        if session.workspace_info.get("type") != "unknown":
            context_parts.append(f"Project type: {session.workspace_info['type']}")
            
        # Add simple context from message history
        if message_history and self.context_llm_client:
            try:
                from ii_agent.llm.base import TextPrompt as TP
                messages = message_history.get_messages_for_llm()
                if messages and len(messages) > 1:
                    # Simple context extraction
                    recent_context = "Recent conversation context available."
                    context_parts.append(recent_context)
            except Exception:
                pass
                
        return "\n".join(context_parts) if context_parts else "No additional context available."
    
    def _build_simple_task(self, task: str, workspace_info: Dict[str, Any], context: str) -> str:
        """Build enhanced task with auto-detected information."""
        parts = [f"Task: {task}"]
        
        if workspace_info.get("type") != "unknown":
            parts.append(f"Project: {workspace_info['type']} application")
            if workspace_info.get("framework"):
                parts.append(f"Framework: {workspace_info['framework']}")
                
        if context and context != "No additional context available.":
            parts.append(f"Context: {context}")
            
        return "\n".join(parts)
    
    def _build_simple_system_prompt(self) -> str:
        """Build simplified system prompt for full-stack development."""
        return """You are an expert Full-Stack Web Developer. Build production-ready web applications using modern best practices.

## YOUR CAPABILITIES:
- Frontend: React, Next.js, TypeScript, Tailwind CSS
- Backend: FastAPI, Node.js, REST APIs
- Database: PostgreSQL, MongoDB, Prisma
- Authentication: NextAuth.js, JWT, OAuth
- Tools: You have access to Read, Write, Edit, MultiEdit, Bash, WebSearch, Glob, Grep, LS

## APPROACH:
1. Understand the task
2. Auto-detect project structure and technology
3. Implement clean, maintainable code
4. Follow modern patterns and best practices

## DELEGATION:
If you need specialized tools (deployment, image generation, browser automation, etc.), clearly state:
"For [task], the main agent will need to use [ToolName] to complete this operation."

Build features that are robust, scalable, and production-ready."""
                
    def _contains_delegation_indicators(self, text: str) -> bool:
        """Check if the result contains indicators that delegation is needed."""
        delegation_indicators = [
            "main agent will need to use",
            "main agent should use",
            "delegate to main agent",
            "requires deployment",
            "needs to be deployed",
            "use DeployTool",
            "use ImageGenerateTool",
            "use VideoGenerateTool",
            "use DatabaseConnection",
            "use BrowserNavigationTool",
            "use AudioGenerateTool",
            "beyond my scope",
            "outside my capabilities"
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in delegation_indicators)
        
    def _extract_delegation_info(self, text: str, original_task: str) -> Optional[Dict[str, Any]]:
        """Extract delegation information from the result text."""
        try:
            # Look for specific tool mentions
            tool_patterns = {
                "DeployTool": r"deploy(?:ment|ing|)|use DeployTool",
                "ImageGenerateTool": r"image generation|use ImageGenerateTool|generate.*image",
                "VideoGenerateTool": r"video generation|use VideoGenerateTool|generate.*video",
                "DatabaseConnection": r"database connection|use DatabaseConnection|connect.*database",
                "BrowserNavigationTool": r"browser automation|use BrowserNavigationTool|navigate.*browser",
                "AudioGenerateTool": r"audio generation|use AudioGenerateTool|generate.*audio",
                "PdfTextExtractTool": r"pdf processing|use PdfTextExtractTool|extract.*pdf",
            }
            
            text_lower = text.lower()
            for tool_name, pattern in tool_patterns.items():
                if re.search(pattern, text_lower):
                    # Extract the specific task that needs delegation
                    task_context = self._extract_task_context(text, pattern)
                    return {
                        "task": task_context or f"Complete {tool_name} operation for: {original_task}",
                        "tool": tool_name,
                        "context": {
                            "original_task": original_task,
                            "delegation_reason": text[:200] + "..." if len(text) > 200 else text,
                            "timestamp": datetime.now().isoformat()
                        }
                    }
            return None
        except Exception as e:
            logger.warning(f"Failed to extract delegation info: {e}")
            return None
            
    def _extract_task_context(self, text: str, pattern: str) -> Optional[str]:
        """Extract the specific task context around a delegation pattern."""
        try:
            # Find sentences containing the pattern
            sentences = re.split(r'[.!?]+', text)
            for sentence in sentences:
                if re.search(pattern, sentence.lower()):
                    return sentence.strip()
            return None
        except Exception:
            return None