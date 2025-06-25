#!/usr/bin/env python3
"""
CLI interface for testing Claude Code integration with ii-agent.

This script provides a command-line interface specifically configured
for testing the Claude Code tool integration.
"""

import os
import argparse
import logging
import asyncio
from dotenv import load_dotenv

from ii_agent.llm.message_history import MessageHistory

load_dotenv()

from ii_agent.core.event import RealtimeEvent, EventType
from ii_agent.utils.constants import TOKEN_BUDGET
from utils import parse_common_args, create_workspace_manager_for_connection
from rich.console import Console
from rich.panel import Panel

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


async def async_main():
    """Async main entry point"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="CLI for testing Claude Code integration with ii-agent"
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
        "--claude-code-session-ttl",
        type=int,
        default=60,
        help="Session TTL in minutes for Claude Code",
    )
    parser.add_argument(
        "--claude-code-max-sessions",
        type=int,
        default=10,
        help="Maximum concurrent Claude Code sessions",
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
    workspace_path = workspace_manager.root
    
    # Create a new session and get its workspace directory
    Sessions.create_session(
        session_uuid=session_id, workspace_path=workspace_manager.root
    )
    logger_for_agent_logs.info(
        f"Created new session {session_id} with workspace at {workspace_manager.root}"
    )

    # Print welcome message
    if not args.minimize_stdout_logs:
        claude_code_status = "Disabled" if args.no_claude_code else "Enabled"
        console.print(
            Panel(
                "[bold]Claude Code Integration Test CLI[/bold]\n\n"
                + f"Session ID: {session_id}\n"
                + f"Workspace: {workspace_path}\n"
                + f"Claude Code: {claude_code_status}\n"
                + f"Claude Model: {args.claude_code_model}\n\n"
                + "Type your instructions to test Claude Code integration.\n"
                + "Try commands like: 'Use claude_code to create a FastAPI server'\n"
                + "Press Ctrl+C to exit. Type 'exit' or 'quit' to end the session.",
                title="[bold blue]Claude Code Test CLI[/bold blue]",
                border_style="blue",
                padding=(1, 2),
            )
        )
    else:
        logger_for_agent_logs.info(
            f"Claude Code CLI started with session {session_id}. Waiting for user input."
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

    # Workspace manager already initialized earlier in the function

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
    
    # Configure tool arguments with Claude Code
    tool_args = {
        "deep_research": False,
        "pdf": True,
        "media_generation": False,
        "audio_generation": False,
        "browser": True,
        "memory_tool": args.memory_tool,
        # Claude Code specific configuration
        "claude_code": not args.no_claude_code,
        "claude_code_api_key": args.claude_code_api_key,
        "claude_code_model": args.claude_code_model,
    }
    
    tools = get_system_tools(
        client=client,
        workspace_manager=workspace_manager,
        message_queue=queue,
        tool_args=tool_args,
    )
    
    # Log available tools
    tool_names = [tool.name for tool in tools]
    logger_for_agent_logs.info(f"Available tools: {', '.join(tool_names)}")
    
    # Create system prompt that mentions Claude Code
    claude_code_prompt = """

When the user asks for complex coding tasks like creating applications, refactoring code, 
or implementing features, consider using the 'claude_code' tool. This tool is particularly 
good at:
- Creating multi-file applications
- Refactoring existing code
- Adding comprehensive tests
- Implementing complex features
- Code reviews and improvements

When calling claude_code, you can optionally provide a 'context' parameter to give specific background.
You should also provide the current workspace folder path in your instruction to claude_code to make it easier to find the files, and also ask claude_code to use workspace folder.
If you don't provide context, Claude Code will automatically generate it from the conversation history.

Example with explicit context:
claude_code(
    task="Add authentication to the server. Let's use the /path/to/workspace/ directory for your work.",
    context="Previously created a FastAPI server in main.py with basic routes. The server has endpoints for /users and /items.",
    context_files=["main.py"]
)

Example without context (auto-generated):
claude_code(
    task="Add authentication to the server",
    context_files=["main.py"]
)"""
    
    # system_prompt = get_system_prompt(WorkSpaceMode.LOCAL) + claude_code_prompt
    system_prompt = get_system_prompt(WorkSpaceMode.LOCAL)
    
    agent = FunctionCallAgent(
        system_prompt=system_prompt,
        client=client,
        workspace_manager=workspace_manager,
        tools=tools,
        message_queue=queue,
        logger_for_agent_logs=logger_for_agent_logs,
        init_history=init_history,
        max_output_tokens_per_turn=MAX_OUTPUT_TOKENS_PER_TURN,
        max_turns=MAX_TURNS,
        session_id=session_id,
    )

    # Create background task for message processing
    message_task = agent.start_message_processing()

    loop = asyncio.get_running_loop()
    prompt = """
