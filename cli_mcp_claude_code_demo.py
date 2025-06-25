#!/usr/bin/env python3
"""
CLI interface for demonstrating MCP (Context7) + Claude Code integration with ii-agent.

This script provides a command-line interface specifically configured
for testing the combined power of Context7 MCP (real-time docs) and Claude Code tools.

Example use cases:
- "Use Context7 to get the latest React hooks documentation, then use Claude Code to build a modern React component"
- "Get FastAPI documentation via Context7 and create a REST API with Claude Code"
- "Use Context7 to research pandas DataFrame operations and build a data analysis script with Claude Code"
"""

import os
import argparse
import logging
import asyncio
from dotenv import load_dotenv
from pathlib import Path

from ii_agent.llm.message_history import MessageHistory
from ii_agent.tools.mcp import MCPRegistry

load_dotenv()

from ii_agent.core.event import RealtimeEvent, EventType
from ii_agent.utils.constants import TOKEN_BUDGET
from utils import parse_common_args, create_workspace_manager_for_connection
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from ii_agent.tools import get_system_tools
from ii_agent.prompts.system_prompt import get_system_prompt
from utils import WorkSpaceMode
from ii_agent.agents.function_call import FunctionCallAgent
from ii_agent.utils import WorkspaceManager
from ii_agent.llm import get_client
from ii_agent.llm.context_manager.llm_summarizing import LLMSummarizingContextManager
from ii_agent.llm.token_counter import TokenCounter
from ii_agent.db.manager import Sessions

MAX_OUTPUT_TOKENS_PER_TURN = 32768
MAX_TURNS = 200

async def setup_mcp_integration(workspace_path: Path, console: Console) -> MCPRegistry:
    """Setup MCP registry and Context7 integration."""
    
    console.print("\n[bold yellow]🔧 Setting up MCP Integration...[/bold yellow]")
    
    try:
        # Initialize MCP registry
        registry = MCPRegistry(workspace_root=workspace_path)
        
        # Initialize with Context7 from .mcprc (if available)
        success = await registry.initialize()
        
        if success:
            # Get available MCP tools
            mcp_tools = await registry.get_mcp_tools()
            
            if mcp_tools:
                console.print(f"[bold green]✅ MCP Integration Ready[/bold green]")
                console.print(f"[green]Found {len(mcp_tools)} Context7 tools: {[t.name for t in mcp_tools]}[/green]")
                return registry
            else:
                console.print("[yellow]⚠️  No MCP tools found. Context7 may not be configured.[/yellow]")
                console.print("[yellow]Create a .mcprc file or check the configuration.[/yellow]")
                return None
        else:
            console.print("[yellow]⚠️  MCP initialization failed. Context7 tools not available.[/yellow]")
            return None
            
    except Exception as e:
        console.print(f"[red]❌ MCP setup error: {str(e)}[/red]")
        return None

def show_demo_examples(console: Console):
    """Show example prompts that demonstrate MCP + Claude Code integration."""
    
    table = Table(title="🚀 MCP + Claude Code Demo Examples", show_header=True, header_style="bold magenta")
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Example Prompt", style="white")
    
    examples = [
        ("React Development", "Use Context7 to get the latest React hooks documentation, then use Claude Code to create a modern data fetching component with error handling"),
        ("FastAPI Backend", "Get current FastAPI documentation via Context7 and build a REST API with authentication using Claude Code"),
        ("Data Analysis", "Use Context7 to research pandas DataFrame operations and create a comprehensive data analysis script with Claude Code"),
        ("Next.js App", "Get Next.js 14 documentation from Context7 and build a full-stack todo application with Claude Code"),
        ("Python Automation", "Research the latest requests library features with Context7 and build a web scraping tool using Claude Code"),
        ("Express.js API", "Use Context7 to get Express.js middleware documentation and create a secure API server with Claude Code"),
        ("TypeScript Project", "Get TypeScript 5.x documentation via Context7 and refactor a JavaScript project to TypeScript using Claude Code"),
        ("Database Integration", "Research SQLAlchemy ORM patterns with Context7 and implement a database layer using Claude Code"),
        ("Testing Framework", "Get pytest documentation from Context7 and create comprehensive tests for existing code using Claude Code"),
        ("Deployment Setup", "Research Docker best practices with Context7 and containerize an application using Claude Code")
    ]
    
    for category, prompt in examples:
        table.add_row(category, prompt)
    
    console.print(table)
    console.print()

