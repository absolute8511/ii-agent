"""Jupyter notebook editing tool."""

from typing import Annotated, Optional
from pydantic import Field
from src.tools.base import BaseTool


DESCRIPTION = """Completely replaces the contents of a specific cell in a Jupyter notebook (.ipynb file) with new source. Jupyter notebooks are interactive documents that combine code, text, and visualizations, commonly used for data analysis and scientific computing. The notebook_path parameter must be an absolute path, not a relative path. The cell_number is 0-indexed. Use edit_mode=insert to add a new cell at the index specified by cell_number. Use edit_mode=delete to delete the cell at the index specified by cell_number."""

class NotebookEditTool(BaseTool):
    """Tool for editing Jupyter notebook files."""
    
    name = "NotebookEdit"
    description = DESCRIPTION

    def run_impl(
        self,
        notebook_path: Annotated[str, Field(description="The absolute path to the Jupyter notebook file to edit (must be absolute, not relative)")],
        new_source: Annotated[str, Field(description="The new source for the cell")],
        cell_id: Annotated[Optional[str], Field(description="The ID of the cell to edit. When inserting a new cell, the new cell will be inserted after the cell with this ID, or at the beginning if not specified.")],
        cell_type: Annotated[Optional[str], Field(description="The type of the cell (code or markdown). If not specified, it defaults to the current cell type. If using edit_mode=insert, this is required.")],
        edit_mode: Annotated[Optional[str], Field(description="The type of edit to make (replace, insert, delete). Defaults to replace.")],
    ) -> str:
        return ""