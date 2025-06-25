"""MCP (Model Context Protocol) integration for ii-agent.

This module provides MCP server integration capabilities, allowing the agent
to dynamically discover and use tools from MCP servers.
"""

from .base import MCPTool, MCPServer, MCPToolInfo, MCPProtocolClient
from .manager import MCPServerManager
from .registry import MCPRegistry
from .stdio_client import MCPStdioClient
from .sse_client import MCPSSEClient

__all__ = [
    "MCPTool", 
    "MCPServer", 
    "MCPToolInfo", 
    "MCPProtocolClient",
    "MCPServerManager", 
    "MCPRegistry",
    "MCPStdioClient",
    "MCPSSEClient"
]