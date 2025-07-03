"""File editing tool for making targeted edits to files."""

import os
import stat
from pathlib import Path
from typing import Annotated, Optional, Dict, Any, Tuple
from pydantic import Field
from src.tools.base import BaseTool
from .shared_state import get_file_tracker
import glob


DESCRIPTION = """Performs exact string replacements in files. 

Usage:
- You must use your `Read` tool at least once in the conversation before editing. This tool will error if you attempt an edit without reading the file. 
- When editing text from Read tool output, ensure you preserve the exact indentation (tabs/spaces) as it appears AFTER the line number prefix. The line number prefix format is: spaces + line number + tab. Everything after that tab is the actual file content to match. Never include any part of the line number prefix in the old_string or new_string.
- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
- Only use emojis if the user explicitly requests it. Avoid adding emojis to files unless asked.
- The edit will FAIL if `old_string` is not unique in the file. Either provide a larger string with more surrounding context to make it unique or use `replace_all` to change every instance of `old_string`. 
- Use `replace_all` for replacing and renaming strings across the file. This parameter is useful if you want to rename a variable for instance."""


def detect_file_encoding(file_path: str) -> str:
    """Detect file encoding using charset-normalizer or fallback methods."""
    try:
        # Try charset-normalizer first (recommended modern approach)
        import charset_normalizer  # type: ignore
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        result = charset_normalizer.from_bytes(raw_data)
        if result.best():
            return str(result.best().encoding)
    except ImportError:
        pass
    
    try:
        # Fallback to chardet if available
        import chardet  # type: ignore
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        result = chardet.detect(raw_data)
        encoding = result.get('encoding') if result else None
        if encoding:
            return encoding
    except ImportError:
        pass
    
    # Final fallback - try common encodings
    common_encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'ascii']
    for encoding in common_encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read()
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    # Default fallback
    return 'utf-8'


def detect_line_endings(file_path: str) -> str:
    """Detect line endings in file. Returns 'CRLF', 'LF', or 'CR'."""
    if not os.path.exists(file_path):
        return 'LF'  # Default for new files
    
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        if b'\r\n' in content:
            return 'CRLF'
        elif b'\n' in content:
            return 'LF'
        elif b'\r' in content:
            return 'CR'
        else:
            return 'LF'  # Default
    except Exception:
        return 'LF'


def normalize_line_endings(text: str, line_ending_type: str) -> str:
    """Normalize line endings in text based on detected type."""
    # First normalize everything to LF
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    if line_ending_type == 'CRLF':
        return text.replace('\n', '\r\n')
    elif line_ending_type == 'CR':
        return text.replace('\n', '\r')
    else:  # LF
        return text


def get_file_snippet(original_content: str, old_string: str, new_string: str, num_context_lines: int = 4) -> Tuple[str, int]:
    """Get a snippet of the file around the change for display purposes."""
    if not original_content:
        return new_string, 1
    
    lines = original_content.split('\n')
    if old_string not in original_content:
        return '\n'.join(lines[:min(10, len(lines))]), 1
    
    # Find the line containing the old string
    change_line_idx = -1
    for i, line in enumerate(lines):
        if old_string in '\n'.join(lines[i:]):
            # More precise: find where the old_string starts
            remaining_text = '\n'.join(lines[i:])
            if remaining_text.startswith(old_string) or '\n' + old_string in remaining_text:
                change_line_idx = i
                break
    
    if change_line_idx == -1:
        change_line_idx = 0
    
    # Calculate snippet bounds
    start_idx = max(0, change_line_idx - num_context_lines)
    
    # Apply the change to get new content
    new_content = original_content.replace(old_string, new_string)
    new_lines = new_content.split('\n')
    
    # Calculate how many lines the replacement spans
    old_line_count = old_string.count('\n') + 1
    new_line_count = new_string.count('\n') + 1
    line_diff = new_line_count - old_line_count
    
    end_idx = min(len(new_lines), change_line_idx + num_context_lines + max(old_line_count, new_line_count))
    
    snippet_lines = new_lines[start_idx:end_idx]
    snippet = '\n'.join(snippet_lines)
    
    return snippet, start_idx + 1  # +1 for 1-based line numbering


def has_write_permission(file_path: str) -> bool:
    """Check if the file/directory has write permissions."""
    try:
        if os.path.exists(file_path):
            return os.access(file_path, os.W_OK)
        else:
            # Check parent directory for new file creation
            parent_dir = os.path.dirname(file_path)
            return os.access(parent_dir, os.W_OK) if os.path.exists(parent_dir) else False
    except Exception:
        return False


def find_similar_file(file_path: str) -> Optional[str]:
    """Find similar files with different extensions."""
    try:
        base_path = os.path.splitext(file_path)[0]
        parent_dir = os.path.dirname(file_path)
        base_name = os.path.basename(base_path)
        
        # Look for files with same base name but different extensions
        pattern = os.path.join(parent_dir, f"{base_name}.*")
        similar_files = glob.glob(pattern)
        
        if similar_files:
            # Return the first match that's not the original file
            for similar in similar_files:
                if similar != file_path:
                    return similar
        
        return None
    except Exception:
        return None