async def async_main():
    """Async main entry point"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="CLI for demonstrating MCP (Context7) + Claude Code integration with ii-agent"
    )
    parser = parse_common_args(parser)
    
    # Add Claude Code specific arguments
    parser.add_argument(
        "--claude-code-api-key",
        type=str,
        default=os.environ.get("ANTHROPIC_API_KEY"),
        help="API key for Claude Code (defaults to ANTHROPIC_API_KEY env var)",
    )
    parser.add_argument(
        "--claude-code-model",
        type=str,
        default="claude-3-opus-20240229",
        help="Claude Code model to use",
    )
    parser.add_argument(
        "--no-claude-code",
        action="store_true",
        default=False,
        help="Disable Claude Code tool (for comparison testing)",
    )
    parser.add_argument(
        "--no-mcp",
        action="store_true",
        default=False,
        help="Disable MCP/Context7 integration",
    )
    parser.add_argument(
        "--claude-code-session-ttl",
        type=int,
        default=60,
        help="Session TTL in minutes for Claude Code",
    )

    args = parser.parse_args()
    if os.path.exists(args.logs_path):
        os.remove(args.logs_path)
    logger_for_agent_logs = logging.getLogger("agent_logs")
    logger_for_agent_logs.setLevel(logging.DEBUG)
    # Prevent propagation to root logger to avoid duplicate logs
    logger_for_agent_logs.propagate = False
    logger_for_agent_logs.addHandler(logging.FileHandler(args.logs_path))
    if not args.minimize_stdout_logs:
        logger_for_agent_logs.addHandler(logging.StreamHandler())

    # Initialize console
    console = Console()

    # Create a new workspace manager for the CLI session
    workspace_manager, session_id = create_workspace_manager_for_connection(
        args.workspace, args.use_container_workspace
    )
    workspace_path = Path(workspace_manager.root)
    
    # Create a new session and get its workspace directory
    Sessions.create_session(
        session_uuid=session_id, workspace_path=workspace_manager.root
    )
    logger_for_agent_logs.info(
        f"Created new session {session_id} with workspace at {workspace_manager.root}"
    )

    # Setup MCP integration
    mcp_registry = None
    if not args.no_mcp:
        console.print(f"[cyan]Workspace path for MCP: {workspace_path}[/cyan]")
        console.print(f"[cyan]Current working directory: {Path.cwd()}[/cyan]")
        
        # Check if .mcprc exists in workspace or current directory
        mcprc_workspace = workspace_path / ".mcprc"
        mcprc_current = Path.cwd() / ".mcprc"
        
        console.print(f"[cyan]Checking for .mcprc at workspace: {mcprc_workspace.exists()}[/cyan]")
        console.print(f"[cyan]Checking for .mcprc at current dir: {mcprc_current.exists()}[/cyan]")
        
        # Use current directory for MCP registry if .mcprc exists there
        mcp_path = Path.cwd() if mcprc_current.exists() else workspace_path
        console.print(f"[cyan]Using MCP path: {mcp_path}[/cyan]")
        
        mcp_registry = await setup_mcp_integration(mcp_path, console)

    # Print welcome message
    if not args.minimize_stdout_logs:
        claude_code_status = "Disabled" if args.no_claude_code else "Enabled"
        mcp_status = "Disabled" if args.no_mcp else ("Enabled" if mcp_registry else "Failed")
        
        welcome_text = Text()
        welcome_text.append("MCP + Claude Code Integration Demo\n\n", style="bold")
        welcome_text.append(f"Session ID: {session_id}\n", style="cyan")
        welcome_text.append(f"Workspace: {workspace_path}\n", style="cyan")
        welcome_text.append(f"Claude Code: {claude_code_status}\n", style="green" if not args.no_claude_code else "red")
        welcome_text.append(f"MCP/Context7: {mcp_status}\n", style="green" if mcp_registry else "yellow")
        welcome_text.append(f"Claude Model: {args.claude_code_model}\n\n", style="cyan")
        
        if mcp_registry:
            welcome_text.append("🎯 Context7 provides real-time documentation\n", style="green")
        welcome_text.append("⚡ Claude Code enables advanced code generation\n", style="green")
        welcome_text.append("🚀 Combined: Up-to-date docs + powerful coding\n\n", style="bold green")
        
        welcome_text.append("Type your instructions or try the examples below.\n", style="white")
        welcome_text.append("Press Ctrl+C to exit. Type 'exit' or 'quit' to end.", style="white")

        console.print(Panel(
            welcome_text,
            title="[bold blue]MCP + Claude Code Demo CLI[/bold blue]",
            border_style="blue",
            padding=(1, 2),
        ))
        
        # Show demo examples
        show_demo_examples(console)
        
    else:
        logger_for_agent_logs.info(
            f"MCP + Claude Code CLI started with session {session_id}. Waiting for user input."
        )

    # Initialize LLM client
    client_kwargs = {
        "model_name": args.model_name,
    }
    if args.llm_client == "anthropic-direct":
        client_kwargs["use_caching"] = False
        client_kwargs["project_id"] = args.project_id
        client_kwargs["region"] = args.region
    elif args.llm_client == "openai-direct":
        client_kwargs["azure_model"] = args.azure_model
        client_kwargs["cot_model"] = args.cot_model

    client = get_client(args.llm_client, **client_kwargs)

    # Initialize token counter
    token_counter = TokenCounter()

    # Create context manager
    context_manager = LLMSummarizingContextManager(
        client=client,
        token_counter=token_counter,
        logger=logger_for_agent_logs,
        token_budget=TOKEN_BUDGET,
    )
    init_history = MessageHistory(context_manager)
    # Set session ID for history to enable Claude Code session management
    init_history.session_id = session_id

    queue = asyncio.Queue()
    
    # Configure tool arguments with both Claude Code and MCP
    tool_args = {
        "deep_research": False,
        "pdf": True,
        "media_generation": False,
        "audio_generation": False,
        "browser": True,
        "memory_tool": args.memory_tool,
        "sequential_thinking": True,  # Enable for complex reasoning
        # Claude Code specific configuration
        "claude_code": not args.no_claude_code,
        "claude_code_api_key": args.claude_code_api_key,
        "claude_code_model": args.claude_code_model,
        # MCP integration handled separately to avoid event loop issues
    }
    
    # Get regular system tools
    tools = get_system_tools(
        client=client,
        workspace_manager=workspace_manager,
        message_queue=queue,
        tool_args=tool_args,
    )
    
    # Add MCP tools if available
    if mcp_registry:
        try:
            mcp_tools = await mcp_registry.get_mcp_tools()
            tools.extend(mcp_tools)
            console.print(f"[green]✅ Added {len(mcp_tools)} MCP tools to tool list[/green]")
            
            # Debug: Show MCP tool details
            for mcp_tool in mcp_tools:
                console.print(f"[dim]MCP Tool: {mcp_tool.name} (type: {type(mcp_tool).__name__})[/dim]")
                
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not add MCP tools: {str(e)}[/yellow]")
    
    # Log available tools before creating agent
    tool_names = [tool.name for tool in tools]
    logger_for_agent_logs.info(f"Available tools before agent creation: {', '.join(tool_names)}")
    console.print(f"[cyan]Total tools before agent creation: {len(tools)}[/cyan]")
    
    # Enhanced system prompt that knows about both Context7 and Claude Code
    enhanced_system_prompt = get_system_prompt(WorkSpaceMode.LOCAL) + """

