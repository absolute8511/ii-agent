"""Directory listing tool for exploring file system structure."""

from typing import Annotated, Optional, List
from pydantic import Field
from src.tools.base import BaseTool


DESCRIPTION = """Lists files and directories in a given path. The path parameter must be an absolute path, not a relative path. You can optionally provide an array of glob patterns to ignore with the ignore parameter. You should generally prefer the Glob and Grep tools, if you know which directories to search."""

class LSTool(BaseTool):
    """Tool for listing files and directories."""
    
    name = "LS"
    description = DESCRIPTION

    def run_impl(
        self,
        path: Annotated[str, Field(description="The absolute path to the directory to list (must be absolute, not relative)")],
        ignore: Annotated[Optional[List[str]], Field(description="List of glob patterns to ignore")],
    ):
        return