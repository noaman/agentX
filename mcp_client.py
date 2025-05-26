from mcp.client.stdio import stdio_client
from mcp.types import Tool as MCPTool
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters,Tool,CallToolRequest
from typing import Any, List
import asyncio
import logging
import shutil
import json
import os
from mcp.client.sse import sse_client




logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
)

class MCPServer:
    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name = name
        self.config = config


class MCPCLient:

    def __init__(self):
        """Initialize the MCP client"""
        self.servers = []
        self.config = {}

    def load_servers(self, config_path: str) -> None:
        """Load server configuration from a JSON file (typically mcp_config.json)
        and creates an instance of each server (no active connection until 'start' though).

        Args:
            config_path: Path to the JSON configuration file.
        """
        with open(config_path, "r") as config_file:
            self.config = json.load(config_file)

        self.servers = [MCPServer(name, config) for name, config in self.config["mcpServers"].items()]


    def load_single_server(self, server_name: str, config: dict[str, Any]):
        self.servers=[]
        self.servers.append(MCPServer(server_name, config))
        

    async def get_tools_json(self, server: MCPServer):
        tools = await self.load_all_tools(server)

        return tools

    async def load_all_tools(self):
        mcp_tools = {}
        for server in self.servers:
            print(f"Loading tools for server: {server.name}")
            all_tools = []
            command = server.config["command"]
            if "args" in server.config:
                args = server.config["args"]
            else:
                args = []

            if "env" in server.config:
                env = server.config["env"]
            else:
                env = None

            if command == "remote":
                tools_sse = await self.load_tools_sse(server.config["end_point"])
                all_tools=tools_sse
            elif command in ["npx", "uvx","uv","python3"]:
                server_params = StdioServerParameters(
                    command=command,
                    args=args,
                    env=env
                )
                async with AsyncExitStack() as exit_stack:
                    stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
                    stdio, write = stdio_transport
                    session = await exit_stack.enter_async_context(ClientSession(stdio, write))
                    await session.initialize()
                    # List available tools
                    response = await session.list_tools()
                    available_tools = [{
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema
                    } for tool in response.tools]
                    all_tools = available_tools

            mcp_tools[server.name] = all_tools

        return mcp_tools

    async def call_tool(self, server_name: str, tool_name: str, input_data: dict[str, Any]) -> Any:

        server = next((s for s in self.servers if s.name == server_name), None)
        if not server:
            raise ValueError(f"Server {server_name} not found")

        command = server.config["command"]
        if command == "remote":
            async with sse_client(server.config["end_point"]) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    await session.send_ping()
                    result =  await session.call_tool(tool_name, input_data)
                    return result



        elif command in ["npx", "uvx","uv","python3"]:
            server_params = StdioServerParameters(
                command=command,
                args=server.config.get("args", []),
                env=server.config.get("env")
            )
            async with AsyncExitStack() as exit_stack:
                stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
                stdio, write = stdio_transport
                session = await exit_stack.enter_async_context(ClientSession(stdio, write))
                await session.initialize()
                result =  await session.call_tool(tool_name, input_data)
                return result



        else:
            raise ValueError(f"Unsupported server command: {command}")


    async def load_tools_sse(self, url):
        async with sse_client(url=url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await session.send_ping()
                response = await session.list_tools()

                available_tools = [{
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                } for tool in response.tools]
                
                return available_tools
        return []
    
    # def test_single_tool(server_name: str, tool_name: str, input_data: dict[str, Any]):
    #     mcp_client = MCPCLient()
    #     mcp_client.load_servers("config/mcp_config.json")
    #     result = await mcp_client.call_tool(server_name, tool_name, input_data)
    #     print(result)