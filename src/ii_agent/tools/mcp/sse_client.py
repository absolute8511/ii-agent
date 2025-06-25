"""MCP SSE (Server-Sent Events) client implementation."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
import aiohttp

from .base import MCPProtocolClient, MCPServer

logger = logging.getLogger(__name__)


class MCPSSEClient(MCPProtocolClient):
    """MCP client that communicates via Server-Sent Events (SSE)."""
    
    def __init__(self, server_config: MCPServer):
        """Initialize SSE MCP client.
        
        Args:
            server_config: Configuration for the MCP server
        """
        super().__init__(server_config)
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_id_counter = 0
        self.pending_requests: Dict[int, asyncio.Future] = {}
        self.event_source_task: Optional[asyncio.Task] = None
        
    async def connect(self) -> bool:
        """Connect to the MCP server via SSE.
        
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            if not self.server_config.url:
                logger.error(f"No URL provided for SSE MCP server {self.server_config.name}")
                return False
                
            logger.info(f"Connecting to MCP server {self.server_config.name} via SSE at {self.server_config.url}")
            
            # Create HTTP session
            self.session = aiohttp.ClientSession()
            
            # Start event source listener
            self.event_source_task = asyncio.create_task(self._listen_events())
            
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
        try:
            # Cancel event source task
            if self.event_source_task:
                self.event_source_task.cancel()
                try:
                    await self.event_source_task
                except asyncio.CancelledError:
                    pass
                self.event_source_task = None
            
            # Close HTTP session
            if self.session:
                await self.session.close()
                self.session = None
            
            # Cancel pending requests
            for future in self.pending_requests.values():
                if not future.done():
                    future.cancel()
            self.pending_requests.clear()
            
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
        """Send a JSON-RPC request to the MCP server via HTTP POST.
        
        Args:
            method: RPC method name
            params: Method parameters
            
        Returns:
            Response from server or None on error
        """
        if not self.session:
            raise RuntimeError("Session not available")
        
        self.request_id_counter += 1
        request_id = self.request_id_counter
        
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
        
        try:
            # Create future for response
            future = asyncio.Future()
            self.pending_requests[request_id] = future
            
            # Send request via HTTP POST
            async with self.session.post(
                f"{self.server_config.url}/rpc",
                json=request,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    # Response will come via SSE, wait for it
                    result = await asyncio.wait_for(future, timeout=30.0)
                    return result
                else:
                    logger.error(f"HTTP error {response.status} sending request to MCP server")
                    return {"error": {"message": f"HTTP {response.status}"}}
                    
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for response from MCP server")
            return {"error": {"message": "Timeout"}}
        except Exception as e:
            logger.error(f"Error sending request to MCP server: {str(e)}")
            return {"error": {"message": str(e)}}
        finally:
            # Clean up pending request
            self.pending_requests.pop(request_id, None)
    
    async def _send_notification(self, method: str, params: Dict[str, Any]):
        """Send a JSON-RPC notification to the MCP server via HTTP POST.
        
        Args:
            method: RPC method name
            params: Method parameters
        """
        if not self.session:
            raise RuntimeError("Session not available")
        
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        try:
            async with self.session.post(
                f"{self.server_config.url}/rpc",
                json=notification,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    logger.warning(f"HTTP error {response.status} sending notification to MCP server")
                    
        except Exception as e:
            logger.error(f"Error sending notification to MCP server: {str(e)}")
    
    async def _listen_events(self):
        """Listen for Server-Sent Events from the MCP server."""
        if not self.session:
            return
        
        try:
            async with self.session.get(
                f"{self.server_config.url}/events",
                headers={"Accept": "text/event-stream"}
            ) as response:
                if response.status != 200:
                    logger.error(f"HTTP error {response.status} connecting to SSE endpoint")
                    return
                
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # Remove 'data: ' prefix
                        
                        try:
                            data = json.loads(data_str)
                            await self._handle_event(data)
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing SSE data: {str(e)}")
                        except Exception as e:
                            logger.error(f"Error handling SSE event: {str(e)}")
                            
        except asyncio.CancelledError:
            logger.info("SSE event listener cancelled")
        except Exception as e:
            logger.error(f"Error in SSE event listener: {str(e)}")
    
    async def _handle_event(self, data: Dict[str, Any]):
        """Handle an event received via SSE.
        
        Args:
            data: Event data
        """
        # Handle JSON-RPC responses
        if "id" in data and data["id"] in self.pending_requests:
            future = self.pending_requests[data["id"]]
            if not future.done():
                if "error" in data:
                    future.set_result({"error": data["error"]})
                else:
                    future.set_result(data.get("result", {}))
        
        # Handle notifications and other events
        # These could be logged or handled as needed
        elif "method" in data:
            logger.info(f"Received notification from MCP server: {data['method']}")
        else:
            logger.debug(f"Received unknown event from MCP server: {data}")