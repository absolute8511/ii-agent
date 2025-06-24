from argparse import ArgumentParser
from ii_agent.utils.constants import DEFAULT_MODEL
from ii_agent.utils.workspace_manager import WorkSpaceMode
from ii_agent.utils import WorkspaceManager


def parse_common_args(parser: ArgumentParser):
    parser.add_argument(
        "--workspace",
        type=str,
        default="test_workspace/",
        help="Path to the workspace",
    )
    parser.add_argument(
        "--logs-path",
        type=str,
        default="agent_logs.txt",
        help="Path to save logs",
    )
    parser.add_argument(
        "--needs-permission",
        "-p",
        help="Ask for permission before executing commands",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--use-container-workspace",
        help="Use docker container to run commands in, or e2b sandbox",
        default=WorkSpaceMode.LOCAL,
        type=WorkSpaceMode,
        choices=list(WorkSpaceMode),
    )
    parser.add_argument(
        "--minimize-stdout-logs",
        help="Minimize the amount of logs printed to stdout.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--project-id",
        type=str,
        default=None,
        help="Project ID to use for Anthropic",
    )
    parser.add_argument(
        "--region",
        type=str,
        default=None,
        help="Region to use for Anthropic",
    )
    parser.add_argument(
        "--memory-tool",
        type=str,
        default="compactify-memory",
        choices=["compactify-memory", "none", "simple"],
        help="Type of memory tool to use",
    )
    parser.add_argument(
        "--llm-client",
        type=str,
        default="anthropic-direct",
        choices=["anthropic-direct", "openai-direct"],
        help="LLM client to use (anthropic-direct or openai-direct for LMStudio/local)",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default=DEFAULT_MODEL,
        help="Name of the LLM model to use (e.g., claude-3-opus-20240229 or local-model-identifier for LMStudio)",
    )
    parser.add_argument(
        "--azure-model",
        action="store_true",
        default=False,
        help="Use Azure OpenAI model",
    )
    parser.add_argument(
        "--no-cot-model",
        action="store_false",
        dest="cot_model",
        default=True,
        help="Disable chain-of-thought model (enabled by default)",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="Prompt to use for the LLM",
    )
    parser.add_argument(
        "--enable-reviewer",
        action="store_true",
        default=False,
        help="Enable reviewer agent to analyze and improve outputs",
    )
    return parser


def create_workspace_manager_for_connection(args):
    """Create a WorkspaceManager instance based on command line arguments."""
    return WorkspaceManager(
        parent_dir=args.workspace,
        session_id="default_session"
    )
