"""Get tool schema from Notion MCP"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def get_tool_schema():
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "mcp-remote", "https://mcp.notion.com/sse"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            for tool in tools.tools:
                if tool.name == "notion-create-pages":
                    print(f"Tool: {tool.name}")
                    print(f"Description: {tool.description}")
                    print(f"Input Schema: {tool.inputSchema}")


if __name__ == "__main__":
    asyncio.run(get_tool_schema())
