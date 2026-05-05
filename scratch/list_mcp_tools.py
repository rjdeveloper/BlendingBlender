import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def list_tools():
    env = os.environ.copy()
    env["DISABLE_TELEMETRY"] = "true"
    server_params = StdioServerParameters(
        command="blender-mcp",
        args=[],
        env=env
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_list = await session.list_tools()
            for tool in tools_list.tools:
                print(f"Tool: {tool.name}")
                print(f"  Description: {tool.description}")
                print(f"  Input Schema: {tool.inputSchema}")

if __name__ == "__main__":
    # Note: Blender must be running with the addon for the bridge to work
    # But we can try to run it anyway to see if the bridge itself lists tools statically
    try:
        asyncio.run(list_tools())
    except Exception as e:
        print(f"Error: {e}")