## Special Tool Integration Notes:

### Context7 MCP Tools (if available):
You have access to Context7 tools for real-time documentation:
- **resolve-library-id**: Convert library names (e.g., "react", "fastapi") to Context7-compatible IDs
- **get-library-docs**: Fetch current, up-to-date documentation from official sources

Always use Context7 BEFORE coding to ensure you have the latest information:
1. Call resolve-library-id with the library name
2. Use get-library-docs with the returned library ID and specific topic
3. Apply the current documentation in your code generation

### Claude Code Tool (if available):
Use the claude_code tool for complex code generation, refactoring, and file operations:
- Creating new applications and projects
- Refactoring existing code following best practices
- Adding comprehensive tests and documentation
- Code reviews and security analysis
- Complex multi-file modifications

### Optimal Workflow:
1. **Research Phase**: Use Context7 to get current documentation
2. **Planning Phase**: Use sequential_thinking to plan the implementation
3. **Implementation Phase**: Use claude_code to generate/modify code
4. **Verification Phase**: Use claude_code to review and test

This combination provides both up-to-date knowledge and powerful implementation capabilities.
"""
    
    # Create agent with all tools (including MCP tools)
    agent = FunctionCallAgent(
        system_prompt=enhanced_system_prompt,
        client=client,
        workspace_manager=workspace_manager,
        tools=tools,  # This now includes MCP tools
        message_queue=queue,
        logger_for_agent_logs=logger_for_agent_logs,
        init_history=init_history,
        max_output_tokens_per_turn=MAX_OUTPUT_TOKENS_PER_TURN,
        max_turns=MAX_TURNS,
        session_id=session_id,
    )
    
    # Verify MCP tools are available
    available_tool_names = [tool.name for tool in agent.tool_manager.get_tools()]
    console.print(f"[cyan]Total tools in agent: {len(available_tool_names)}[/cyan]")
    logger_for_agent_logs.info(f"Available tools in agent: {', '.join(available_tool_names)}")
    
    if mcp_registry:
        mcp_tool_names = ["resolve-library-id", "get-library-docs"]
        mcp_tools_found = [name for name in mcp_tool_names if name in available_tool_names]
        
        if mcp_tools_found:
            console.print(f"[green]✅ MCP tools confirmed in agent: {mcp_tools_found}[/green]")
        else:
            console.print(f"[red]❌ MCP tools not found in agent tool manager[/red]")
            console.print(f"[yellow]Available tools in agent: {available_tool_names[:10]}...[/yellow]")
            
            # Check if any tools have "mcp" in their name
            mcp_related = [name for name in available_tool_names if "mcp" in name.lower() or "context" in name.lower()]
            if mcp_related:
                console.print(f"[yellow]Found MCP-related tools: {mcp_related}[/yellow]")

    # Create background task for message processing
    message_task = agent.start_message_processing()

    loop = asyncio.get_running_loop()
    
    # Predefined demo prompts to showcase the integration
    demo_prompts = [
        """Use Context7 to get the latest React hooks documentation, then use Claude Code to create a modern React component that:
