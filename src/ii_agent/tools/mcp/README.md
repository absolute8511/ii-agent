# MCP (Model Context Protocol) Integration

This module provides MCP server integration for ii-agent, allowing the agent to discover and use tools from MCP servers dynamically.

## Overview

The MCP integration enables ii-agent to:
- Connect to local and remote MCP servers
- Automatically discover available tools
- Execute tools through the MCP protocol
- Support both STDIO and SSE transport protocols
- Handle tool schema translation between MCP and ii-agent formats

## Configuration

### 1. Enable MCP in tool_args

```python
tool_args = {
    "mcp": True,
    "mcp_servers": {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"],
            "description": "File system access"
        }
    }
}
```

### 2. Using .mcprc Configuration File

Create a `.mcprc` file in your workspace or home directory:

```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/directory"],
    "description": "Provides file system access",
    "transport": "stdio"
  },
  "git": {
    "command": "npx", 
    "args": ["-y", "@modelcontextprotocol/server-git"],
    "description": "Git repository operations",
    "transport": "stdio"
  }
}
```

### 3. Environment Variables

Set the `MCP_SERVERS` environment variable:

```bash
export MCP_SERVERS='{"filesystem": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]}}'
```

## Supported Transport Protocols

### STDIO Transport
- Default protocol for most MCP servers
- Communicates via subprocess stdin/stdout
- Suitable for local command-line tools

### SSE (Server-Sent Events) Transport
- For remote MCP servers over HTTP
- Requires server URL configuration
- Useful for web-based MCP services

## Server Configuration Options

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | string | Yes (STDIO) | Command to execute for STDIO servers |
| `args` | array | No | Command line arguments |
| `env` | object | No | Environment variables |
| `description` | string | No | Human-readable description |
| `transport` | string | No | "stdio" (default) or "sse" |
| `url` | string | Yes (SSE) | URL for SSE servers |

## Example MCP Servers

### Official MCP Servers

```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
    "description": "File system operations"
  },
  "git": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-git"],
    "description": "Git operations"
  },
  "sqlite": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-sqlite", "database.db"],
    "description": "SQLite database access"
  },
  "brave_search": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
    "env": {
      "BRAVE_API_KEY": "your-api-key"
    },
    "description": "Web search via Brave"
  }
}
```

### Custom Python MCP Server

```json
{
  "custom_tool": {
    "command": "python",
    "args": ["-m", "my_project.mcp_server"],
    "env": {
      "API_KEY": "secret-key"
    },
    "description": "Custom tool implementation"
  }
}
```

## Usage in FunctionCallAgent

Once configured, MCP tools are automatically available to the FunctionCallAgent:

```python
from ii_agent.agents.function_call import FunctionCallAgent

# Enable MCP in tool configuration
tool_args = {"mcp": True}

# Create agent with MCP tools
agent = FunctionCallAgent(
    # ... other parameters
    tools=get_system_tools(client, workspace_manager, message_queue, tool_args)
)

# MCP tools are now available alongside built-in tools
```

## Troubleshooting

### Common Issues

1. **MCP servers not starting**: Check that the command and arguments are correct
2. **Permission errors**: Ensure the MCP server has necessary permissions
3. **Network issues**: For SSE servers, verify the URL is accessible
4. **Schema errors**: Check that tool schemas are valid JSON Schema

### Debugging

Enable debug logging:

```python
import logging
logging.getLogger('ii_agent.tools.mcp').setLevel(logging.DEBUG)
```

### Status Checking

Use the MCP registry to check server status:

```python
from ii_agent.tools.mcp import MCPRegistry

registry = MCPRegistry()
await registry.initialize()
status = await registry.get_server_status()
print(status)
```

## Architecture

```
FunctionCallAgent
    ↓
AgentToolManager
    ↓
get_system_tools()
    ↓
MCPRegistry
    ↓
MCPServerManager
    ↓
MCPProtocolClient (STDIO/SSE)
    ↓
MCP Server Process/Remote Server
```

## Security Considerations

- MCP servers run as separate processes with their own permissions
- File system access is limited to configured directories
- Environment variables should not contain sensitive data in logs
- Remote MCP servers should use secure connections (HTTPS)

## Contributing

To add support for new transport protocols or extend MCP functionality:

1. Implement new client in `mcp/` directory
2. Add transport option to `MCPServerManager`
3. Update schema translation if needed
4. Add tests and documentation