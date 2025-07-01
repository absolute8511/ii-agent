"""File writing tool for creating and overwriting files."""

from pathlib import Path
from typing import Annotated, Optional
from pydantic import Field
from src.tools.base import BaseTool
from src.utils.workspace_manager import WorkspaceManager


def is_path_in_directory(directory: Path, path: Path) -> bool:
    """Check if path is within directory."""
    directory = directory.resolve()
    path = path.resolve()
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


class FileWriteTool(BaseTool):
    """Tool for writing content to files."""
    
    name = "Write"
    description = """\
Writes a file to the local filesystem.

Usage:
- This tool will overwrite the existing file if there is one at the provided path.
- If this is an existing file, you MUST use the Read tool first to read the file's contents. This tool will fail if you did not read the file first.
- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
- NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
- Only use emojis if the user explicitly requests it. Avoid writing emojis to files unless asked."""

    def __init__(self, workspace_manager: Optional[WorkspaceManager] = None):
        super().__init__()
        self.workspace_manager = workspace_manager

    def run_impl(
        self,
        file_path: Annotated[str, Field(description="The absolute path to the file to write (must be absolute, not relative)")],
        content: Annotated[str, Field(description="The content to write to the file")],
    ) -> str:
        """Write content to a file."""
        try:
            path = Path(file_path)
            
            # Check if workspace manager is available and validate path
            if self.workspace_manager:
                # Convert to workspace path if needed
                workspace_path = self.workspace_manager.workspace_path(path)
                if not is_path_in_directory(self.workspace_manager.root, workspace_path):
                    container_root = self.workspace_manager.container_path(self.workspace_manager.root)
                    return f"Error: Path {file_path} is outside the workspace root directory: {container_root}. You can only access files within the workspace root directory."
                path = workspace_path
            
            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if it's trying to write to a directory
            if path.exists() and path.is_dir():
                return f"Error: {file_path} is a directory, not a file. Cannot write to a directory."
            
            # Write the content to the file
            path.write_text(content, encoding='utf-8')
            
            # Calculate file size and line count
            file_size = path.stat().st_size
            line_count = len(content.splitlines())
            
            return f"File written successfully to {file_path}\n" \
                   f"- Size: {file_size} bytes\n" \
                   f"- Lines: {line_count}"
            
        except PermissionError:
            return f"Error: Permission denied writing to {file_path}"
        except OSError as e:
            return f"Error: Cannot write to {file_path}: {str(e)}"
        except Exception as e:
            return f"Error writing to {file_path}: {str(e)}"