import asyncio

from fastmcp import FastMCP
from argparse import ArgumentParser
from pathlib import Path
from typing import List
from src.tools.base import BaseTool

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
    
    tools = [
    ]
    
    asyncio.run(setup(tools=tools))
    main_mcp.run(transport="http", host="0.0.0.0", port=args.port)