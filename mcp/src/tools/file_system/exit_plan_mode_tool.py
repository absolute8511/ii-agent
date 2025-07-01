"""Exit plan mode tool for transitioning from planning to implementation."""

from typing import Annotated
from pydantic import Field
from src.tools.base import BaseTool


class ExitPlanModeTool(BaseTool):
    """Tool for exiting plan mode when ready to begin implementation."""
    
    name = "exit_plan_mode"
    description = """Use this tool when you are in plan mode and have finished presenting your plan and are ready to code. This will prompt the user to exit plan mode. 
IMPORTANT: Only use this tool when the task requires planning the implementation steps of a task that requires writing code. For research tasks where you're gathering information, searching files, reading files or in general trying to understand the codebase - do NOT use this tool.

Eg. 
1. Initial task: "Search for and understand the implementation of vim mode in the codebase" - Do not use the exit plan mode tool because you are not planning the implementation steps of a task.
2. Initial task: "Help me implement yank mode for vim" - Use the exit plan mode tool after you have finished planning the implementation steps of the task.
"""

    def run_impl(
        self,
        plan: Annotated[str, Field(description="The plan you came up with, that you want to run by the user for approval. Supports markdown. The plan should be pretty concise.")],
    ) -> str:
        """Exit plan mode and present the plan to the user for approval."""
        # TODO: Implement plan mode exit logic
        # This would involve:
        # 1. Validating that a plan has been created
        # 2. Formatting the plan appropriately for user review
        # 3. Transitioning the system state from planning to implementation
        # 4. Prompting the user for approval to proceed
        # 5. Handling user feedback on the plan
        
        return f"Exiting plan mode with the following plan:\n\n{plan}\n\nWaiting for user approval to proceed with implementation..."