"""MCP IDE tool for getting language diagnostics from VS Code."""

from typing import Annotated, Optional
from pydantic import Field
from src.tools.base import BaseTool


DESCRIPTION = """Get language diagnostics from VS Code"""

class GetDiagnosticsTool(BaseTool):
    """Tool for getting language diagnostics from VS Code."""
    
    name = "mcp__ide__getDiagnostics"
    description = DESCRIPTION

    def run_impl(
        self,
        uri: Annotated[Optional[str], Field(description="Optional file URI to get diagnostics for. If not provided, gets diagnostics for all files.")],
    ) -> str:
        return ""