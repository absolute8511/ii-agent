from pathlib import Path
from src.tools.base import BaseTool
from src.utils.workspace_manager import WorkspaceManager
from pydantic import Field
from typing import Annotated
from .tmux_terminal_manager import TmuxSessionManager


class BaseShellTool(BaseTool):
    def __init__(self, workspace_manager: WorkspaceManager):
        self.workspace_manager = workspace_manager
        self.terminal_manager = TmuxSessionManager(
            default_shell="/bin/bash",
            default_timeout=30,
            cwd=str(workspace_manager.root),
        )
    
class ShellExecTool(BaseShellTool):
    name = "shell_exec"
    description = "Execute commands in a specified shell session. Use for running code, installing packages, or managing files."

    def run_impl(
        self,
        session_id: Annotated[str, Field(description="Unique identifier of defthe target shell session; automatically creates new session if not exists")],
        command: Annotated[str, Field(description="Shell command to execute")],
        exec_dir: Annotated[str, Field(description="Working directory for command execution")],
    ) -> str:

        workspace_exec_dir = str(self.workspace_manager.container_path(Path(exec_dir)))

        result = self.terminal_manager.shell_exec(
            session_id, command, workspace_exec_dir, timeout=30
        )
        return result.output


class ShellViewTool(BaseShellTool):
    name = "shell_view"
    description = "View the content of a specified shell session. Use for checking command execution results or monitoring output."

    def run_impl(
        self,
        session_id: Annotated[str, Field(description="Unique identifier of the target shell session")],
    ) -> str:

        result = self.terminal_manager.shell_view(session_id)
        return result.output


class ShellWaitTool(BaseShellTool):
    name = "shell_wait"
    description = "Wait for a specified number of seconds in a shell session"

    def run_impl(
        self,
        session_id: Annotated[str, Field(description="Unique identifier of the target shell session")],
        seconds: Annotated[int, Field(description="Number of seconds to wait")],
    ) -> str:

        result = self.terminal_manager.shell_wait(session_id, seconds)
        return result


class ShellKillProcessTool(BaseShellTool):
    name = "shell_kill_process"
    description = "Terminate a running process in a specified shell session. Use for stopping long-running processes or handling frozen commands."

    def run_impl(
        self,
        session_id: Annotated[str, Field(description="Unique identifier of the target shell session")],
    ) -> str:
        result = self.terminal_manager.shell_kill_process(session_id)
        return result.output


class ShellWriteToProcessTool(BaseShellTool):
    name = "shell_write_to_process"
    description = "Write to a process in a specified shell session. Use for interacting with running processes."

    def run_impl(
        self,
        session_id: Annotated[str, Field(description="Unique identifier of the target shell session")],
        input_text: Annotated[str, Field(description="Text to write to the process")],
        press_enter: Annotated[bool, Field(description="Whether to press enter after writing the text")],
    ) -> str:
        result = self.terminal_manager.shell_write_to_process(
            session_id, input_text, press_enter
        )
        return result.output
