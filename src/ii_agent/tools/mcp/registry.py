"""MCP Registry for managing MCP server configurations and tool discovery."""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from .base import MCPServer, MCPTool
from .manager import MCPServerManager

logger = logging.getLogger(__name__)


class MCPRegistry:
    """Registry for MCP servers and their configurations."""
    
    def __init__(self, workspace_root: Optional[Path] = None):
        """Initialize the MCP registry.
        
        Args:
            workspace_root: Root directory for workspace-specific MCP configurations
        """
        self.workspace_root = workspace_root or Path.cwd()
        self.server_manager = MCPServerManager()
        self.initialized = False
    
    async def initialize(self, tool_args: Optional[Dict[str, Any]] = None) -> bool:
        """Initialize the MCP registry by discovering and connecting to servers.
        
        Args:
            tool_args: Tool configuration arguments
            
        Returns:
            True if initialization was successful
        """
        if self.initialized:
            return True
            
        try:
            logger.info("Initializing MCP registry...")
            
            # Load server configurations
            servers = await self._load_server_configurations(tool_args)
            
            # Connect to servers
            connected_count = 0
            for server in servers:
                if await self.server_manager.add_server(server):
                    connected_count += 1
            
            logger.info(f"MCP registry initialized with {connected_count}/{len(servers)} servers connected")
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Error initializing MCP registry: {str(e)}")
            return False
    
    async def _load_server_configurations(self, tool_args: Optional[Dict[str, Any]] = None) -> List[MCPServer]:
        """Load MCP server configurations from various sources.
        
        Args:
            tool_args: Tool configuration arguments
            
        Returns:
            List of MCP server configurations
        """
        servers = []
        
        # 1. Load from .mcprc file in workspace
        mcprc_servers = await self._load_from_mcprc()
        servers.extend(mcprc_servers)
        
        # 2. Load from environment variables
        env_servers = await self._load_from_environment()
        servers.extend(env_servers)
        
        # 3. Load from tool_args
        if tool_args and tool_args.get("mcp_servers"):
            arg_servers = await self._load_from_tool_args(tool_args["mcp_servers"])
            servers.extend(arg_servers)
        
        # 4. Load default servers if enabled
        if tool_args and tool_args.get("mcp_defaults", True):
            default_servers = await self._load_default_servers()
            servers.extend(default_servers)
        
        # Remove duplicates (by name)
        unique_servers = {}
        for server in servers:
            unique_servers[server.name] = server
        
        return list(unique_servers.values())
    
    async def _load_from_mcprc(self) -> List[MCPServer]:
        """Load server configurations from .mcprc file."""
        servers = []
        
        mcprc_paths = [
            self.workspace_root / ".mcprc",
            Path.home() / ".mcprc"
        ]
        
        for mcprc_path in mcprc_paths:
            if mcprc_path.exists():
                try:
                    with open(mcprc_path, 'r') as f:
                        config = json.load(f)
                    
                    for name, server_config in config.items():
                        server = MCPServer(
                            name=name,
                            command=server_config.get("command", ""),
                            args=server_config.get("args", []),
                            env=server_config.get("env"),
                            description=server_config.get("description"),
                            transport=server_config.get("transport", "stdio"),
                            url=server_config.get("url")
                        )
                        servers.append(server)
                    
                    logger.info(f"Loaded {len(config)} servers from {mcprc_path}")
                    break  # Use first found .mcprc file
                    
                except Exception as e:
                    logger.error(f"Error loading .mcprc from {mcprc_path}: {str(e)}")
        
        return servers
    
    async def _load_from_environment(self) -> List[MCPServer]:
        """Load server configurations from environment variables."""
        servers = []
        
        # Look for MCP_SERVERS environment variable
        mcp_servers_env = os.environ.get("MCP_SERVERS")
        if mcp_servers_env:
            try:
                config = json.loads(mcp_servers_env)
                for name, server_config in config.items():
                    server = MCPServer(
                        name=name,
                        command=server_config.get("command", ""),
                        args=server_config.get("args", []),
                        env=server_config.get("env"),
                        description=server_config.get("description"),
                        transport=server_config.get("transport", "stdio"),
                        url=server_config.get("url")
                    )
                    servers.append(server)
                
                logger.info(f"Loaded {len(config)} servers from MCP_SERVERS environment variable")
                
            except Exception as e:
                logger.error(f"Error parsing MCP_SERVERS environment variable: {str(e)}")
        
        return servers
    
    async def _load_from_tool_args(self, mcp_servers_config: Any) -> List[MCPServer]:
        """Load server configurations from tool_args."""
        servers = []
        
        if isinstance(mcp_servers_config, dict):
            for name, server_config in mcp_servers_config.items():
                server = MCPServer(
                    name=name,
                    command=server_config.get("command", ""),
                    args=server_config.get("args", []),
                    env=server_config.get("env"),
                    description=server_config.get("description"),
                    transport=server_config.get("transport", "stdio"),
                    url=server_config.get("url")
                )
                servers.append(server)
        
        return servers
    
    async def _load_default_servers(self) -> List[MCPServer]:
        """Load default MCP servers."""
        servers = []
        
        # Add sequential thinking tool as a built-in MCP server
        # This is already implemented as a regular tool, but we can expose it as MCP for consistency
        # servers.append(MCPServer(
        #     name="sequential_thinking",
        #     command="python",
        #     args=["-m", "ii_agent.tools.sequential_thinking_mcp_server"],
        #     description="Sequential thinking tool for complex problem-solving"
        # ))
        
        return servers
    
    async def get_mcp_tools(self) -> List[MCPTool]:
        """Get all MCP tools from connected servers.
        
        Returns:
            List of MCP tools ready for use by the agent
        """
        if not self.initialized:
            await self.initialize()
        
        mcp_tools = []
        all_tool_info = self.server_manager.get_all_tools()
        
        for tool_info in all_tool_info:
            mcp_tool = MCPTool(tool_info, self.server_manager)
            mcp_tools.append(mcp_tool)
        
        return mcp_tools
    
    async def add_server_runtime(self, server: MCPServer) -> bool:
        """Add a server at runtime.
        
        Args:
            server: MCP server configuration
            
        Returns:
            True if server was added successfully
        """
        return await self.server_manager.add_server(server)
    
    async def remove_server_runtime(self, server_name: str):
        """Remove a server at runtime.
        
        Args:
            server_name: Name of the server to remove
        """
        await self.server_manager.remove_server(server_name)
    
    async def get_server_status(self) -> Dict[str, Any]:
        """Get status of all MCP servers.
        
        Returns:
            Dictionary with server status information
        """
        health_status = await self.server_manager.health_check()
        all_tools = self.server_manager.get_all_tools()
        
        server_info = {}
        for server_name in self.server_manager.servers.keys():
            server_tools = self.server_manager.get_server_tools(server_name)
            server_info[server_name] = {
                "healthy": health_status.get(server_name, False),
                "tool_count": len(server_tools),
                "tools": [tool.name for tool in server_tools]
            }
        
        return {
            "total_servers": len(self.server_manager.servers),
            "total_tools": len(all_tools),
            "servers": server_info
        }
    
    async def shutdown(self):
        """Shutdown the MCP registry and all server connections."""
        await self.server_manager.shutdown()
        self.initialized = False