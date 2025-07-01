"""Content search tool using regular expressions."""

import re
from pathlib import Path
from typing import Annotated, Optional
from pydantic import Field
from src.tools.base import BaseTool
from src.utils.workspace_manager import WorkspaceManager
from ..constants import MAX_SEARCH_FILES, BINARY_EXTENSIONS, MAX_MATCHES_PER_FILE, MAX_TOTAL_MATCHES


DESCRIPTION = """
- Fast content search tool that works with any codebase size
- Searches file contents using regular expressions
- Supports full regex syntax (eg. "log.*Error", "function\\s+\\w+", etc.)
- Filter files by pattern with the include parameter (eg. "*.js", "*.{ts,tsx}")
- Returns file paths with at least one match sorted by modification time
- Use this tool when you need to find files containing specific patterns
- If you need to identify/count the number of matches within files, use the Bash tool with `rg` (ripgrep) directly. Do NOT use `grep`.
- When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead
"""


class GrepTool(BaseTool):
    """Tool for searching file contents using regular expressions."""
    
    name = "Grep"
    description = DESCRIPTION

    def __init__(self, workspace_manager: Optional[WorkspaceManager] = None):
        super().__init__()
        self.workspace_manager = workspace_manager

    def run_impl(
        self,
        pattern: Annotated[str, Field(description="The regular expression pattern to search for in file contents")],
        path: Annotated[Optional[str], Field(description="The directory to search in. Defaults to the current working directory.")],
        include: Annotated[Optional[str], Field(description="File pattern to include in the search (e.g. \"*.js\", \"*.{ts,tsx}\")")],
    ) -> str:
        return ""