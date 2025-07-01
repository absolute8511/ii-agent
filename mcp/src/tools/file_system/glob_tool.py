"""File pattern matching tool using glob patterns."""

import glob
from pathlib import Path
from typing import Annotated, Optional
from pydantic import Field
from src.tools.base import BaseTool
from src.utils.workspace_manager import WorkspaceManager


DESCRIPTION = """\
- Fast file pattern matching tool that works with any codebase size
- Supports glob patterns like "**/*.js" or "src/**/*.ts"
- Returns matching file paths sorted by modification time
- Use this tool when you need to find files by name patterns
- When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead"""


def is_path_in_directory(directory: Path, path: Path) -> bool:
    """Check if path is within directory."""
    directory = directory.resolve()
    path = path.resolve()
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


class GlobTool(BaseTool):
    """Tool for finding files using glob patterns."""
    
    name = "Glob"
    description = """\
- Fast file pattern matching tool that works with any codebase size
- Supports glob patterns like "**/*.js" or "src/**/*.ts"
- Returns matching file paths sorted by modification time
- Use this tool when you need to find files by name patterns
- When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead"""

    def __init__(self, workspace_manager: Optional[WorkspaceManager] = None):
        super().__init__()
        self.workspace_manager = workspace_manager

    def run_impl(
        self,
        pattern: Annotated[str, Field(description="The glob pattern to match files against")],
        path: Annotated[Optional[str], Field(description="The directory to search in. If not specified, the current working directory will be used. IMPORTANT: Omit this field to use the default directory. DO NOT enter \"undefined\" or \"null\" - simply omit it for the default behavior. Must be a valid directory path if provided.")] = None,
    ) -> str:
        """Find files matching the given glob pattern."""
        try:
            # Determine the search directory
            if path is None:
                search_dir = Path.cwd()
            else:
                search_dir = Path(path)
            
            # Check if workspace manager is available and validate path
            if self.workspace_manager:
                # Convert to workspace path if needed
                workspace_path = self.workspace_manager.workspace_path(search_dir)
                if not is_path_in_directory(self.workspace_manager.root, workspace_path):
                    container_root = self.workspace_manager.container_path(self.workspace_manager.root)
                    return f"Error: Path {path or 'current directory'} is outside the workspace root directory: {container_root}. You can only access files within the workspace root directory."
                search_dir = workspace_path
            
            # Check if search directory exists
            if not search_dir.exists():
                return f"Error: Directory {search_dir} does not exist."
            
            if not search_dir.is_dir():
                return f"Error: {search_dir} is not a directory."
            
            # Perform glob search
            # Use rglob for recursive patterns or glob for non-recursive
            if '**' in pattern:
                # Recursive search
                matches = list(search_dir.rglob(pattern))
            else:
                # Non-recursive search
                matches = list(search_dir.glob(pattern))
            
            if not matches:
                return f"No files found matching pattern '{pattern}' in {search_dir}"
            
            # Filter out directories unless specifically requested
            file_matches = [match for match in matches if match.is_file()]
            
            # Sort by modification time (most recent first)
            try:
                file_matches.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            except (OSError, PermissionError):
                # If we can't get modification times, sort by name
                file_matches.sort(key=lambda x: str(x))
            
            # Format the results
            result_lines = [f"Found {len(file_matches)} files matching '{pattern}' in {search_dir}:"]
            result_lines.append("")
            
            for match in file_matches[:100]:  # Limit to first 100 results
                # Get relative path from search directory for cleaner display
                try:
                    rel_path = match.relative_to(search_dir)
                    result_lines.append(str(rel_path))
                except ValueError:
                    # If relative path fails, use absolute path
                    result_lines.append(str(match))
            
            if len(file_matches) > 100:
                result_lines.append("")
                result_lines.append(f"... and {len(file_matches) - 100} more files (showing first 100)")
            
            return "\n".join(result_lines)
            
        except Exception as e:
            return f"Error performing glob search: {str(e)}"
