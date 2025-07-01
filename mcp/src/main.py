import asyncio

from fastmcp import FastMCP
from argparse import ArgumentParser
from pathlib import Path
from typing import List
from src.tools.base import BaseTool
from src.tools.file_system import (
    StrReplaceEditorTool,
    GlobTool,
    GrepTool,
)
from src.tools.shell.shell_tool import (
    ShellExecTool,
    ShellViewTool,
    ShellWaitTool,
    ShellKillProcessTool,
    ShellWriteToProcessTool,
)
from src.utils.workspace_manager import WorkspaceManager


main_mcp = FastMCP(name="ii-mcp")

async def setup(tools: List[BaseTool]):
    for tool in tools:
        main_mcp.tool(
            tool.run_impl,
            name=tool.name,
            description=tool.description,
        )

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--workspace_dir", type=str)
    parser.add_argument("--port", type=int, default=6060)
    args = parser.parse_args()
    if not args.workspace_dir:
        raise ValueError("Workspace directory is required")
    
    workspace_manager = WorkspaceManager(root=Path(args.workspace_dir))
    tools = [
        StrReplaceEditorTool(workspace_manager=workspace_manager),
        ShellExecTool(workspace_manager=workspace_manager),
        ShellViewTool(workspace_manager=workspace_manager),
        ShellWaitTool(workspace_manager=workspace_manager),
        ShellKillProcessTool(workspace_manager=workspace_manager),
        ShellWriteToProcessTool(workspace_manager=workspace_manager),
    ]
    asyncio.run(setup(tools=tools))
    main_mcp.run(transport="http", host="0.0.0.0", port=args.port)