"""Jupyter notebook reading tool."""

from typing import Annotated, Optional
from pydantic import Field
from src.tools.base import BaseTool


DESCRIPTION = """Reads a Jupyter notebook (.ipynb file) and returns all of the cells with their outputs. Jupyter notebooks are interactive documents that combine code, text, and visualizations, commonly used for data analysis and scientific computing. The notebook_path parameter must be an absolute path, not a relative path."""

class NotebookReadTool(BaseTool):
    """Tool for reading Jupyter notebook files."""
    
    name = "NotebookRead"
    description = DESCRIPTION

    def run_impl(
        self,
        notebook_path: Annotated[str, Field(description="The absolute path to the Jupyter notebook file to read (must be absolute, not relative)")],
        cell_id: Annotated[Optional[str], Field(description="The ID of a specific cell to read. If not provided, all cells will be read.")],
    ) -> str:
        return ""