"""MCP Server Manager for handling MCP server connections and lifecycle."""

import asyncio
import logging
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .base import MCPServer, MCPProtocolClient, MCPToolInfo
from .stdio_client import MCPStdioClient
from .sse_client import MCPSSEClient
from .schema_utils import translate_mcp_schema_to_llm_tool, validate_mcp_tool_schema

logger = logging.getLogger(__name__)


class MCPServerManager:
    """Manages MCP server connections and tool discovery."""
    
    def __init__(self):
        """Initialize the MCP server manager."""
        self.servers: Dict[str, MCPServer] = {}
        self.clients: Dict[str, MCPProtocolClient] = {}
        self.server_tools: Dict[str, List[MCPToolInfo]] = {}
        self.connection_lock = asyncio.Lock()
        self.tool_cache: Dict[str, Any] = {}  # Cache for tool results
        self.connection_pool: Dict[str, List[MCPProtocolClient]] = {}  # Connection pool
        self.max_connections_per_server = 3
        
    async def add_server(self, server: MCPServer) -> bool:
        """Add and connect to an MCP server.
        
        Args:
            server: MCP server configuration
            
        Returns:
            True if server was added and connected successfully
        """
        async with self.connection_lock:
            try:
                logger.info(f"Adding MCP server: {server.name}")
                
                # Store server config
                self.servers[server.name] = server
                
                # Create appropriate client based on transport
                if server.transport == "stdio":
                    client = MCPStdioClient(server)
                elif server.transport == "sse":
                    client = MCPSSEClient(server)
                else:
                    logger.error(f"Unsupported transport: {server.transport}")
                    return False
                
                # Connect to server
                if await client.connect():
                    self.clients[server.name] = client
                    
                    # Discover available tools
                    await self._discover_tools(server.name)
                    
                    logger.info(f"Successfully connected to MCP server: {server.name}")
                    return True
                else:
                    logger.error(f"Failed to connect to MCP server: {server.name}")
                    return False
                    
            except Exception as e:
                logger.error(f"Error adding MCP server {server.name}: {str(e)}")
                return False
    
    async def remove_server(self, server_name: str):
        """Remove and disconnect from an MCP server.
        
        Args:
            server_name: Name of the server to remove
        """
        async with self.connection_lock:
            try:
                # Disconnect client
                if server_name in self.clients:
                    await self.clients[server_name].disconnect()
                    del self.clients[server_name]
                
                # Remove server config and tools
                self.servers.pop(server_name, None)
                self.server_tools.pop(server_name, None)
                
                logger.info(f"Removed MCP server: {server_name}")
                
            except Exception as e:
                logger.error(f"Error removing MCP server {server_name}: {str(e)}")
    
    async def get_server(self, server_name: str) -> Optional[MCPProtocolClient]:
        """Get an MCP server client with connection pooling.
        
        Args:
            server_name: Name of the server
            
        Returns:
            MCP protocol client or None if not found
        """
        # Try to get from connection pool first
        if server_name in self.connection_pool and self.connection_pool[server_name]:
            return self.connection_pool[server_name].pop(0)
        
        # Fall back to main client
        return self.clients.get(server_name)
    
    async def return_server_connection(self, server_name: str, client: MCPProtocolClient):
        """Return a server connection to the pool.
        
        Args:
            server_name: Name of the server
            client: Client to return to pool
        """
        if server_name not in self.connection_pool:
            self.connection_pool[server_name] = []
        
        # Only pool if under limit and connection is healthy
        if len(self.connection_pool[server_name]) < self.max_connections_per_server and client.connected:
            self.connection_pool[server_name].append(client)
        else:
            # Disconnect excess connections
            await client.disconnect()
    
    async def _discover_tools(self, server_name: str):
        """Discover tools available on an MCP server.
        
        Args:
            server_name: Name of the server to discover tools from
        """
        try:
            client = self.clients.get(server_name)
            if not client:
                logger.error(f"No client found for server: {server_name}")
                return
            
            # Get tools from server
            tools_data = await client.list_tools()
            
            # Convert to MCPToolInfo objects
            tools = []
            for tool_data in tools_data:
                # Validate the tool schema
                if not validate_mcp_tool_schema(tool_data):
                    logger.warning(f"Invalid tool schema from server {server_name}: {tool_data}")
                    continue
                
                # Translate schema to LLMTool format
                input_schema = translate_mcp_schema_to_llm_tool(tool_data)
                
                tool_info = MCPToolInfo(
                    name=tool_data.get("name", ""),
                    description=tool_data.get("description", ""),
                    input_schema=input_schema,
                    server_name=server_name
                )
                tools.append(tool_info)
            
            self.server_tools[server_name] = tools
            
            logger.info(f"Discovered {len(tools)} tools from server {server_name}: {[t.name for t in tools]}")
            
        except Exception as e:
            logger.error(f"Error discovering tools from server {server_name}: {str(e)}")
    
    def get_all_tools(self) -> List[MCPToolInfo]:
        """Get all tools from all connected servers.
        
        Returns:
            List of all available MCP tools
        """
        all_tools = []
        for tools in self.server_tools.values():
            all_tools.extend(tools)
        return all_tools
    
    def get_server_tools(self, server_name: str) -> List[MCPToolInfo]:
        """Get tools from a specific server.
        
        Args:
            server_name: Name of the server
            
        Returns:
            List of tools from the specified server
        """
        return self.server_tools.get(server_name, [])
    
    async def health_check(self) -> Dict[str, bool]:
        """Check the health of all connected servers.
        
        Returns:
            Dictionary mapping server names to their health status
        """
        health_status = {}
        
        for server_name, client in self.clients.items():
            try:
                # Try to list tools as a health check
                await client.list_tools()
                health_status[server_name] = True
            except Exception as e:
                logger.warning(f"Health check failed for server {server_name}: {str(e)}")
                health_status[server_name] = False
        
        return health_status
    
    async def shutdown(self):
        """Shutdown all MCP server connections."""
        logger.info("Shutting down MCP server manager...")
        
        # Disconnect all clients
        for server_name in list(self.clients.keys()):
            await self.remove_server(server_name)
        
        logger.info("MCP server manager shutdown complete")