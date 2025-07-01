from src.tools.base import BaseTool
from typing import Annotated, Optional
from pydantic import Field


class GrepTool(BaseTool):
    name = "search_file_content"
    description = "Searches for a regular expression pattern within the content of files in a specified directory (or current working directory). Can filter files by a glob pattern. Returns the lines containing matches, along with their file paths and line numbers."

    def run_impl(
        self,
        pattern: Annotated[
            str,
            Field(
                description="The regular expression (regex) pattern to search for within file contents (e.g., 'function\\s+myFunction', 'import\\s+\\{.*\\}\\s+from\\s+.*')."
            ),
        ],
        path: Annotated[
            str,
            Field(
                description="Optional: The absolute path to the directory to search within. If omitted, searches the working directory."
            ),
        ] = "",
        include: Annotated[
            str,
            Field(
                description="Optional: A glob pattern to filter which files are searched (e.g., '*.js', '*.{ts,tsx}', 'src/**'). If omitted, searches all files (respecting potential global ignores)."
            ),
        ] = "",
    ):
        pass
