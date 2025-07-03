"""File pattern matching tool using glob patterns."""

import glob
import os
import time
from pathlib import Path
from typing import Annotated, Optional, Dict, Any, List
from pydantic import Field
from src.tools.base import BaseTool
from src.tools.constants import MAX_GLOB_RESULTS


DESCRIPTION = """- Fast file pattern matching tool that works with any codebase size
- Supports glob patterns like "**/*.js" or "src/**/*.ts"
- Returns matching file paths sorted by modification time
- Use this tool when you need to find files by name patterns
- When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead
- You have the capability to call multiple tools in a single response. It is always better to speculatively perform multiple searches as a batch that are potentially useful."""


class GlobTool(BaseTool):
    """Tool for finding files using glob patterns."""
    
    name = "Glob"
    description = DESCRIPTION

    def run_impl(
        self,
        pattern: Annotated[str, Field(description="The glob pattern to match files against")],
        path: Annotated[Optional[str], Field(description="The directory to search in. If not specified, the current working directory will be used. IMPORTANT: Omit this field to use the default directory. DO NOT enter \"undefined\" or \"null\" - simply omit it for the default behavior. Must be a valid directory path if provided.")],
    ) -> Dict[str, Any]:
        """Execute the glob pattern matching operation."""
        
        start_time = time.time()
        
        try:
            # Determine the search directory
            if path is None:
                search_dir = os.getcwd()
            else:
                # Convert to absolute path if relative
                if not os.path.isabs(path):
                    search_dir = os.path.abspath(path)
                else:
                    search_dir = path
            
            # Validate that the search directory exists
            if not os.path.exists(search_dir):
                duration_ms = int((time.time() - start_time) * 1000)
                return {
                    "success": False,
                    "error": f"Directory does not exist: {search_dir}",
                    "error_type": "directory_not_found",
                    "duration_ms": duration_ms
                }
            
            if not os.path.isdir(search_dir):
                duration_ms = int((time.time() - start_time) * 1000)
                return {
                    "success": False,
                    "error": f"Path is not a directory: {search_dir}",
                    "error_type": "not_a_directory", 
                    "duration_ms": duration_ms
                }
            
            # Build the full glob pattern
            if os.path.isabs(pattern):
                # If pattern is already absolute, use it as-is
                full_pattern = pattern
            else:
                # Combine search directory with relative pattern
                full_pattern = os.path.join(search_dir, pattern)
            
            # Use pathlib for more robust glob matching
            search_path = Path(search_dir)
            
            try:
                # Use glob with recursive=True for ** patterns
                if '**' in pattern:
                    matches = list(search_path.glob(pattern))
                else:
                    matches = list(search_path.glob(pattern))
                
                # Convert to strings and filter out directories (keep only files)
                file_matches = []
                for match in matches:
                    if match.is_file():
                        file_matches.append(str(match))
                
            except Exception as e:
                # Fallback to standard glob module
                try:
                    if '**' in pattern:
                        raw_matches = glob.glob(full_pattern, recursive=True)
                    else:
                        raw_matches = glob.glob(full_pattern)
                    
                    # Filter to only include files (not directories)
                    file_matches = [m for m in raw_matches if os.path.isfile(m)]
                    
                except Exception as fallback_e:
                    duration_ms = int((time.time() - start_time) * 1000)
                    return {
                        "success": False,
                        "error": f"Glob pattern matching failed: {str(fallback_e)}",
                        "error_type": "glob_error",
                        "duration_ms": duration_ms
                    }
            
            # Sort files by modification time (newest first, like the TypeScript version)
            try:
                file_matches.sort(key=lambda f: os.path.getmtime(f), reverse=True)
            except Exception:
                # If sorting fails, just use alphabetical order
                file_matches.sort()
            
            # Apply limit and check for truncation
            truncated = len(file_matches) > MAX_GLOB_RESULTS
            if truncated:
                file_matches = file_matches[:MAX_GLOB_RESULTS]
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            return {
                "success": True,
                "filenames": file_matches,
                "num_files": len(file_matches),
                "truncated": truncated,
                "duration_ms": duration_ms,
                "search_directory": search_dir,
                "pattern": pattern
            }
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "error": f"Unexpected error during glob operation: {str(e)}",
                "error_type": "unexpected_error",
                "duration_ms": duration_ms
            }