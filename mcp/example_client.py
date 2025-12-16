#!/usr/bin/env python3
"""
Example MCP client demonstrating programmatic integration.

This script shows how to:
1. Connect to a local MCP server
2. List available tools
3. Call tools with arguments
4. Use results in AI applications
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def connect_to_mcp_server() -> tuple:
    """
    Connect to local MCP server.

    Returns:
        Tuple of (ClientSession, transport)
    """
    print("🔌 Connecting to MCP server...")

    # Server parameters
    server_params = StdioServerParameters(
        command="python",
        args=[str(Path(__file__).parent / "server.py")],
        env=None,
    )

    # Create client and connect
    stdio_transport = await stdio_client(server_params)
    stdio, write = stdio_transport

    session = ClientSession(stdio, write)
    await session.initialize()

    print("✅ Connected to MCP server")
    return session, stdio_transport


async def list_available_tools(session: ClientSession) -> List[Dict[str, Any]]:
    """
    Get list of available MCP tools.

    Args:
        session: Active MCP session

    Returns:
        List of tool definitions
    """
    print("\n📋 Fetching available tools...")

    tools_result = await session.list_tools()

    tools = []
    for tool in tools_result.tools:
        tools.append(
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
        )

    print(f"✅ Found {len(tools)} tools")
    return tools


async def call_mcp_tool(
    session: ClientSession, tool_name: str, arguments: Dict[str, Any]
) -> str:
    """
    Call an MCP tool.

    Args:
        session: Active MCP session
        tool_name: Name of the tool to call
        arguments: Tool arguments

    Returns:
        Tool result as JSON string
    """
    print(f"\n🔧 Calling tool '{tool_name}' with arguments: {arguments}")

    result = await session.call_tool(tool_name, arguments)

    # Result is returned as list of TextContent
    if result.content:
        output = result.content[0].text
        print(f"✅ Tool executed successfully")
        return output

    return ""


async def demo_tools(session: ClientSession):
    """
    Demonstrate all available tools.

    Args:
        session: Active MCP session
    """
    print("\n" + "=" * 60)
    print("🎯 DEMO: Testing all available tools")
    print("=" * 60)

    # Demo 1: get_user
    print("\n📌 Demo 1: Get user information")
    result = await call_mcp_tool(session, "get_user", {"username": "octocat"})
    data = json.loads(result)
    print(f"   User: {data['login']}")
    print(f"   Name: {data['name']}")
    print(f"   Repos: {data['public_repos']}")
    print(f"   Followers: {data['followers']}")

    # Demo 2: get_user_repos
    print("\n📌 Demo 2: Get user repositories")
    result = await call_mcp_tool(
        session, "get_user_repos", {"username": "octocat", "limit": 3}
    )
    data = json.loads(result)
    print(f"   Total repos: {data['total_count']}")
    for repo in data["repositories"]:
        print(f"   - {repo['name']} ({repo['language']}) ⭐ {repo['stars']}")

    # Demo 3: get_repo_info
    print("\n📌 Demo 3: Get repository information")
    result = await call_mcp_tool(
        session, "get_repo_info", {"owner": "octocat", "repo": "Hello-World"}
    )
    data = json.loads(result)
    print(f"   Repository: {data['full_name']}")
    print(f"   Description: {data['description']}")
    print(f"   Stars: {data['stars']}")
    print(f"   Language: {data['language']}")

    # Demo 4: search_repos
    print("\n📌 Demo 4: Search repositories")
    result = await call_mcp_tool(
        session, "search_repos", {"query": "telegram bot", "limit": 3}
    )
    data = json.loads(result)
    print(f"   Query: '{data['query']}'")
    print(f"   Results: {data['total_count']}")
    for repo in data["items"]:
        print(f"   - {repo['name']} ⭐ {repo['stars']}")

    # Demo 5: get_repo_issues
    print("\n📌 Demo 5: Get repository issues")
    result = await call_mcp_tool(
        session,
        "get_repo_issues",
        {"owner": "octocat", "repo": "Hello-World", "state": "open", "limit": 3},
    )
    data = json.loads(result)
    print(f"   Repository: {data['owner']}/{data['repo']}")
    print(f"   State: {data['state']}")
    print(f"   Total issues: {data['total_count']}")
    for issue in data["issues"]:
        print(f"   - #{issue['number']}: {issue['title']}")


async def main():
    """Main function demonstrating MCP client usage."""
    print("=" * 60)
    print("🚀 MCP Client Example")
    print("=" * 60)

    session = None
    try:
        # Connect to MCP server
        session, transport = await connect_to_mcp_server()

        # List available tools
        tools = await list_available_tools(session)

        print("\n📚 Available tools:")
        for tool in tools:
            print(f"   - {tool['name']}: {tool['description']}")

        # Run demos
        await demo_tools(session)

        print("\n" + "=" * 60)
        print("✅ All demos completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        if session:
            print("\n🔌 Closing connection...")
            await session.__aexit__(None, None, None)
            print("✅ Connection closed")


if __name__ == "__main__":
    asyncio.run(main())

