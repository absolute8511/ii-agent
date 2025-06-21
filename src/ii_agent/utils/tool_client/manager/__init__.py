from dataclasses import dataclass
from .terminal_manager import PexpectSessionManager
from .tmux_terminal_manager import TmuxSessionManager
from .str_replace_manager import StrReplaceManager


@dataclass
class SessionResult:
    success: bool
    output: str


@dataclass
class StrReplaceResponse:
    success: bool
    file_content: str


@dataclass
class StrReplaceToolError(Exception):
    message: str

    def __str__(self):
        return self.message


__all__ = [
    "SessionResult",
    "StrReplaceResponse",
    "StrReplaceToolError",
    "PexpectSessionManager",
    "TmuxSessionManager",
    "StrReplaceManager",
]
