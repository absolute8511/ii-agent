"""File reading tool for reading file contents."""

import os
from pathlib import Path
from typing import Annotated, Optional, Dict, Any
from pydantic import Field
from src.tools.base import BaseTool
from src.tools.constants import MAX_FILE_READ_LINES, MAX_LINE_LENGTH
from .shared_state import get_file_tracker


DESCRIPTION = """Reads a file from the local filesystem. You can access any file directly by using this tool.
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


def format_with_line_numbers(content: str, start_line: int = 1, max_lines: Optional[int] = None, max_line_length: int = MAX_LINE_LENGTH) -> str:
    """Format content with line numbers in cat -n style."""
    lines = content.split('\n')
    
    if max_lines is not None:
        lines = lines[:max_lines]
    
    formatted_lines = []
    for i, line in enumerate(lines, start=start_line):
        # Truncate long lines
        if len(line) > max_line_length:
            line = line[:max_line_length - 3] + "..."
        
        # Format with line number like cat -n
        formatted_lines.append(f"     {i}\t{line}")
    
    return '\n'.join(formatted_lines)


def is_binary_file(file_path: str, sample_size: int = 8192) -> bool:
    """Check if a file appears to be binary by examining a sample."""
    try:
        with open(file_path, 'rb') as f:
            sample = f.read(sample_size)
        
        # Check for null bytes (common in binary files)
        if b'\x00' in sample:
            return True
        
        # Check if the sample can be decoded as text
        try:
            sample.decode('utf-8')
            return False
        except UnicodeDecodeError:
            try:
                sample.decode('latin-1')
                return False
            except UnicodeDecodeError:
                return True
                
    except Exception:
        return False


class FileReadTool(BaseTool):
    """Tool for reading file contents with optional line range specification."""
    
    name = "Read"
    description = DESCRIPTION
    
    def __init__(self):
        super().__init__()
        self._file_tracker = get_file_tracker()

    def run_impl(
        self,
        file_path: Annotated[str, Field(description="The absolute path to the file to read")],
        limit: Annotated[Optional[int], Field(description="The number of lines to read. Only provide if the file is too large to read at once.")] = None,
        offset: Annotated[Optional[int], Field(description="The line number to start reading from. Only provide if the file is too large to read at once")] = None,
    ) -> Dict[str, Any]:
        """Read file contents and return formatted output."""
        
        try:
            # Convert to absolute path
            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)
            
            # Check if file exists
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"File does not exist: {file_path}",
                    "error_type": "file_not_found"
                }
            
            # Check if it's a directory
            if os.path.isdir(file_path):
                return {
                    "success": False,
                    "error": f"Path is a directory, not a file: {file_path}",
                    "error_type": "is_directory"
                }
            
            # Check for Jupyter notebooks
            if file_path.endswith('.ipynb'):
                return {
                    "success": False,
                    "error": "File is a Jupyter Notebook. Use the NotebookRead tool to read this file.",
                    "error_type": "wrong_tool"
                }
            
            # Handle image files and other binary files
            if is_binary_file(file_path):
                # For images and other binary files, we'll return a message
                # In a real implementation, this might display the image or provide file info
                file_size = os.path.getsize(file_path)
                return {
                    "success": True,
                    "content": f"[Binary file: {os.path.basename(file_path)}, size: {file_size} bytes]",
                    "file_path": file_path,
                    "is_binary": True,
                    "size_bytes": file_size
                }
            
            # Set defaults for limit and offset
            if limit is None:
                limit = MAX_FILE_READ_LINES
            if offset is None:
                offset = 1
            
            # Validate parameters
            if offset < 1:
                offset = 1
            if limit < 1:
                limit = 1
            
            # Detect file encoding
            encoding = detect_file_encoding(file_path)
            
            try:
                # Read the file
                with open(file_path, 'r', encoding=encoding) as f:
                    lines = f.readlines()
                
                # Mark file as read for timestamp tracking
                self._file_tracker.mark_file_read(file_path)
                
                # Handle empty file
                if not lines:
                    return {
                        "success": True,
                        "content": "[WARNING: File exists but has empty contents]",
                        "file_path": file_path,
                        "total_lines": 0,
                        "lines_read": 0,
                        "start_line": offset,
                        "encoding": encoding
                    }
                
                # Apply offset and limit
                start_idx = offset - 1  # Convert to 0-based indexing
                end_idx = start_idx + limit
                
                if start_idx >= len(lines):
                    return {
                        "success": False,
                        "error": f"Start line {offset} is beyond file length ({len(lines)} lines)",
                        "error_type": "invalid_range"
                    }
                
                selected_lines = lines[start_idx:end_idx]
                
                # Join lines and remove the final newline if present (since readlines() includes \n)
                content = ''.join(selected_lines)
                if content.endswith('\n'):
                    content = content[:-1]
                
                # Format with line numbers
                formatted_content = format_with_line_numbers(content, start_line=offset)
                
                return {
                    "success": True,
                    "content": formatted_content,
                    "file_path": file_path,
                    "total_lines": len(lines),
                    "lines_read": len(selected_lines),
                    "start_line": offset,
                    "end_line": offset + len(selected_lines) - 1,
                    "encoding": encoding
                }
                
            except UnicodeDecodeError as e:
                return {
                    "success": False,
                    "error": f"Failed to decode file with encoding '{encoding}': {str(e)}",
                    "error_type": "encoding_error"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to read file: {str(e)}",
                    "error_type": "read_error"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "error_type": "unexpected_error"
            }