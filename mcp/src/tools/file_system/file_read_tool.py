"""File reading tool for reading file contents."""

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


class FileReadTool(BaseTool):
    """Tool for reading file contents with optional line range specification."""
    
    name = "Read"
    description = """\
Reads a file from the local filesystem. You can access any file directly by using this tool.
Assume this tool is able to read all files on the machine. If the User provides a path to a file assume that path is valid. It is okay to read a file that does not exist; an error will be returned.

Usage:
- The file_path parameter must be an absolute path, not a relative path
- By default, it reads up to 2000 lines starting from the beginning of the file
- You can optionally specify a line offset and limit (especially handy for long files), but it's recommended to read the whole file by not providing these parameters
- Any lines longer than 2000 characters will be truncated
- Results are returned using cat -n format, with line numbers starting at 1
- This tool allows Claude Code to read images (eg PNG, JPG, etc). When reading an image file the contents are presented visually as Claude Code is a multimodal LLM.
- For Jupyter notebooks (.ipynb files), use the NotebookRead instead
- You have the capability to call multiple tools in a single response. It is always better to speculatively read multiple files as a batch that are potentially useful. 
- You will regularly be asked to read screenshots. If the user provides a path to a screenshot ALWAYS use this tool to view the file at the path. This tool will work with all temporary file paths like /var/folders/123/abc/T/TemporaryItems/NSIRD_screencaptureui_ZfB1tD/Screenshot.png
- If you read a file that exists but has empty contents you will receive a system reminder warning in place of file contents."""

    def __init__(self, workspace_manager: Optional[WorkspaceManager] = None):
        super().__init__()
        self.workspace_manager = workspace_manager

    def run_impl(
        self,
        file_path: Annotated[str, Field(description="The absolute path to the file to read")],
        limit: Annotated[Optional[int], Field(description="The number of lines to read. Only provide if the file is too large to read at once.")] = None,
        offset: Annotated[Optional[int], Field(description="The line number to start reading from. Only provide if the file is too large to read at once")] = None,
    ) -> str:
        """Read a file and return its contents with line numbers."""
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
            
            # Check if file exists
            if not path.exists():
                return f"Error: File {file_path} does not exist."
            
            # Check if it's a directory
            if path.is_dir():
                return f"Error: {file_path} is a directory, not a file. Use the LS tool to list directory contents."
            
            # Read file contents
            try:
                content = path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # Try reading as binary for non-text files
                try:
                    content = path.read_bytes().decode('utf-8', errors='replace')
                except Exception:
                    return f"Error: Cannot read {file_path} - file appears to be binary or corrupted."
            
            # Handle empty file
            if not content:
                return f"File {file_path} is empty."
            
            # Split into lines
            lines = content.splitlines()
            total_lines = len(lines)
            
            # Apply offset and limit
            start_line = (offset - 1) if offset else 0
            end_line = min(start_line + limit, total_lines) if limit else total_lines
            
            # Validate offset
            if offset and (offset < 1 or offset > total_lines):
                return f"Error: Invalid offset {offset}. File has {total_lines} lines."
            
            # Get the lines to display
            selected_lines = lines[start_line:end_line]
            
            # Format output with line numbers (starting from 1)
            formatted_lines = []
            for i, line in enumerate(selected_lines):
                line_num = start_line + i + 1
                # Truncate long lines
                if len(line) > 2000:
                    line = line[:2000] + "... (line truncated)"
                formatted_lines.append(f"{line_num:6}\t{line}")
            
            # Create output
            result = "\n".join(formatted_lines)
            
            # Add file info
            if offset or limit:
                result += f"\n\nShowing lines {start_line + 1}-{end_line} of {total_lines} total lines in {file_path}"
            else:
                result += f"\n\nTotal lines in file: {total_lines}"
            
            return result
            
        except PermissionError:
            return f"Error: Permission denied reading {file_path}"
        except Exception as e:
            return f"Error reading {file_path}: {str(e)}"