class FileEditTool(BaseTool):
    """Tool for making targeted string replacements in files."""
    
    name = "Edit"
    description = DESCRIPTION
    
    def __init__(self):
        super().__init__()
        self._file_tracker = get_file_tracker()
    
    def needs_permissions(self, file_path: str) -> bool:
        """Check if this operation needs special permissions."""
        return not has_write_permission(file_path)

    def run_impl(
        self,
        file_path: Annotated[str, Field(description="The absolute path to the file to modify")],
        old_string: Annotated[str, Field(description="The text to replace")],
        new_string: Annotated[str, Field(description="The text to replace it with (must be different from old_string)")],
        replace_all: Annotated[bool, Field(description="Replace all occurences of old_string (default false)", default=False)],
    ) -> Dict[str, Any]:
        """Execute the file edit operation."""
        
        try:
            # Input validation
            if old_string == new_string:
                return {
                    "success": False,
                    "error": "No changes to make: old_string and new_string are exactly the same.",
                    "error_type": "validation_error"
                }
            
            # Convert to absolute path
            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)
            
            # Check write permissions
            if not has_write_permission(file_path):
                return {
                    "success": False,
                    "error": "Insufficient permissions to write to this file or directory.",
                    "error_type": "permission_denied"
                }
            
            # Check if file exists for non-create operations
            file_exists = os.path.exists(file_path)
            
            if file_exists and old_string == "":
                return {
                    "success": False,
                    "error": "Cannot create new file - file already exists.",
                    "error_type": "file_exists"
                }
            
            # Handle file creation
            if not file_exists and old_string == "":
                try:
                    # Create directory if needed
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    
                    # Write new file
                    with open(file_path, 'w', encoding='utf-8', newline='') as f:
                        f.write(normalize_line_endings(new_string, 'LF'))
                    
                    # Update read timestamp
                    self._file_tracker.mark_file_read(file_path)
                    
                    snippet, start_line = get_file_snippet("", old_string, new_string)
                    
                    return {
                        "success": True,
                        "message": f"Created new file: {file_path}",
                        "file_path": file_path,
                        "old_string": old_string,
                        "new_string": new_string,
                        "snippet": snippet,
                        "start_line": start_line,
                        "operation": "create"
                    }
                    
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to create file: {str(e)}",
                        "error_type": "file_operation"
                    }
            
            # File must exist for edit operations
            if not file_exists:
                # Try to find a similar file with a different extension
                similar_file = find_similar_file(file_path)
                error_msg = "File does not exist."
                if similar_file:
                    error_msg += f" Did you mean {similar_file}?"
                
                return {
                    "success": False,
                    "error": error_msg,
                    "error_type": "file_not_found",
                    "suggested_file": similar_file
                }
            
            # Check for Jupyter notebooks
            if file_path.endswith('.ipynb'):
                return {
                    "success": False,
                    "error": "File is a Jupyter Notebook. Use the NotebookEdit tool to edit this file.",
                    "error_type": "wrong_tool"
                }
            
            # Check read timestamp
            if not self._file_tracker.was_file_read(file_path):
                return {
                    "success": False,
                    "error": "File has not been read yet. Read it first before writing to it.",
                    "error_type": "read_required"
                }
            
            # Check if file was modified since last read
            if self._file_tracker.is_file_modified_since_read(file_path):
                return {
                    "success": False,
                    "error": "File has been modified since read, either by the user or by a linter. Read it again before attempting to write it.",
                    "error_type": "file_modified"
                }
            
            # Read file with proper encoding
            encoding = detect_file_encoding(file_path)
            line_ending_type = detect_line_endings(file_path)
            
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    original_content = f.read()
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to read file: {str(e)}",
                    "error_type": "read_error"
                }
            
            # Check if old_string exists in file
            if old_string not in original_content:
                return {
                    "success": False,
                    "error": "String to replace not found in file.",
                    "error_type": "string_not_found"
                }
            
            # Check for multiple matches if not replace_all
            if not replace_all:
                match_count = original_content.count(old_string)
                if match_count > 1:
                    return {
                        "success": False,
                        "error": f"Found {match_count} matches of the string to replace. For safety, this tool only supports replacing exactly one occurrence at a time. Add more lines of context to your edit and try again.",
                        "error_type": "multiple_matches"
                    }
            
            # Perform the replacement
            if replace_all:
                new_content = original_content.replace(old_string, new_string)
            else:
                new_content = original_content.replace(old_string, new_string, 1)
            
            # Normalize line endings to match original file
            new_content = normalize_line_endings(new_content, line_ending_type)
            
            # Write the file back
            try:
                with open(file_path, 'w', encoding=encoding, newline='') as f:
                    f.write(new_content)
                
                # Update read timestamp
                self._file_tracker.mark_file_read(file_path)
                
                # Generate snippet for response
                snippet, start_line = get_file_snippet(original_content, old_string, new_string)
                
                return {
                    "success": True,
                    "message": f"Successfully updated file: {file_path}",
                    "file_path": file_path,
                    "old_string": old_string,
                    "new_string": new_string,
                    "snippet": snippet,
                    "start_line": start_line,
                    "operation": "replace_all" if replace_all else "replace_once",
                    "matches_replaced": original_content.count(old_string) if replace_all else 1
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to write file: {str(e)}",
                    "error_type": "write_error"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "error_type": "unexpected_error"
            }