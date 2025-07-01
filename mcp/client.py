from fastmcp import Client
import asyncio

# The Client automatically uses StreamableHttpTransport for HTTP URLs
client = Client("http://127.0.0.1:6060/mcp")

async def main():
    async with client:
        tools = await client.list_tools()
        # resources = await client.list_resources()
        # print(f"Available tools: {tools}")

        # print(tools[0])

        result = await client.call_tool("str_replace_editor", {"command": "view", "path": "/home/pvduy/phu/ii-agent/mcp/client.py"})
        print(result)
        result = await client.call_tool("shell_exec", {"session_id": "test_mcp", "command": "ls", "exec_dir": "/home/pvduy/phu/ii-agent/mcp"})
        print(result)

asyncio.run(main())