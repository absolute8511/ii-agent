"""MultiEdit tool for making multiple edits to a single file atomically."""

from typing import Annotated, List, Dict, Any, Optional
from pydantic import Field
from src.tools.base import BaseTool


class MultiEditTool(BaseTool):
    """Tool for making multiple edits to a single file in one operation."""
    
    name = "MultiEdit"
    description = """\
This is a tool for making multiple edits to a single file in one operation. It is built on top of the Edit tool and allows you to perform multiple find-and-replace operations efficiently. Prefer this tool over the Edit tool when you need to make multiple edits to the same file.

Before using this tool:

1. Use the Read tool to understand the file's contents and context
2. Verify the directory path is correct

To make multiple file edits, provide the following:
1. file_path: The absolute path to the file to modify (must be absolute, not relative)
2. edits: An array of edit operations to perform, where each edit contains:
   - old_string: The text to replace (must match the file contents exactly, including all whitespace and indentation)
   - new_string: The edited text to replace the old_string
   - replace_all: Replace all occurences of old_string. This parameter is optional and defaults to false.

IMPORTANT:
- All edits are applied in sequence, in the order they are provided
- Each edit operates on the result of the previous edit
- All edits must be valid for the operation to succeed - if any edit fails, none will be applied
- This tool is ideal when you need to make several changes to different parts of the same file
- For Jupyter notebooks (.ipynb files), use the NotebookEdit instead

CRITICAL REQUIREMENTS:
1. All edits follow the same requirements as the single Edit tool
2. The edits are atomic - either all succeed or none are applied
3. Plan your edits carefully to avoid conflicts between sequential operations

WARNING:
- The tool will fail if edits.old_string doesn't match the file contents exactly (including whitespace)
- The tool will fail if edits.old_string and edits.new_string are the same
- Since edits are applied in sequence, ensure that earlier edits don't affect the text that later edits are trying to find

When making edits:
- Ensure all edits result in idiomatic, correct code
- Do not leave the code in a broken state
- Always use absolute file paths (starting with /)
- Only use emojis if the user explicitly requests it. Avoid adding emojis to files unless asked.
- Use replace_all for replacing and renaming strings across the file. This parameter is useful if you want to rename a variable for instance.

If you want to create a new file, use:
- A new file path, including dir name if needed
- First edit: empty old_string and the new file's contents as new_string
- Subsequent edits: normal edit operations on the created content"""

    def run_impl(
        self,
        file_path: Annotated[str, Field(description="The absolute path to the file to modify")],
        edits: Annotated[List[Dict[str, Any]], Field(description="Array of edit operations to perform sequentially on the file. Each edit should have 'old_string', 'new_string', and optionally 'replace_all' keys.")],
    ) -> str:
        """Perform multiple edits on a file atomically."""
        # TODO: Implement multi-edit logic
        # This would involve:
        # 1. Validating the file path and edits array
        # 2. Reading the current file contents
        # 3. Validating that all old_strings can be found
        # 4. Applying edits sequentially while tracking changes
        # 5. Ensuring atomicity (all or nothing)
        # 6. Writing the final result back to the file
        # 7. Providing feedback on what was changed
        
        edit_count = len(edits)
        edit_descriptions = []
        
        for i, edit in enumerate(edits):
            old_str = edit.get('old_string', '')
            new_str = edit.get('new_string', '')
            replace_all = edit.get('replace_all', False)
            
            edit_descriptions.append(f"Edit {i+1}: Replace {'all' if replace_all else '1'} occurrence(s) of '{old_str[:50]}...' with '{new_str[:50]}...'")
        
        return f"Would apply {edit_count} edits to {file_path}:\n" + "\n".join(edit_descriptions)