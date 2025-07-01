"""File writing tool for creating and overwriting files."""

from pathlib import Path
from typing import Annotated, Optional
from pydantic import Field
from src.tools.base import BaseTool
from src.utils.workspace_manager import WorkspaceManager


DESCRIPTION = """Writes a file to the local filesystem.

Usage:
- This tool will overwrite the existing file if there is one at the provided path.
- If this is an existing file, you MUST use the Read tool first to read the file's contents. This tool will fail if you did not read the file first.
- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
- NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
- Only use emojis if the user explicitly requests it. Avoid writing emojis to files unless asked."""


class FileWriteTool(BaseTool):
    """Tool for writing content to files."""
    
    name = "Write"
    description = DESCRIPTION

    def __init__(self, workspace_manager: Optional[WorkspaceManager] = None):
        super().__init__()
        self.workspace_manager = workspace_manager

    def run_impl(
        self,
        file_path: Annotated[str, Field(description="The absolute path to the file to write (must be absolute, not relative)")],
        content: Annotated[str, Field(description="The content to write to the file")],
    ) -> str:
        return ""