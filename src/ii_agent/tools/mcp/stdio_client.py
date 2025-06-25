"""MCP STDIO client implementation."""

import asyncio
import json
import logging
import subprocess
from typing import Any, Dict, List, Optional
import uuid

from .base import MCPProtocolClient, MCPServer

logger = logging.getLogger(__name__)


class MCPStdioClient(MCPProtocolClient):
    """MCP client that communicates via STDIO with subprocess."""
    
    def __init__(self, server_config: MCPServer):
        """Initialize STDIO MCP client.
        
        Args:
            server_config: Configuration for the MCP server
        """
        super().__init__(server_config)
        self.process: Optional[subprocess.Popen] = None
        self.read_lock = asyncio.Lock()
        self.write_lock = asyncio.Lock()
        self.request_id_counter = 0
        
    async def connect(self) -> bool:
        """Connect to the MCP server via STDIO subprocess.
        
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            logger.info(f"Connecting to MCP server {self.server_config.name} via STDIO")
            
            # Prepare command and environment
            command = [self.server_config.command] + self.server_config.args
            env = dict(self.server_config.env or {})
            
            # Start the subprocess
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                bufsize=0  # Unbuffered for real-time communication
            )
            
            # Initialize the MCP connection
            init_result = await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "prompts": {}
                },
                "clientInfo": {
                    "name": "ii-agent",
                    "version": "1.0.0"
                }
            })
            
            if init_result and not init_result.get("error"):
                # Send initialized notification
                await self._send_notification("notifications/initialized", {})
                
                self.connected = True
                logger.info(f"Successfully connected to MCP server {self.server_config.name}")
                return True
            else:
                logger.error(f"Failed to initialize MCP server {self.server_config.name}: {init_result}")
                await self.disconnect()
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to MCP server {self.server_config.name}: {str(e)}")
            await self.disconnect()
            return False
    
    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.sleep(0.1)
                if self.process.poll() is None:
                    self.process.kill()
                self.process = None
            except Exception as e:
                logger.error(f"Error disconnecting from MCP server: {str(e)}")
        
        self.connected = False
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the MCP server.
        
        Returns:
            List of tool definitions
        """
        if not self.connected:
            raise RuntimeError("Not connected to MCP server")
        
        try:
            result = await self._send_request("tools/list", {})
            
            if result and not result.get("error"):
                return result.get("tools", [])
            else:
                logger.error(f"Error listing tools: {result}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing tools from MCP server: {str(e)}")
            return []
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        if not self.connected:
            raise RuntimeError("Not connected to MCP server")
        
        try:
            result = await self._send_request("tools/call", {
                "name": name,
                "arguments": arguments
            })
            
            if result and not result.get("error"):
                return result.get("content", [])
            else:
                error_msg = result.get("error", {}).get("message", "Unknown error") if result else "No response"
                logger.error(f"Error calling tool {name}: {error_msg}")
                return {"isError": True, "content": error_msg}
                
        except Exception as e:
            logger.error(f"Error calling tool {name} on MCP server: {str(e)}")
            return {"isError": True, "content": str(e)}
    
    async def list_prompts(self) -> List[Dict[str, Any]]:
        """List available prompts from the MCP server.
        
        Returns:
            List of prompt definitions
        """
        if not self.connected:
            raise RuntimeError("Not connected to MCP server")
        
        try:
            result = await self._send_request("prompts/list", {})
            
            if result and not result.get("error"):
                return result.get("prompts", [])
            else:
                logger.error(f"Error listing prompts: {result}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing prompts from MCP server: {str(e)}")
            return []
    
    async def _send_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a JSON-RPC request to the MCP server.
        
        Args:
            method: RPC method name
            params: Method parameters
            
        Returns:
            Response from server or None on error
        """
        if not self.process or not self.process.stdin:
            raise RuntimeError("Process not available")
        
        self.request_id_counter += 1
        request_id = self.request_id_counter
        
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
        
        try:
            async with self.write_lock:
                # Send request
                request_json = json.dumps(request) + "\n"
                self.process.stdin.write(request_json)
                self.process.stdin.flush()
            
            # Read response
            async with self.read_lock:
                response_line = await self._read_line()
                if response_line:
                    response = json.loads(response_line.strip())
                    
                    # Check if this is the response to our request
                    if response.get("id") == request_id:
                        if "error" in response:
                            return {"error": response["error"]}
                        else:
                            return response.get("result", {})
                    else:
                        logger.warning(f"Received response with wrong ID: expected {request_id}, got {response.get('id')}")
                        return None
                else:
                    logger.error("No response received from MCP server")
                    return None
                    
        except Exception as e:
            logger.error(f"Error sending request to MCP server: {str(e)}")
            return None
    
    async def _send_notification(self, method: str, params: Dict[str, Any]):
        """Send a JSON-RPC notification to the MCP server.
        
        Args:
            method: RPC method name
            params: Method parameters
        """
        if not self.process or not self.process.stdin:
            raise RuntimeError("Process not available")
        
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        try:
            async with self.write_lock:
                notification_json = json.dumps(notification) + "\n"
                self.process.stdin.write(notification_json)
                self.process.stdin.flush()
                
        except Exception as e:
            logger.error(f"Error sending notification to MCP server: {str(e)}")
    
    async def _read_line(self) -> Optional[str]:
        """Read a line from the server's stdout.
        
        Returns:
            Line from server or None on error/timeout
        """
        if not self.process or not self.process.stdout:
            return None
        
        try:
            # Use asyncio to read with timeout
            loop = asyncio.get_event_loop()
            line = await asyncio.wait_for(
                loop.run_in_executor(None, self.process.stdout.readline),
                timeout=30.0  # 30 second timeout
            )
            return line if line else None
            
        except asyncio.TimeoutError:
            logger.error("Timeout reading from MCP server")
            return None
        except Exception as e:
            logger.error(f"Error reading from MCP server: {str(e)}")
            return None