"""Client for Claude Code operations that can work locally or remotely."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, AsyncGenerator
import httpx
import asyncio

from ii_agent.core.config.client_config import ClientConfig
from ii_agent.core.storage.models.settings import Settings
from ii_agent.utils.constants import WorkSpaceMode

try:
    from claude_code_sdk import ClaudeCodeOptions, query
    CLAUDE_CODE_AVAILABLE = True
except ImportError:
    CLAUDE_CODE_AVAILABLE = False
    ClaudeCodeOptions = None
    query = None

logger = logging.getLogger(__name__)


class ClaudeCodeResult:
    """Result object for Claude Code operations."""
    
    def __init__(self, success: bool, messages: list = None, error: str = None):
        self.success = success
        self.messages = messages or []
        self.error = error
    
    @property
    def result(self) -> str:
        """Get the final result from the last message."""
        if self.messages:
            last_message = self.messages[-1]
            if hasattr(last_message, 'result'):
                return last_message.result
            return str(last_message)
        return self.error or "No result"


class ClaudeCodeClientBase(ABC):
    """Abstract base class for Claude Code clients."""

    @abstractmethod
    async def execute_task(
        self,
        task: str,
        options: Dict[str, Any],
    ) -> ClaudeCodeResult:
        """Execute a Claude Code task."""
        pass


class LocalClaudeCodeClient(ClaudeCodeClientBase):
    """Local implementation using Claude Code SDK directly."""

    def __init__(self, config: ClientConfig):
        self.config = config
        if not CLAUDE_CODE_AVAILABLE:
            raise ImportError(
                "claude_code_sdk is not available. Install it with: pip install claude-code-sdk"
            )

    async def execute_task(
        self,
        task: str,
        options: Dict[str, Any],
    ) -> ClaudeCodeResult:
        """Execute a Claude Code task locally."""
        try:
            # Convert options dict to ClaudeCodeOptions object
            claude_options = ClaudeCodeOptions(**options)
            
            # Execute Claude Code
            messages = []
            async for message in query(prompt=task, options=claude_options):
                messages.append(message)
            
            return ClaudeCodeResult(success=True, messages=messages)
            
        except Exception as e:
            logger.error(f"Local Claude Code execution error: {e}", exc_info=True)
            return ClaudeCodeResult(success=False, error=str(e))


class RemoteClaudeCodeClient(ClaudeCodeClientBase):
    """Remote implementation using HTTP API calls to sandbox server."""

    def __init__(self, config: ClientConfig):
        self.config = config
        if not config.server_url:
            raise ValueError("server_url is required for remote mode")
        self.server_url = config.server_url.rstrip("/")
        self.timeout = config.timeout

    async def execute_task(
        self,
        task: str,
        options: Dict[str, Any],
    ) -> ClaudeCodeResult:
        """Execute a Claude Code task remotely."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.server_url}/api/claude_code/execute",
                    json={
                        "task": task,
                        "options": options,
                    },
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                result_data = response.json()
                
                if result_data.get("success", False):
                    return ClaudeCodeResult(
                        success=True,
                        messages=result_data.get("messages", [])
                    )
                else:
                    return ClaudeCodeResult(
                        success=False,
                        error=result_data.get("error", "Unknown error")
                    )
                    
        except httpx.RequestError as e:
            logger.error(f"Request error for Claude Code: {e}")
            return ClaudeCodeResult(success=False, error=f"Request error: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for Claude Code: {e}")
            return ClaudeCodeResult(
                success=False,
                error=f"HTTP error {e.response.status_code}: {e.response.text}",
            )
        except Exception as e:
            logger.error(f"Unexpected error for Claude Code: {e}")
            return ClaudeCodeResult(success=False, error=f"Unexpected error: {str(e)}")


class ClaudeCodeClient:
    """Factory class for creating the appropriate client based on configuration."""

    def __init__(self, settings: Settings):
        self.config = settings.client_config
        if settings.sandbox_config.mode == WorkSpaceMode.LOCAL:
            self._client = LocalClaudeCodeClient(self.config)
        elif (
            settings.sandbox_config.mode == WorkSpaceMode.E2B
            or settings.sandbox_config.mode == WorkSpaceMode.DOCKER
        ):
            self._client = RemoteClaudeCodeClient(self.config)
        else:
            raise ValueError(
                f"Unsupported mode: {settings.sandbox_config.mode}. Must be 'local', 'docker', or 'e2b'"
            )

    async def execute_task(
        self,
        task: str,
        options: Dict[str, Any],
    ) -> ClaudeCodeResult:
        """Execute a Claude Code task."""
        return await self._client.execute_task(task, options)