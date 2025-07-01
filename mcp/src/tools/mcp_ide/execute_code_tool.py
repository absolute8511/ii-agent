"""MCP IDE tool for executing Python code in Jupyter kernel."""

from typing import Annotated
from pydantic import Field
from src.tools.base import BaseTool


DESCRIPTION = """Execute python code in the Jupyter kernel for the current notebook file.
    
    All code will be executed in the current Jupyter kernel.
    
    Avoid declaring variables or modifying the state of the kernel unless the user
    explicitly asks for it.
    
    Any code executed will persist across calls to this tool, unless the kernel
    has been restarted."""

class ExecuteCodeTool(BaseTool):
    """Tool for executing Python code in Jupyter kernel."""
    
    name = "mcp__ide__executeCode"
    description = DESCRIPTION

    def run_impl(
        self,
        code: Annotated[str, Field(description="The code to be executed on the kernel.")],
    ) -> str:
        return ""