1. Fetches data from an API using custom hooks
2. Handles loading and error states
3. Implements proper TypeScript types
4. Includes comprehensive tests
Focus on using the most current React patterns from Context7.""",
        
        """Get FastAPI documentation via Context7 and use Claude Code to build a REST API that:
1. Implements JWT authentication
2. Has proper request/response models with Pydantic
3. Includes database integration with SQLAlchemy
4. Has comprehensive API documentation
5. Includes proper error handling and logging
Make sure to use the latest FastAPI features from Context7.""",
        
        """Research pandas DataFrame operations with Context7 and create a data analysis script using Claude Code that:
1. Loads and cleans CSV data
2. Performs statistical analysis
3. Creates visualizations with matplotlib/seaborn
4. Generates a comprehensive report
5. Includes proper error handling and data validation
Use the most current pandas methods from Context7."""
    ]
    
    current_demo = 0

    if not args.minimize_stdout_logs:
        console.print("\n[bold cyan]🎯 Demo Mode Available:[/bold cyan]")
        console.print("• Type 'demo' to run the next demonstration")
        console.print("• Type 'demo list' to see all available demos")
        console.print("• Or enter your own custom prompt")
        console.print()

    # Handle single prompt mode
    if args.prompt:
        user_input = args.prompt
        console.print(f"\n[bold yellow]Running with prompt:[/bold yellow] {user_input}")
        
        try:
            result = await agent.run_agent_async(user_input, resume=True)
            logger_for_agent_logs.info(f"Agent: {result}")
            console.print(f"\n[bold green]Result:[/bold green] {result}")
        except Exception as e:
            logger_for_agent_logs.error(f"Error: {str(e)}")
            console.print(f"[red]Error: {str(e)}[/red]")
        
        # Cleanup and exit
        if mcp_registry:
            await mcp_registry.shutdown()
        message_task.cancel()
        return

    # Main interaction loop
    try:
        while True:
            # Use async input
            user_input = await loop.run_in_executor(
                None, lambda: input("User input: ")
            )

            # Handle demo commands
            if user_input.lower() == "demo":
                if current_demo < len(demo_prompts):
                    user_input = demo_prompts[current_demo]
                    console.print(f"\n[bold yellow]🎯 Running Demo {current_demo + 1}:[/bold yellow]")
                    console.print(f"[yellow]{user_input}[/yellow]\n")
                    current_demo += 1
                else:
                    console.print("[yellow]All demos completed! Enter your own prompts or type 'demo' to restart from demo 1.[/yellow]")
                    current_demo = 0
                    continue
            elif user_input.lower() == "demo list":
                console.print("\n[bold cyan]Available Demo Prompts:[/bold cyan]")
                for i, prompt in enumerate(demo_prompts, 1):
                    console.print(f"\n[cyan]Demo {i}:[/cyan]")
                    console.print(f"[white]{prompt[:100]}...[/white]")
                console.print()
                continue

            agent.message_queue.put_nowait(
                RealtimeEvent(type=EventType.USER_MESSAGE, content={"text": user_input})
            )
            
            if user_input.lower() in ["exit", "quit"]:
                console.print("[bold]Exiting...[/bold]")
                logger_for_agent_logs.info("Exiting...")
                break

            logger_for_agent_logs.info("\nAgent is thinking...")
            try:
                # Run the agent
                result = await agent.run_agent_async(user_input, resume=True)
                logger_for_agent_logs.info(f"Agent: {result}")
                
                # Log tool usage statistics
                if not args.minimize_stdout_logs:
                    tool_usage = {}
                    for tool in agent.tool_manager.tools:
                        if hasattr(tool, 'server_name') and tool.server_name == 'context7':
                            tool_usage['Context7'] = tool_usage.get('Context7', 0) + 1
                        elif tool.name == 'claude_code':
                            tool_usage['Claude Code'] = tool_usage.get('Claude Code', 0) + 1
                    
                    if tool_usage:
                        usage_text = ", ".join([f"{k}: {v}" for k, v in tool_usage.items()])
                        console.print(f"[dim]Tool usage this turn: {usage_text}[/dim]")
                
                # Log Claude Code session info if used
                if not args.no_claude_code:
                    for tool in agent.tool_manager.tools:
                        if tool.name == "claude_code" and hasattr(tool, "session_manager"):
                            active_sessions = len(tool.session_manager.sessions)
                            if active_sessions > 0:
                                logger_for_agent_logs.info(
                                    f"Claude Code active sessions: {active_sessions}"
                                )
                
            except (KeyboardInterrupt, asyncio.CancelledError):
                agent.cancel()
                logger_for_agent_logs.info("Agent cancelled")
            except Exception as e:
                logger_for_agent_logs.error(f"Error: {str(e)}")
                logger_for_agent_logs.debug("Full error:", exc_info=True)

            logger_for_agent_logs.info("\n" + "-" * 40 + "\n")

    except KeyboardInterrupt:
        console.print("\n[bold]Session interrupted. Exiting...[/bold]")
    finally:
        # Cleanup tasks
        message_task.cancel()
        
        # Cleanup MCP registry
        if mcp_registry:
            try:
                await mcp_registry.shutdown()
                console.print("[green]✅ MCP registry cleanup complete[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️  MCP cleanup warning: {str(e)}[/yellow]")

    console.print("[bold]Goodbye![/bold]")


if __name__ == "__main__":
    asyncio.run(async_main())
