"""Directory listing tool for exploring file system structure."""

import os
import fnmatch
import time
from pathlib import Path
from typing import Annotated, Optional, List, Dict, Any, NamedTuple
from pydantic import Field
from src.tools.base import BaseTool


DESCRIPTION = """Lists files and directories in a given path. The path parameter must be an absolute path, not a relative path. You can optionally provide an array of glob patterns to ignore with the ignore parameter. You should generally prefer the Glob and Grep tools, if you know which directories to search."""

# Constants
MAX_FILES = 1000
TRUNCATED_MESSAGE = f"There are more than {MAX_FILES} files in the repository. Use the LS tool (passing a specific path), Bash tool, and other tools to explore nested directories. The first {MAX_FILES} files and directories are included below:\n\n"


class TreeNode(NamedTuple):
    """Represents a node in the file tree."""
    name: str
    path: str
    type: str  # 'file' or 'directory'
    children: Optional[List['TreeNode']] = None


class LSTool(BaseTool):
    """Tool for listing files and directories."""
    
    name = "LS"
    description = DESCRIPTION

    def _should_skip(self, path: str, ignore_patterns: Optional[List[str]] = None) -> bool:
        """
        Determine if a path should be skipped based on filtering rules.
        
        Args:
            path: The file or directory path to check
            ignore_patterns: Optional list of glob patterns to ignore
            
        Returns:
            True if the path should be skipped, False otherwise
        """
        basename = os.path.basename(path)
        
        # Skip dotfiles and directories (except current directory ".")
        if path != "." and basename.startswith("."):
            return True
            
        # Also check if any part of the path contains hidden directories
        path_parts = path.split(os.sep)
        for part in path_parts:
            if part.startswith(".") and part != "." and part != "..":
                return True
            
        # Skip __pycache__ directories
        if "__pycache__" in path:
            return True
            
        # Check custom ignore patterns
        if ignore_patterns:
            for pattern in ignore_patterns:
                if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(basename, pattern):
                    return True
                    
        return False

    def _list_directory(self, initial_path: str, cwd: str, ignore_patterns: Optional[List[str]] = None) -> List[str]:
        """
        Recursively list files and directories.
        
        Args:
            initial_path: The starting directory path
            cwd: Current working directory for relative path calculation
            ignore_patterns: Optional list of glob patterns to ignore
            
        Returns:
            List of relative paths from cwd
        """
        results = []
        queue = [initial_path]
        
        while queue and len(results) <= MAX_FILES:
            current_path = queue.pop(0)
            
            if self._should_skip(current_path, ignore_patterns):
                continue
                
            # Add directory to results if it's not the initial path
            if current_path != initial_path:
                relative_path = os.path.relpath(current_path, cwd)
                results.append(relative_path + os.sep)
                
            # Try to read directory contents
            try:
                entries = os.listdir(current_path)
                entries.sort()  # Sort entries for consistent output
                
                for entry in entries:
                    entry_path = os.path.join(current_path, entry)
                    
                    if self._should_skip(entry_path, ignore_patterns):
                        continue
                        
                    if os.path.isdir(entry_path):
                        # Add directory to queue for processing
                        queue.append(entry_path)
                    else:
                        # Add file to results
                        relative_path = os.path.relpath(entry_path, cwd)
                        results.append(relative_path)
                        
                    # Check if we've hit the limit
                    if len(results) > MAX_FILES:
                        return results
                        
            except (OSError, PermissionError) as e:
                # Log error but continue processing (similar to TypeScript version)
                # In production, you might want to use a proper logger
                continue
                
        return results

    def _create_file_tree(self, sorted_paths: List[str]) -> List[TreeNode]:
        """
        Create a tree structure from a list of sorted paths.
        
        Args:
            sorted_paths: List of relative file paths
            
        Returns:
            List of TreeNode objects representing the tree structure
        """
        root = []
        
        for path in sorted_paths:
            parts = path.split(os.sep)
            current_level = root
            current_path = ""
            
            for i, part in enumerate(parts):
                if not part:  # Skip empty parts (from trailing slashes)
                    continue
                    
                current_path = os.path.join(current_path, part) if current_path else part
                is_last_part = i == len(parts) - 1
                
                # Find existing node at current level
                existing_node = None
                for node in current_level:
                    if node.name == part:
                        existing_node = node
                        break
                        
                if existing_node:
                    # Use existing node
                    current_level = existing_node.children if existing_node.children else []
                else:
                    # Create new node
                    node_type = "file" if is_last_part else "directory"
                    children = [] if not is_last_part else None
                    
                    new_node = TreeNode(
                        name=part,
                        path=current_path, 
                        type=node_type,
                        children=children
                    )
                    
                    current_level.append(new_node)
                    current_level = children if children is not None else []
                    
        return root

    def _print_tree(self, tree: List[TreeNode], level: int = 0, prefix: str = "") -> str:
        """
        Format tree structure as a readable string.
        
        Args:
            tree: List of TreeNode objects to format
            level: Current indentation level
            prefix: Current line prefix
            
        Returns:
            Formatted tree string
        """
        result = ""
        
        # Add absolute path at root level
        if level == 0:
            result += f"- {os.getcwd()}{os.sep}\n"
            prefix = "  "
            
        for node in tree:
            # Add current node
            suffix = os.sep if node.type == "directory" else ""
            result += f"{prefix}- {node.name}{suffix}\n"
            
            # Recursively add children
            if node.children:
                result += self._print_tree(node.children, level + 1, f"{prefix}  ")
                
        return result

    def run_impl(
        self,
        path: Annotated[str, Field(description="The absolute path to the directory to list (must be absolute, not relative)")],
        ignore: Annotated[Optional[List[str]], Field(description="List of glob patterns to ignore")] = None,
    ) -> Dict[str, Any]:
        """
        Execute the directory listing operation.
        
        Args:
            path: Absolute path to the directory to list
            ignore: Optional list of glob patterns to ignore
            
        Returns:
            Dictionary containing the directory tree and metadata
        """
        start_time = time.time()
        
        try:
            # Validate path is absolute
            if not os.path.isabs(path):
                return {
                    "success": False,
                    "error": f"Path must be absolute, got: {path}",
                    "error_type": "invalid_path"
                }
                
            # Check if path exists
            if not os.path.exists(path):
                return {
                    "success": False,
                    "error": f"Path does not exist: {path}",
                    "error_type": "path_not_found"
                }
                
            # Check if path is a directory
            if not os.path.isdir(path):
                return {
                    "success": False,
                    "error": f"Path is not a directory: {path}",
                    "error_type": "not_a_directory"
                }
                
            # Get current working directory for relative path calculation
            cwd = os.getcwd()
            
            # List directory contents
            file_paths = self._list_directory(path, cwd, ignore)
            file_paths.sort()  # Sort for consistent output
            
            # Create tree structure
            tree = self._create_file_tree(file_paths)
            
            # Format tree as string
            tree_output = self._print_tree(tree)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Check if results were truncated
            truncated = len(file_paths) > MAX_FILES
            
            # Prepare result
            result = {
                "success": True,
                "tree": tree_output,
                "num_items": len(file_paths),
                "truncated": truncated,
                "duration_ms": duration_ms,
                "directory": path
            }
            
            # Add truncation warning if needed
            if truncated:
                result["tree"] = f"{TRUNCATED_MESSAGE}{tree_output}"
                
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "error_type": "unexpected_error"
            }