"""Content search tool using regular expressions."""

import os
import subprocess
import time
from pathlib import Path
from typing import Annotated, Dict, List, Optional, Union
from pydantic import Field
from src.tools.base import BaseTool


DESCRIPTION = """
- Fast content search tool that works with any codebase size
- Searches file contents using regular expressions
- Supports full regex syntax (eg. "log.*Error", "function\\s+\\w+", etc.)
- Filter files by pattern with the include parameter (eg. "*.js", "*.{ts,tsx}")
- Returns file paths with at least one match sorted by modification time
- Use this tool when you need to find files containing specific patterns
- If you need to identify/count the number of matches within files, use the Bash tool with `rg` (ripgrep) directly. Do NOT use `grep`.
- When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead
"""

MAX_RESULTS = 100


class GrepTool(BaseTool):
    """Tool for searching file contents using regular expressions."""
    
    name = "Grep"
    description = DESCRIPTION

    def run_impl(
        self,
        pattern: Annotated[str, Field(description="The regular expression pattern to search for in file contents")],
        path: Annotated[Optional[str], Field(description="The directory to search in. Defaults to the current working directory.")] = None,
        include: Annotated[Optional[str], Field(description="File pattern to include in the search (e.g. \"*.js\", \"*.{ts,tsx}\")")] = None,
    ) -> Union[str, Dict]:
        """
        Search for pattern in files using ripgrep.
        
        Returns:
            Union[str, Dict]: Either an error message string or a dict with:
                - filenames: List of matching file paths
                - duration_ms: Search duration in milliseconds
                - num_files: Number of matching files
        """
        start_time = time.time()
        
        # Set search path - default to current working directory
        search_path = Path(path).resolve() if path else Path.cwd()
        
        if not search_path.exists():
            return f"Error: Path '{search_path}' does not exist"
        
        if not search_path.is_dir():
            return f"Error: Path '{search_path}' is not a directory"
        
        try:
            # Build ripgrep command arguments
            cmd = ['rg', '-li', pattern]  # -l: list files, -i: case insensitive
            
            if include:
                cmd.extend(['--glob', include])
            
            # Run ripgrep
            result = subprocess.run(
                cmd,
                cwd=search_path,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            if result.returncode != 0 and result.returncode != 1:
                # returncode 1 is normal for "no matches found"
                return f"Error running ripgrep: {result.stderr.strip()}"
            
            # Parse results
            if not result.stdout.strip():
                filenames = []
            else:
                filenames = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            
            # Get file stats and sort by modification time (newest first)
            file_stats = []
            for filename in filenames:
                file_path = search_path / filename
                try:
                    stat = file_path.stat()
                    file_stats.append((filename, stat.st_mtime))
                except (OSError, FileNotFoundError):
                    # File might have been deleted between search and stat
                    file_stats.append((filename, 0))
            
            # Sort by modification time (newest first), then by filename for ties
            file_stats.sort(key=lambda x: (-x[1], x[0]))
            
            # Extract sorted filenames and limit results
            sorted_filenames = [f[0] for f in file_stats[:MAX_RESULTS]]
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Format output
            num_files = len(sorted_filenames)
            if num_files == 0:
                return "No files found"
            
            result_text = f"Found {num_files} file{'s' if num_files != 1 else ''}\n"
            result_text += "\n".join(sorted_filenames)
            
            if len(filenames) > MAX_RESULTS:
                result_text += "\n(Results are truncated. Consider using a more specific path or pattern.)"
            
            return {
                "filenames": sorted_filenames,
                "duration_ms": duration_ms,
                "num_files": num_files,
                "result_text": result_text
            }
            
        except subprocess.TimeoutExpired:
            return "Error: Search timed out (30 seconds). Try using a more specific pattern or path."
        except FileNotFoundError:
            return "Error: ripgrep (rg) command not found. Please install ripgrep."
        except Exception as e:
            return f"Error: {str(e)}"