Build a simplified node-based media generation web application inspired by ComfyUI

The app should allow users to visually connect nodes to create custom workflows

There are three node types:
- Text Node: Contains a text input box
- Image Node: Accepts uploaded image or displays image generated from other nodes
- Video Node: Accepts uploaded video or displays video generated from other nodes

Design the system to support these valid node connections:
Consider graph execute from left to right 
- Text(s) -> Text: Combine multiple text nodes into one summarization or ideation output
- Text -> Image: Generate an image from a text prompt
- Text -> Video: Generate a video from a text prompt
- Text + Image -> Image: Apply text-based edits to an image (e.g., "make it look like night")
- Text + Image -> Video: Generate video from a text prompt and input image as the starting frame
- Image -> Video: Generate a video from an image as the starting frame
- Text + Image -> Text: Ask questions about the image or extract information from it using a prompt
- Image -> Text: Describe or caption the image automatically

Example graph:
// Example 1: Text-to-Text
{
"nodes": [
    { "id": "node_1", "type": "text", "data": { "text": "Describe the benefits of exercise." } },
    { "id": "node_2", "type": "text", "data": {} }
  ],
"edges": [
    { "id": "edge_1", "source": "node_1", "target": "node_2" }
  ]
}
// Output:
{
    "output_nodes": [
        { "id": "node_2", "type": "text", "data": {"text": "Exercise offers numerous benefits including improved cardiovascular health, increased strength and flexibility, enhanced mental well-being, weight management, and a reduced risk of chronic diseases."} }
    ]
}

{
  "nodes": [
    { "id": "node_1", "type": "text", "data": { "text": "A dog" } },
    { "id": "node_2", "type": "text", "data": { "text": "A cat" } },
    { "id": "node_3", "type": "text", "data": {} }
  ],
  "edges": [
    { "id": "edge_1", "source": "node_1", "target": "node_3" },
    { "id": "edge_2", "source": "node_2", "target": "node_3" }
  ]
}
// Output:
{
    "output_nodes": [
        { "id": "node_3", "type": "text", "data": {"text": "A dog and a cat"} }
    ]
}

// Example 2: Text-to-Image (Prompt to Image)
{
  "nodes": [
    { "id": "node_1", "type": "text", "data": { "text": "A futuristic city at night" } },
    { "id": "node_2", "type": "image", "data": {} }
  ],
  "edges": [
    { "id": "edge_1", "source": "node_1", "target": "node_2" }
  ]
}
// Output:
{
    "output_nodes": [
        { "id": "node_2", "type": "image", "data": {"url": "<image_url>"} }
    ]
}

// Example 3: Text + Image → Image (Edit Image with Prompt)
{
  "nodes": [
    { "id": "node_1", "type": "text", "data": { "text": "Make it look like winter" } },
    { "id": "node_2", "type": "image", "data": { "url": "https://example.com/original.jpg" } },
    { "id": "node_3", "type": "image", "data": {} }
  ],
  "edges": [
    { "id": "edge_1", "source": "node_1", "target": "node_3" },
    { "id": "edge_2", "source": "node_2", "target": "node_3" }
  ]
}
// Output:
{
    "output_nodes": [
        { "id": "node_3", "type": "image", "data": {"url": "<image_url>"} }
    ]
}

// Example 4: Text + Image → Video (Generate Video from Prompt and Image)
{
  "nodes": [
    { "id": "node_1", "type": "text", "data": { "text": "Animate this image to show sunrise" } },
    { "id": "node_2", "type": "image", "data": { "url": "https://example.com/mountain.jpg" } },
    { "id": "node_3", "type": "video", "data": {} }
  ],
  "edges": [
    { "id": "edge_1", "source": "node_1", "target": "node_3" },
    { "id": "edge_2", "source": "node_2", "target": "node_3" }
  ]
}
// Output:
{
    "output_nodes": [
        { "id": "node_3", "type": "video", "data": {"url": "<video_url>"} }
    ]
}

// Example 5: Multi-step Workflow (Text → Image → Text)
{
  "nodes": [
    { "id": "node_1", "type": "text", "data": { "text": "A cat playing chess" } },
    { "id": "node_2", "type": "image", "data": {} },
    { "id": "node_3", "type": "text", "data": {} }
  ],
  "edges": [
    { "id": "edge_1", "source": "node_1", "target": "node_2" },
    { "id": "edge_2", "source": "node_2", "target": "node_3" }
  ]
}
// Output:
{
    "output_nodes": [
        { "id": "node_2", "type": "image", "data": {"url": "<image_url>"} },
        { "id": "node_3", "type": "text", "data": {"text": "A cat is sitting at a chessboard, appearing to contemplate its next move in a game of chess."} }
    ]
}

