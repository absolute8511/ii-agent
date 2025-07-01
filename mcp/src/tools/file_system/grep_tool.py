"""Content search tool using regular expressions."""

import re
from pathlib import Path
from typing import Annotated, Optional
from pydantic import Field
from src.tools.base import BaseTool
from src.utils.workspace_manager import WorkspaceManager
from ..constants import MAX_SEARCH_FILES, BINARY_EXTENSIONS, MAX_MATCHES_PER_FILE, MAX_TOTAL_MATCHES


DESCRIPTION = """\
- Fast content search tool that works with any codebase size
- Searches file contents using regular expressions
- Supports full regex syntax (eg. "log.*Error", "function\\s+\\w+", etc.)
- Filter files by pattern with the include parameter (eg. "*.js", "*.{ts,tsx}")
- Returns file paths with at least one match sorted by modification time
- Use this tool when you need to find files containing specific patterns
- If you need to identify/count the number of matches within files, use the Bash tool with `rg` (ripgrep) directly. Do NOT use `grep`.
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


class GrepTool(BaseTool):
    """Tool for searching file contents using regular expressions."""
    
    name = "Grep"
    description = """\

- Fast content search tool that works with any codebase size
- Searches file contents using regular expressions
- Supports full regex syntax (eg. "log.*Error", "function\\s+\\w+", etc.)
- Filter files by pattern with the include parameter (eg. "*.js", "*.{ts,tsx}")
- Returns matching file paths sorted by modification time
- Use this tool when you need to find files containing specific patterns
- If you need to identify/count the number of matches within files, use the Bash tool with `rg` (ripgrep) directly. Do NOT use `grep`.
- When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead
"""

    def __init__(self, workspace_manager: Optional[WorkspaceManager] = None):
        super().__init__()
        self.workspace_manager = workspace_manager

    def run_impl(
        self,
        pattern: Annotated[str, Field(description="The regular expression pattern to search for in file contents")],
        path: Annotated[Optional[str], Field(description="The directory to search in. Defaults to the current working directory.")] = None,
        include: Annotated[Optional[str], Field(description='File pattern to include in the search (e.g. "*.js", "*.{ts,tsx}")')] = None,
    ) -> str:
        """Search for a pattern in file contents."""
        try:
            # Compile the regex pattern
            try:
                regex = re.compile(pattern, re.MULTILINE)
            except re.error as e:
                return f"Error: Invalid regular expression '{pattern}': {str(e)}"
            
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
            
            # Get files to search
            if include:
                # Use glob pattern to filter files
                if '**' in include:
                    files_to_search = list(search_dir.rglob(include))
                else:
                    files_to_search = list(search_dir.glob(include))
                # Filter to only files
                files_to_search = [f for f in files_to_search if f.is_file()]
            else:
                # Search all text files recursively
                files_to_search = []
                for file_path in search_dir.rglob('*'):
                    if file_path.is_file():
                        # Skip binary files by checking extension
                        if file_path.suffix.lower() not in BINARY_EXTENSIONS:
                            files_to_search.append(file_path)
            
            if not files_to_search:
                return f"No files found to search in {search_dir}" + (f" with pattern '{include}'" if include else "")
            
            # Search for the pattern in each file
            matching_files = []
            matches_found = []
            
            for file_path in files_to_search[:MAX_SEARCH_FILES]:  # Limit to 1000 files for performance
                try:
                    # Try to read the file as text
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    
                    # Search for matches
                    matches = list(regex.finditer(content))
                    
                    if matches:
                        matching_files.append(file_path)
                        
                        # Get line numbers for matches
                        lines = content.split('\n')
                        for match in matches[:MAX_MATCHES_PER_FILE]:  # Limit to first 10 matches per file
                            # Find which line the match is on
                            match_start = match.start()
                            line_num = content[:match_start].count('\n') + 1
                            
                            # Get the line content
                            if line_num <= len(lines):
                                line_content = lines[line_num - 1].strip()
                                matches_found.append({
                                    'file': file_path,
                                    'line_num': line_num,
                                    'line_content': line_content,
                                    'match': match.group()
                                })
                        
                        if len(matches_found) >= MAX_TOTAL_MATCHES:  # Limit total matches displayed
                            break
                            
                except (UnicodeDecodeError, PermissionError, OSError):
                    # Skip files that can't be read
                    continue
            
            if not matching_files:
                return f"No matches found for pattern '{pattern}' in {search_dir}" + (f" (files: {include})" if include else "")
            
            # Sort matching files by modification time
            try:
                matching_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            except (OSError, PermissionError):
                matching_files.sort(key=lambda x: str(x))
            
            # Format the results
            result_lines = [f"Found {len(matching_files)} files with matches for pattern '{pattern}':"]
            result_lines.append("")
            
            # Group matches by file
            current_file = None
            for match_info in matches_found:
                file_path = match_info['file']
                if file_path != current_file:
                    if current_file is not None:
                        result_lines.append("")
                    # Show relative path for cleaner display
                    try:
                        rel_path = file_path.relative_to(search_dir)
                    except ValueError:
                        rel_path = file_path
                    result_lines.append(f"=== {rel_path} ===")
                    current_file = file_path
                
                result_lines.append(f"  {match_info['line_num']:4}: {match_info['line_content']}")
            
            if len(matching_files) > len(set(match['file'] for match in matches_found)):
                result_lines.append("")
                result_lines.append("... (some files with matches not shown due to limits)")
            
            return "\n".join(result_lines)
            
        except Exception as e:
            return f"Error performing grep search: {str(e)}"
