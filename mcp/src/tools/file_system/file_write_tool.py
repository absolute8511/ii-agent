"""File writing tool for creating and overwriting files."""

import os
import stat
from pathlib import Path
from typing import Annotated, Optional, Dict, Any, Tuple
from pydantic import Field
from src.tools.base import BaseTool
from src.tools.constants import MAX_LINE_LENGTH
from .shared_state import get_file_tracker


DESCRIPTION = """Writes a file to the local filesystem.

Usage:
- This tool will overwrite the existing file if there is one at the provided path.
- If this is an existing file, you MUST use the Read tool first to read the file's contents. This tool will fail if you did not read the file first.
- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
- NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
- Only use emojis if the user explicitly requests it. Avoid writing emojis to files unless asked."""


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
                f.read(1024)  # Test read a small chunk
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


def generate_diff_summary(old_content: str, new_content: str, file_path: str, max_lines: int = 10) -> Dict[str, Any]:
    """Generate a summary of changes between old and new content."""
    old_lines = old_content.split('\n') if old_content else []
    new_lines = new_content.split('\n')
    
    # Simple diff calculation
    lines_added = len(new_lines) - len(old_lines)
    
    # Get a preview of the content
    preview_lines = new_lines[:max_lines]
    if len(new_lines) > max_lines:
        preview_lines.append(f"... (+{len(new_lines) - max_lines} more lines)")
    
    return {
        "old_line_count": len(old_lines),
        "new_line_count": len(new_lines),
        "lines_added": lines_added,
        "preview": '\n'.join(preview_lines),
        "file_path": file_path
    }


def format_with_line_numbers(content: str, start_line: int = 1, max_lines: Optional[int] = None) -> str:
    """Format content with line numbers in cat -n style."""
    lines = content.split('\n')
    
    if max_lines is not None:
        lines = lines[:max_lines]
    
    formatted_lines = []
    for i, line in enumerate(lines, start=start_line):
        # Truncate long lines
        if len(line) > MAX_LINE_LENGTH:
            line = line[:MAX_LINE_LENGTH - 3] + "..."
        
        # Format with line number like cat -n
        formatted_lines.append(f"     {i}\t{line}")
    
    return '\n'.join(formatted_lines)


def has_write_permission(file_path: str) -> bool:
    """Check if we have write permission for the file or its directory."""
    abs_path = os.path.abspath(file_path)
    
    if os.path.exists(abs_path):
        # Check file permissions
        return os.access(abs_path, os.W_OK)
    else:
        # Check directory permissions
        dir_path = os.path.dirname(abs_path)
        return os.access(dir_path, os.W_OK)


class FileWriteTool(BaseTool):
    """Tool for writing content to files."""
    
    name = "Write"
    description = DESCRIPTION
    
    def __init__(self):
        super().__init__()
        self._file_tracker = get_file_tracker()

    def run_impl(
        self,
        file_path: Annotated[str, Field(description="The absolute path to the file to write (must be absolute, not relative)")],
        content: Annotated[str, Field(description="The content to write to the file")],
    ) -> Dict[str, Any]:
        """Execute the file write operation."""
        
        try:
            # Convert to absolute path
            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)
            
            # Check permissions
            if not has_write_permission(file_path):
                return {
                    "success": False,
                    "error": f"No write permission for: {file_path}",
                    "error_type": "permission_denied"
                }
            
            # Check if file exists
            file_exists = os.path.exists(file_path)
            old_content = ""
            old_encoding = 'utf-8'
            old_line_endings = 'LF'
            
            if file_exists:
                # Validate that file was read first (only for existing files)
                if not self._file_tracker.was_file_read(file_path):
                    return {
                        "success": False,
                        "error": "File has not been read yet. Read it first before writing to it.",
                        "error_type": "not_read_first"
                    }
                
                # Check if file was modified since last read
                if self._file_tracker.is_file_modified_since_read(file_path):
                    return {
                        "success": False,
                        "error": "File has been modified since read, either by the user or by a linter. Read it again before attempting to write it.",
                        "error_type": "file_modified"
                    }
                
                # Check if it's a directory
                if os.path.isdir(file_path):
                    return {
                        "success": False,
                        "error": f"Path is a directory, not a file: {file_path}",
                        "error_type": "is_directory"
                    }
                
                # Read existing content for comparison
                old_encoding = detect_file_encoding(file_path)
                old_line_endings = detect_line_endings(file_path)
                
                try:
                    with open(file_path, 'r', encoding=old_encoding) as f:
                        old_content = f.read()
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to read existing file: {str(e)}",
                        "error_type": "read_error"
                    }
            
            # Determine encoding and line endings to use
            encoding = old_encoding if file_exists else 'utf-8'
            line_endings = old_line_endings if file_exists else 'LF'
            
            # Normalize content line endings
            normalized_content = normalize_line_endings(content, line_endings)
            
            # Create directory if needed
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to create directory {directory}: {str(e)}",
                        "error_type": "mkdir_error"
                    }
            
            # Write the file
            try:
                with open(file_path, 'w', encoding=encoding, newline='') as f:
                    f.write(normalized_content)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to write file: {str(e)}",
                    "error_type": "write_error"
                }
            
            # Update read timestamp to prevent stale writes
            self._file_tracker.mark_file_read(file_path)
            
            # Generate response based on whether this was a create or update
            operation_type = "update" if file_exists else "create"
            
            if operation_type == "create":
                num_lines = len(content.split('\n'))
                preview = format_with_line_numbers(content, max_lines=20)
                
                return {
                    "success": True,
                    "message": f"Created new file: {file_path}",
                    "operation": "create",
                    "file_path": file_path,
                    "content": content,
                    "line_count": num_lines,
                    "preview": preview,
                    "encoding": encoding,
                    "line_endings": line_endings
                }
            else:
                # Generate diff summary for updates
                diff_summary = generate_diff_summary(old_content, content, file_path)
                
                return {
                    "success": True,
                    "message": f"Updated file: {file_path}",
                    "operation": "update", 
                    "file_path": file_path,
                    "content": content,
                    "old_content": old_content,
                    "diff_summary": diff_summary,
                    "encoding": encoding,
                    "line_endings": line_endings
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "error_type": "unexpected_error"
            }