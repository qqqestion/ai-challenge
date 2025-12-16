#!/usr/bin/env python3
"""
GitHub MCP Server (Stub Implementation).

This is a Model Context Protocol server that provides stub tools
for GitHub integration. In the future, these will be connected
to the real GitHub API.
"""

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from tools import (
    get_user,
    get_user_repos,
    get_repo_info,
    search_repos,
    get_repo_issues,
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("github-mcp-server")


# Create server instance
app = Server("github-mcp-server")


# Define available tools
TOOLS = [
    Tool(
        name="get_user",
        description="Get information about a GitHub user",
        inputSchema={
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "GitHub username to look up",
                }
            },
            "required": ["username"],
        },
    ),
    Tool(
        name="get_user_repos",
        description="Get list of repositories for a GitHub user",
        inputSchema={
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "GitHub username",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of repositories to return (default: 10)",
                    "default": 10,
                },
            },
            "required": ["username"],
        },
    ),
    Tool(
        name="get_repo_info",
        description="Get detailed information about a specific repository",
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "Repository owner (username or organization)",
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name",
                },
            },
            "required": ["owner", "repo"],
        },
    ),
    Tool(
        name="search_repos",
        description="Search for GitHub repositories by query",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of results to return (default: 10)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="get_repo_issues",
        description="Get issues for a repository",
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "Repository owner",
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name",
                },
                "state": {
                    "type": "string",
                    "description": "Issue state: open, closed, or all (default: open)",
                    "enum": ["open", "closed", "all"],
                    "default": "open",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of issues to return (default: 10)",
                    "default": 10,
                },
            },
            "required": ["owner", "repo"],
        },
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """
    Handle tool calls.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        Tool result as TextContent
    """
    logger.info(f"Tool called: {name} with arguments: {arguments}")

    try:
        if name == "get_user":
            result = await get_user(arguments["username"])
        elif name == "get_user_repos":
            result = await get_user_repos(
                arguments["username"], arguments.get("limit", 10)
            )
        elif name == "get_repo_info":
            result = await get_repo_info(arguments["owner"], arguments["repo"])
        elif name == "search_repos":
            result = await search_repos(arguments["query"], arguments.get("limit", 10))
        elif name == "get_repo_issues":
            result = await get_repo_issues(
                arguments["owner"],
                arguments["repo"],
                arguments.get("state", "open"),
                arguments.get("limit", 10),
            )
        else:
            raise ValueError(f"Unknown tool: {name}")

        import json

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server."""
    logger.info("Starting GitHub MCP Server (Stub Implementation)")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

