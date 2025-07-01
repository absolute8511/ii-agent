"""Directory listing tool for exploring file system structure."""

import fnmatch
from pathlib import Path
from typing import Annotated, Optional, List
from pydantic import Field
from src.tools.base import BaseTool
from src.utils.workspace_manager import WorkspaceManager


from ..constants import MAX_FILES_LS, LS_TRUNCATED_MESSAGE

MAX_FILES = MAX_FILES_LS
TRUNCATED_MESSAGE = LS_TRUNCATED_MESSAGE


def is_path_in_directory(directory: Path, path: Path) -> bool:
    """Check if path is within directory."""
    directory = directory.resolve()
    path = path.resolve()
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


class LSTool(BaseTool):
    """Tool for listing files and directories."""
    
    name = "LS"
    description = """\
Lists files and directories in a given path. The path parameter must be an absolute path, not a relative path. You can optionally provide an array of glob patterns to ignore with the ignore parameter. You should generally prefer the Glob and Grep tools, if you know which directories to search."""

    def __init__(self, workspace_manager: Optional[WorkspaceManager] = None):
        super().__init__()
        self.workspace_manager = workspace_manager

    def run_impl(
        self,
        path: Annotated[str, Field(description="The absolute path to the directory to list (must be absolute, not relative)")],
        ignore: Annotated[Optional[List[str]], Field(description="List of glob patterns to ignore")] = None,
    ) -> str:
        """List files and directories in the given path."""
        try:
            target_path = Path(path)
            
            # Check if workspace manager is available and validate path
            if self.workspace_manager:
                # Convert to workspace path if needed
                workspace_path = self.workspace_manager.workspace_path(target_path)
                if not is_path_in_directory(self.workspace_manager.root, workspace_path):
                    container_root = self.workspace_manager.container_path(self.workspace_manager.root)
                    return f"Error: Path {path} is outside the workspace root directory: {container_root}. You can only access files within the workspace root directory."
                target_path = workspace_path
            
            # Check if path exists
            if not target_path.exists():
                return f"Error: Path {path} does not exist."
            
            # Check if it's a file (should be a directory)
            if target_path.is_file():
                return f"Error: {path} is a file, not a directory. Use the Read tool to view file contents."
            
            # Get all items in directory
            try:
                all_items = list(target_path.iterdir())
            except PermissionError:
                return f"Error: Permission denied accessing {path}"
            
            # Filter out ignored patterns
            if ignore:
                filtered_items = []
                for item in all_items:
                    should_ignore = False
                    for pattern in ignore:
                        if fnmatch.fnmatch(item.name, pattern) or fnmatch.fnmatch(str(item), pattern):
                            should_ignore = True
                            break
                    if not should_ignore:
                        filtered_items.append(item)
                all_items = filtered_items
            
            # Sort items: directories first, then files, both alphabetically
            directories = sorted([item for item in all_items if item.is_dir()], key=lambda x: x.name.lower())
            files = sorted([item for item in all_items if item.is_file()], key=lambda x: x.name.lower())
            
            # Combine and limit
            items = directories + files
            total_items = len(items)
            
            # Check if we need to truncate
            truncated = total_items > MAX_FILES
            if truncated:
                items = items[:MAX_FILES]
            
            # Build the output
            result_lines = []
            if truncated:
                result_lines.append(TRUNCATED_MESSAGE)
            
            # Format the listing
            result_lines.append(f"Contents of {path}:")
            result_lines.append("")
            
            if not items:
                result_lines.append("(empty directory)")
            else:
                # Group directories and files for display
                if directories:
                    result_lines.append("Directories:")
                    for directory in directories[:MAX_FILES]:
                        if directory in items:  # Make sure it's not truncated out
                            result_lines.append(f"  {directory.name}/")
                
                if files and directories:
                    result_lines.append("")
                
                if files:
                    result_lines.append("Files:")
                    file_count = 0
                    for file in files:
                        if file in items and file_count < MAX_FILES:  # Make sure it's not truncated out
                            # Get file size
                            try:
                                size = file.stat().st_size
                                if size < 1024:
                                    size_str = f"{size}B"
                                elif size < 1024 * 1024:
                                    size_str = f"{size // 1024}KB"
                                else:
                                    size_str = f"{size // (1024 * 1024)}MB"
                            except (OSError, PermissionError):
                                size_str = "?"
                            
                            result_lines.append(f"  {file.name} ({size_str})")
                            file_count += 1
            
            # Add summary
            result_lines.append("")
            if truncated:
                result_lines.append(f"Showing {len(items)} of {total_items} items")
            else:
                result_lines.append(f"Total: {total_items} items ({len(directories)} directories, {len(files)} files)")
            
            return "\n".join(result_lines)
            
        except Exception as e:
            return f"Error listing {path}: {str(e)}"
