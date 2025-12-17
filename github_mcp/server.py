#!/usr/bin/env python3
"""
GitHub MCP Server (Real Implementation).

This is a Model Context Protocol server that provides tools
for GitHub integration using GitHub REST API.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

# Add current directory to path for imports (must be before other imports)
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# MCP and local imports (after sys.path modification)
from mcp.server import Server  # noqa: E402
from mcp.server.stdio import stdio_server  # noqa: E402
from mcp.types import Tool, TextContent  # noqa: E402

from tools import (  # noqa: E402
    get_user,
    get_user_repos,
    get_repo_info,
    get_user_events,
    get_repo_events,
)


# Configure logging with more verbose output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
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
        name="get_user_events",
        description="Get list of events for a GitHub user",
        inputSchema={
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "GitHub username",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of events to return (default: 30, max: 100)",
                    "default": 30,
                },
            },
            "required": ["username"],
        },
    ),
    Tool(
        name="get_repo_events",
        description="Get list of events for a GitHub repository",
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
                "limit": {
                    "type": "number",
                    "description": "Maximum number of events to return (default: 30, max: 100)",
                    "default": 30,
                },
            },
            "required": ["owner", "repo"],
        },
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    logger.debug(f"list_tools() called, returning {len(TOOLS)} tools")
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
    logger.info(f"call_tool() invoked: {name}")
    logger.debug(f"Arguments: {arguments}")

    try:
        logger.debug(f"Executing tool: {name}")

        if name == "get_user":
            result = await get_user(arguments["username"])
        elif name == "get_user_repos":
            result = await get_user_repos(
                arguments["username"], arguments.get("limit", 10)
            )
        elif name == "get_repo_info":
            result = await get_repo_info(arguments["owner"], arguments["repo"])
        elif name == "get_user_events":
            result = await get_user_events(
                arguments["username"], arguments.get("limit", 30)
            )
        elif name == "get_repo_events":
            result = await get_repo_events(
                arguments["owner"], arguments["repo"], arguments.get("limit", 30)
            )
        else:
            logger.error(f"Unknown tool requested: {name}")
            raise ValueError(f"Unknown tool: {name}")

        import json

        logger.debug(f"Tool {name} executed successfully")
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server."""
    try:
        logger.info("=" * 60)
        logger.info("Starting GitHub MCP Server (Real Implementation)")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Server script: {__file__}")
        logger.info(f"Working directory: {Path.cwd()}")
        logger.info("=" * 60)

        logger.debug("Creating stdio_server context...")
        async with stdio_server() as (read_stream, write_stream):
            logger.debug("stdio_server context created successfully")
            logger.debug(f"Read stream: {read_stream}")
            logger.debug(f"Write stream: {write_stream}")

            logger.info("Initializing MCP server application...")
            init_options = app.create_initialization_options()
            logger.debug(f"Initialization options: {init_options}")

            logger.info("Starting app.run()...")
            await app.run(read_stream, write_stream, init_options)

            logger.info("Server stopped gracefully")

    except Exception as e:
        logger.error(f"Fatal error in main(): {e}", exc_info=True)
        raise


if __name__ == "__main__":
    logger.debug("Script started as __main__")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server crashed: {e}", exc_info=True)
        raise
