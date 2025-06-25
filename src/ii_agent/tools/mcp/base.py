"""Base classes for MCP (Model Context Protocol) integration."""

import asyncio
import json
import logging
from typing import Any, Dict, Optional, List
from dataclasses import dataclass

from ii_agent.tools.base import LLMTool, ToolImplOutput
from ii_agent.llm.message_history import MessageHistory

logger = logging.getLogger(__name__)


@dataclass
class MCPServer:
    """Configuration for an MCP server."""
    name: str
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    transport: str = "stdio"  # "stdio" or "sse"
    url: Optional[str] = None  # For SSE transport


@dataclass
class MCPToolInfo:
    """Information about a tool available from an MCP server."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str


class MCPTool(LLMTool):
    """A tool that proxies calls to an MCP server tool."""
    
    def __init__(self, tool_info: MCPToolInfo, server_manager: 'MCPServerManager'):
        """Initialize MCP tool proxy.
        
        Args:
            tool_info: Information about the MCP tool
            server_manager: Manager for MCP server connections
        """
        self.name = tool_info.name
        self.description = tool_info.description
        self.input_schema = tool_info.input_schema
        self.server_name = tool_info.server_name
        self.server_manager = server_manager
        
    async def run_impl(
        self, 
        tool_input: Dict[str, Any], 
        message_history: Optional[MessageHistory] = None
    ) -> ToolImplOutput:
        """Execute the tool on the MCP server with improved error handling and connection management.
        
        Args:
            tool_input: Input parameters for the tool
            message_history: Optional message history
            
        Returns:
            Tool execution result
        """
        server = None
        try:
            # Get the MCP server connection
            server = await self.server_manager.get_server(self.server_name)
            if not server:
                raise RuntimeError(f"MCP server '{self.server_name}' not available")
            
            # Execute the tool on the MCP server with timeout
            result = await asyncio.wait_for(
                server.call_tool(self.name, tool_input),
                timeout=60.0  # 60 second timeout
            )
            
            # Convert MCP result to our format
            if isinstance(result, dict):
                if result.get("isError"):
                    tool_output = f"Error: {result.get('content', 'Unknown error')}"
                    tool_result_message = f"MCP tool '{self.name}' failed"
                else:
                    tool_output = result.get("content", "")
                    tool_result_message = f"MCP tool '{self.name}' executed successfully"
            else:
                tool_output = str(result)
                tool_result_message = f"MCP tool '{self.name}' executed successfully"
                
            return ToolImplOutput(
                tool_output=tool_output,
                tool_result_message=tool_result_message,
                auxiliary_data={
                    "mcp_server": self.server_name,
                    "mcp_tool": self.name
                }
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout executing MCP tool '{self.name}'")
            return ToolImplOutput(
                tool_output="Error: Tool execution timed out",
                tool_result_message=f"MCP tool '{self.name}' timed out",
                auxiliary_data={
                    "error": "timeout",
                    "mcp_server": self.server_name,
                    "mcp_tool": self.name
                }
            )
        except Exception as e:
            logger.error(f"Error executing MCP tool '{self.name}': {str(e)}")
            return ToolImplOutput(
                tool_output=f"Error executing MCP tool: {str(e)}",
                tool_result_message=f"MCP tool '{self.name}' failed: {str(e)}",
                auxiliary_data={
                    "error": str(e),
                    "mcp_server": self.server_name,
                    "mcp_tool": self.name
                }
            )
        finally:
            # Return connection to pool if available
            if server and hasattr(self.server_manager, 'return_server_connection'):
                try:
                    await self.server_manager.return_server_connection(self.server_name, server)
                except Exception as e:
                    logger.warning(f"Error returning connection to pool: {str(e)}")
    
    def get_tool_start_message(self, tool_input: Dict[str, Any]) -> str:
        """Return a user-friendly message when the tool is called."""
        return f"Calling MCP tool '{self.name}' on server '{self.server_name}'"


class MCPProtocolClient:
    """Base class for MCP protocol communication."""
    
    def __init__(self, server_config: MCPServer):
        """Initialize MCP protocol client.
        
        Args:
            server_config: Configuration for the MCP server
        """
        self.server_config = server_config
        self.connected = False
        
    async def connect(self) -> bool:
        """Connect to the MCP server.
        
        Returns:
            True if connected successfully, False otherwise
        """
        raise NotImplementedError
        
    async def disconnect(self):
        """Disconnect from the MCP server."""
        raise NotImplementedError
        
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the MCP server.
        
        Returns:
            List of tool definitions
        """
        raise NotImplementedError
        
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        raise NotImplementedError
        
    async def list_prompts(self) -> List[Dict[str, Any]]:
        """List available prompts from the MCP server.
        
        Returns:
            List of prompt definitions
        """
        raise NotImplementedError