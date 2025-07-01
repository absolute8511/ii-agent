from src.tools.base import BaseTool
from typing import Annotated
from pydantic import Field


class GlobTool(BaseTool):
    name = "glob"
    description = "Efficiently finds files matching specific glob patterns (e.g., `src/**/*.ts`, `**/*.md`), returning absolute paths sorted by modification time (newest first). Ideal for quickly locating files based on their name or path structure, especially in large codebases."

    def run_impl(
        self,
        pattern: Annotated[
            str,
            Field(
                description="The glob pattern to match against (e.g., '**/*.py', 'docs/*.md')"
            ),
        ],
        path: Annotated[
            str,
            Field(
                description="Optional: The absolute path to the directory to search within. If omitted, searches the working directory."
            ),
        ] = "",
        case_sensitive: Annotated[
            bool,
            Field(
                description="Optional: Whether the search should be case-sensitive. Defaults to false."
            ),
        ] = False,
        respect_git_ignore: Annotated[
            bool,
            Field(
                description="Optional: Whether to respect .gitignore patterns when listing files. Only available in git repositories. Defaults to true."
            ),
        ] = True,
    ):
        pass
