"""File editing tool for making targeted edits to files."""

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


class FileEditTool(BaseTool):
    """Tool for making targeted string replacements in files."""
    
    name = "Edit"
    description = """\
Performs exact string replacements in files. 

Usage:
- You must use your `Read` tool at least once in the conversation before editing. This tool will error if you attempt an edit without reading the file. 
- When editing text from Read tool output, ensure you preserve the exact indentation (tabs/spaces) as it appears AFTER the line number prefix. The line number prefix format is: spaces + line number + tab. Everything after that tab is the actual file content to match. Never include any part of the line number prefix in the old_string or new_string.
- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
- Only use emojis if the user explicitly requests it. Avoid adding emojis to files unless asked.
- The edit will FAIL if `old_string` is not unique in the file. Either provide a larger string with more surrounding context to make it unique or use `replace_all` to change every instance of `old_string`. 
- Use `replace_all` for replacing and renaming strings across the file. This parameter is useful if you want to rename a variable for instance."""

    def __init__(self, workspace_manager: Optional[WorkspaceManager] = None):
        super().__init__()
        self.workspace_manager = workspace_manager

    def run_impl(
        self,
        file_path: Annotated[str, Field(description="The absolute path to the file to modify")],
        old_string: Annotated[str, Field(description="The text to replace")],
        new_string: Annotated[str, Field(description="The text to replace it with (must be different from old_string)")],
        replace_all: Annotated[bool, Field(description="Replace all occurences of old_string (default false)")] = False,
    ) -> str:
        """Perform a string replacement in a file."""
        try:
            # Validate that old_string and new_string are different
            if old_string == new_string:
                return "Error: old_string and new_string cannot be the same"
            
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
                return f"Error: {file_path} is a directory, not a file."
            
            # Read the current content
            try:
                content = path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                return f"Error: Cannot edit {file_path} - file appears to be binary."
            
            # Check if old_string exists in the file
            if old_string not in content:
                return f"Error: The string to replace was not found in {file_path}.\n\nString to find:\n{old_string}"
            
            # Count occurrences
            occurrences = content.count(old_string)
            
            if occurrences == 0:
                return f"Error: The string to replace was not found in {file_path}."
            elif occurrences > 1 and not replace_all:
                # Find line numbers where the string appears
                lines = content.split('\n')
                line_numbers = []
                for i, line in enumerate(lines, 1):
                    if old_string in line:
                        line_numbers.append(i)
                
                return f"Error: Multiple occurrences of the string found in {file_path} at lines: {line_numbers}. " \
                       f"Use replace_all=True to replace all occurrences, or provide more context to make the string unique."
            
            # Perform the replacement
            if replace_all:
                new_content = content.replace(old_string, new_string)
                result_msg = f"Replaced {occurrences} occurrence(s) of the string in {file_path}"
            else:
                new_content = content.replace(old_string, new_string, 1)
                result_msg = f"Replaced 1 occurrence of the string in {file_path}"
            
            # Write the modified content back to the file
            path.write_text(new_content, encoding='utf-8')
            
            # Show a snippet of the change
            lines = new_content.split('\n')
            # Find the line containing the replacement
            changed_line_num = None
            for i, line in enumerate(lines):
                if new_string in line:
                    changed_line_num = i + 1
                    break
            
            if changed_line_num:
                # Show context around the change
                start_line = max(0, changed_line_num - 4)
                end_line = min(len(lines), changed_line_num + 3)
                snippet_lines = []
                for i in range(start_line, end_line):
                    snippet_lines.append(f"{i+1:6}\t{lines[i]}")
                
                snippet = "\n".join(snippet_lines)
                result_msg += f"\n\nHere's the edited section:\n{snippet}"
            
            return result_msg
            
        except PermissionError:
            return f"Error: Permission denied modifying {file_path}"
        except Exception as e:
            return f"Error editing {file_path}: {str(e)}"