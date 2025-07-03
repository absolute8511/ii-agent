"""Claude Code integration tool for ii-agent."""

import logging
from typing import Any, Dict, Optional

from ii_agent.llm.message_history import MessageHistory
from ii_agent.tools.base import LLMTool, ToolImplOutput
from ii_agent.utils.workspace_manager import WorkspaceManager
from ii_agent.tools.clients.claude_code_client import ClaudeCodeClient
from ii_agent.core.storage.models.settings import Settings

# Keep backwards compatibility with direct SDK usage
try:
    from claude_code_sdk import ClaudeCodeOptions, query
    CLAUDE_CODE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_CODE_SDK_AVAILABLE = False
    ClaudeCodeOptions = None
    query = None

logger = logging.getLogger(__name__)


class CodingAssistantTool(LLMTool):
    """Coding assistant tool that delegates complex coding tasks to Claude Code."""
    
    name = "coding_assistant"
    description = """Expert coding assistant that handles all programming tasks. Use this tool whenever you need to write, modify, debug, or analyze code.

WHEN TO USE:
• Any task involving writing or editing code files
• Building new features, components, or applications  
• Fixing bugs, errors, or performance issues
• Refactoring, optimizing, or restructuring code
• Writing unit tests, integration tests, or test suites
• Code analysis, documentation, or architectural planning
• Installing dependencies or configuring development environments

CAPABILITIES:
• Full read/write access to all workspace files
• Can execute terminal commands and run code
• Can search codebases and analyze existing patterns
• Can install packages and manage dependencies
• Can run tests and validate implementations
• Can search the web for documentation and best practices

USE THIS TOOL for any programming-related task instead of trying to code manually. Provide clear task descriptions and any relevant context about requirements or constraints."""
    
    input_schema = {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "The coding task to accomplish. Be specific about requirements, expected behavior, and any constraints."
            },
            "context": {
                "type": "string",
                "description": "Additional context about the project, such as existing code structure, dependencies, or specific requirements",
                "default": ""
            }
        },
        "required": ["task"]
    }
    
    def __init__(
        self,
        workspace_manager: WorkspaceManager,
        llm_client: Optional[Any] = None,
        settings: Optional[Settings] = None,
    ):
        self.workspace_manager = workspace_manager
        self.llm_client = llm_client
        self.settings = settings
        
        # Initialize Claude Code client if settings are available
        self.claude_code_client = None
        if settings:
            try:
                self.claude_code_client = ClaudeCodeClient(settings)
                logger.info(f"Claude Code client initialized for mode: {settings.sandbox_config.mode}")
            except Exception as e:
                logger.warning(f"Failed to initialize Claude Code client: {e}")
                self.claude_code_client = None
    
    async def run_claude_code(self, task: str, options: Dict[str, Any]) -> list:
        """Run Claude Code using the appropriate client (local or remote)."""
        if self.claude_code_client:
            # Use the client-based approach (supports both local and Docker modes)
            result = await self.claude_code_client.execute_task(task, options)
            if result.success:
                return result.messages
            else:
                raise Exception(f"Claude Code execution failed: {result.error}")
        else:
            # Fallback to direct SDK usage (legacy local mode)
            if not CLAUDE_CODE_SDK_AVAILABLE:
                raise ImportError("claude_code_sdk not available and no client configured")
            
            # Convert options dict back to ClaudeCodeOptions for legacy compatibility
            claude_options = ClaudeCodeOptions(**options)
            messages = []
            async for message in query(prompt=task, options=claude_options):
                messages.append(message)
            return messages
    
    async def run_impl(
        self,
        tool_input: Dict[str, Any],
        message_history: Optional[MessageHistory] = None,
    ) -> ToolImplOutput:
        """Execute coding assistant task by delegating to Claude Code."""
        task = tool_input["task"]
        additional_context = tool_input.get("context", "")
        
        logger.info(f"Coding Assistant invoked with task: {task[:100]}...")
        
        # Build context from message history if available
        context_summary = ""
        if message_history is not None:
            try:
                message_lists = message_history.get_messages_for_llm()
                if message_lists:
                    context = message_history._context_manager.generate_complete_conversation_summary(message_lists)
                    if context:
                        context_summary = f"\n\nContext from previous conversation:\n{context}"
            except Exception as e:
                logger.warning(f"Failed to generate context summary: {e}")
        
        # Combine additional context with conversation context
        if additional_context:
            context_summary = f"{context_summary}\n\nAdditional context:\n{additional_context}"
        
        try:
            # Configure Claude Code with smart defaults
            options = {
                "system_prompt": self._build_simple_system_prompt(),
                "append_system_prompt": context_summary if context_summary else None,
                "max_turns": 200,
                "cwd": str(self.workspace_manager.root_path()),
                "permission_mode": "acceptEdits",
                "allowed_tools": ["Read", "Write", "Edit", "MultiEdit", "Bash", "WebSearch", "Glob", "Grep", "LS"],
            }
    
            logger.info(f"Delegating to Claude Code with workspace: {self.workspace_manager.root}")
            
            # Execute Claude Code
            messages = await self.run_claude_code(task, options)
            
            # Extract result
            if not messages:
                logger.warning("No messages returned from Claude Code")
                return ToolImplOutput(
                    "Claude Code did not return any response. Please try again with a more specific task.",
                    "Coding Assistant: No response",
                    auxiliary_data={"success": False, "error": "No response from Claude Code"}
                )
            
            final_result = messages[-1].result if hasattr(messages[-1], 'result') else str(messages[-1])
            
            logger.info(f"Coding Assistant completed successfully after {len(messages)} turns")
            
            return ToolImplOutput(
                final_result,
                f"Coding Assistant completed: {task[:50]}{'...' if len(task) > 50 else ''}",
                auxiliary_data={
                    "success": True,
                    "turns": len(messages),
                    "workspace": str(self.workspace_manager.root)
                }
            )
            
        except Exception as e:
            logger.error(f"Coding Assistant error: {str(e)}", exc_info=True)
            return ToolImplOutput(
                f"Error executing coding task: {str(e)}\n\nPlease check the logs for more details.",
                "Coding Assistant execution failed",
                auxiliary_data={"success": False, "error": str(e)}
            )
    
    def _build_simple_system_prompt(self) -> str:
        """Build a comprehensive system prompt for Claude Code."""
        workspace_path = self.workspace_manager.root_path()
        return f"""You are an expert coding assistant integrated with ii-agent, specialized in implementing complex coding tasks.

Current workspace: {workspace_path}

Your Role:
- You are a coding expert within the ii-agent ecosystem
- You handle implementation details while the main agent handles planning and coordination
- Focus exclusively on coding tasks - implementation, debugging, refactoring, and testing

Your Capabilities:
- Full access to the workspace files and directories
- Can read, write, edit, and execute code
- Can search for patterns across the codebase using Glob and Grep
- Can run terminal commands, install dependencies, and execute tests
- Can search the web for documentation, best practices, and solutions

Guidelines:
1. Code Quality:
   - Write clean, maintainable, and well-documented code
   - Follow existing code patterns and conventions in the workspace
   - Implement proper error handling and edge case management
   - Add appropriate comments and documentation

2. Testing:
   - Write tests for new functionality when possible
   - Run existing tests to ensure no regressions
   - Verify your implementation works as expected

3. Communication:
   - Provide clear summaries of what you implemented
   - Explain any architectural decisions or trade-offs
   - Report any issues or blockers encountered
   - Suggest next steps if the task requires further work

4. Best Practices:
   - Use version control best practices (though don't commit unless asked)
   - Follow security best practices (never expose secrets or credentials)
   - Optimize for performance when relevant
   - Consider scalability and maintainability

Remember: You are the coding expert. The main agent will handle planning, web browsing, deployments, and coordination with other tools. Focus on delivering high-quality code implementations."""
    
    def get_tool_start_message(self, tool_input: Dict[str, Any]) -> str:
        """Return a user-friendly message when the tool starts."""
        task = tool_input["task"]
        return f"Delegating coding task to Coding Assistant: {task[:80]}{'...' if len(task) > 80 else ''}"