// Example 6: Complex Graph (Text + Image → Image, then → Video)
{
  "nodes": [
    { "id": "node_1", "type": "text", "data": { "text": "Make it look like night" } },
    { "id": "node_2", "type": "image", "data": { "url": "https://example.com/park.jpg" } },
    { "id": "node_3", "type": "image", "data": {} },
    { "id": "node_4", "type": "video", "data": {} }
  ],
  "edges": [
    { "id": "edge_1", "source": "node_1", "target": "node_3" },
    { "id": "edge_2", "source": "node_2", "target": "node_3" },
    { "id": "edge_3", "source": "node_3", "target": "node_4" }
  ]
}
// Output:
{
    "output_nodes": [
        { "id": "node_3", "type": "image", "data": {"url": "<image_url>"} },
        { "id": "node_4", "type": "video", "data": {"url": "<video_url>"} }
    ]
}

Services
- Use [https://fal.ai](https://fal.ai) for:
  - `text → image`
    * model: `fal-ai/imagen4/preview/fast`
    * detail usage: https://fal.ai/models/fal-ai/imagen4/preview/fast/api?platform=python
  - `text → video`
    * model: `fal-ai/bytedance/seedance/v1/lite/text-to-video`
    * detail usage: https://fal.ai/models/fal-ai/bytedance/seedance/v1/lite/text-to-video/api?platform=python
  - `text + image → image`
    * model: `fal-ai/flux-pro/kontext`
    * detail usage: https://fal.ai/models/fal-ai/flux-pro/kontext/api?platform=python
  - `text + image → video`
    * model: `fal-ai/bytedance/seedance/v1/lite/image-to-video`
    * detail usage: https://fal.ai/models/fal-ai/bytedance/seedance/v1/lite/image-to-video/api?platform=python
  - `image → video`
    * model: `fal-ai/bytedance/seedance/v1/lite/image-to-video`
    * detail usage: https://fal.ai/models/fal-ai/bytedance/seedance/v1/lite/image-to-video/api?platform=python
  
  Visit the detail page for usage and parameters

- Use **OpenAI** API (GPT-4o by default) for:
  - `text → text` (combine prompts)
  - `image → text` (caption or QA)
  - `text + image → text` (QA with image)

Backend
- FastAPI
- `/run-graph`: Accept a JSON graph definition (nodes + edges), return output nodes
  * The core challenge here is processing the graph in the correct order
  * For a graph like Example 5 (Text → Image → Text), node_2 must wait for node_1's implicit "execution" (which is just providing its data), and node_3 must wait for node_2's explicit execution. You'll need to implement a topological sort of the graph to determine the correct, dependency-aware execution order
  * For simple, when the workflow is done, the all the output nodes will be returned and results are displayed in the UI
- `/validate-graph`: Validate the graph structure
  * edge level: Verifies all connections (from a right-side handle to a left-side handle) match allowed type patterns and that target nodes receive the correct number of inputs.
  * node level: Confirms that any node with zero connections to its input handles (the "left side") is properly initialized with user-provided data (text or an uploaded file).
  * Graph level: Ensures the entire workflow is a one-way flow by checking for circular dependencies (loops) that would prevent execution.
- Don't need polling for status of the job, just return the result when the job is done
- No need for authentication
- Write test cases for complex workflows and cover as many scenarios as possible

Frontend
- React Flow
- Canvas: create nodes, connect nodes and create your own personalized workflows
- Has a page for configuration API keys and model names for fal.ai and OpenAI
- Favor a modern, minimalistic aesthetic with a default dark mode interface
  * Choose a color scheme from white -> grey -> dark
  * Apply a consistent color across components, transitioning smoothly from white to grey to dark tones
- The result of each node is displayed inside the node
- Create an example workflow in the UI for demonstration

Service keys for real testing
openai: 
fal.ai: 
"""
#    prompt = "build a website of a snake game"
 #   prompt = "hello"
    # Example prompts for Claude Code
    if not args.minimize_stdout_logs and not args.no_claude_code:
        console.print("\n[bold cyan]Example Claude Code commands:[/bold cyan]")
        console.print("• Use claude_code to create a FastAPI server with user authentication")
        console.print("• Use claude_code to refactor messy_code.py following best practices")
        console.print("• Use claude_code to add comprehensive tests for the TodoList class")
        console.print("• Use claude_code to review the security of our authentication code")
        console.print()
    
    # Main interaction loop
    try:
        while True:
            # Use async input
            if prompt is None:
                user_input = await loop.run_in_executor(
                    None, lambda: input("User input: ")
                )
            else:
                user_input = prompt
                # Only use prompt once
                prompt = None

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
                
                # Log Claude Code session info if used
                if not args.no_claude_code:
                    # Check if Claude Code was used in this turn
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
        loop.stop()
    finally:
        # Cleanup tasks
        message_task.cancel()

    console.print("[bold]Goodbye![/bold]")


if __name__ == "__main__":
    asyncio.run(async_main())
