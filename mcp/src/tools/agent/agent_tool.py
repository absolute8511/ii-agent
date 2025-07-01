"""Agent tool for launching sub-agents to handle complex tasks."""

from typing import Annotated
from pydantic import Field
from src.tools.base import BaseTool
from ..constants import AGENT_TOOL_PROMPT


PROMPT = AGENT_TOOL_PROMPT

DESCRIPTION = PROMPT

class AgentTool(BaseTool):
    """Tool for launching new agents with specific capabilities."""
    
    name = "Task"
    description = DESCRIPTION

    def run_impl(
        self,
        description: Annotated[str, Field(description="A short (3-5 word) description of the task")],
        prompt: Annotated[str, Field(description="The task for the agent to perform")],
    ) -> str:
        """Launch a new agent to handle the specified task."""
        # TODO: Implement agent launching logic
        # This would involve:
        # 1. Creating a new agent instance with the specified tools
        # 2. Setting up the agent's context and workspace
        # 3. Executing the prompt and returning the agent's response
        # 4. Handling any errors or timeouts
        
        return f"Agent task '{description}' would be executed with prompt: {prompt[:100]}..."