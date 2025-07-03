"""Command execution actions for ii-agent."""

from dataclasses import dataclass
from typing import ClassVar, Optional

from ...core.schema import ActionType
from ..action import Action, ActionConfirmationStatus, ActionSecurityRisk


@dataclass
class CmdRunAction(Action):
    """Runs a shell command in the environment."""
    
    command: str = ""
    is_input: bool = False  # if True, the command is input to a running process
    thought: str = ""
    blocking: bool = False  # if True, run in blocking manner with timeout
    is_static: bool = False  # if True, run in separate process
    cwd: Optional[str] = None  # working directory (only for static commands)
    hidden: bool = False  # if True, hide from logs/UI
    timeout: Optional[int] = None  # timeout in seconds
    runnable: ClassVar[bool] = True
    confirmation_state: ActionConfirmationStatus = ActionConfirmationStatus.CONFIRMED
    security_risk: Optional[ActionSecurityRisk] = ActionSecurityRisk.MEDIUM
    
    @property
    def message(self) -> str:
        if self.is_input:
            return f"Sending input to running process: {self.command}"
        else:
            return f"Running command: {self.command}"
    
    def __str__(self) -> str:
        ret = f"**CmdRunAction (is_input={self.is_input})**\n"
        if self.thought:
            ret += f"THOUGHT: {self.thought}\n"
        if self.cwd:
            ret += f"CWD: {self.cwd}\n"
        ret += f"COMMAND:\n{self.command}"
        return ret


@dataclass
class IPythonRunCellAction(Action):
    """Runs Python code in an IPython/Jupyter environment."""
    
    code: str = ""
    thought: str = ""
    include_extra: bool = True  # include CWD & Python interpreter info
    kernel_init_code: str = ""  # code to run if kernel restarts
    runnable: ClassVar[bool] = True
    confirmation_state: ActionConfirmationStatus = ActionConfirmationStatus.CONFIRMED
    security_risk: Optional[ActionSecurityRisk] = ActionSecurityRisk.MEDIUM
    
    @property
    def message(self) -> str:
        return f"Running Python code: {self.code[:50]}{'...' if len(self.code) > 50 else ''}"
    
    def __str__(self) -> str:
        ret = "**IPythonRunCellAction**\n"
        if self.thought:
            ret += f"THOUGHT: {self.thought}\n"
        ret += f"CODE:\n{self.code}"
        return ret