#!/usr/bin/env python3
"""
Git MCP Server.

Provides tools to inspect local git repository state.
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

from mcp.server import Server  # noqa: E402
from mcp.server.stdio import stdio_server  # noqa: E402
from mcp.types import Tool, TextContent  # noqa: E402

from tools import get_current_branch, list_branches, to_json  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("git-mcp-server")

# Create server instance
app = Server("git-mcp-server")

# Define available tools
TOOLS = [
    Tool(
        name="get_current_branch",
        description="Get current branch name for the repository (default: project root).",
        inputSchema={
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to the git repository. Defaults to project root.",
                },
            },
        },
    ),
    Tool(
        name="list_branches",
        description="List local branches for the repository (default: project root).",
        inputSchema={
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to the git repository. Defaults to project root.",
                },
            },
        },
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    logger.debug("list_tools() called")
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """
    Handle tool calls.
    """
    logger.info("call_tool() invoked: %s", name)
    logger.debug("Arguments: %s", arguments)

    try:
        if name == "get_current_branch":
            result = await get_current_branch(arguments.get("repo_path"))
        elif name == "list_branches":
            result = await list_branches(arguments.get("repo_path"))
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=to_json(result))]
    except Exception as exc:
        logger.error("Error executing tool %s: %s", name, exc, exc_info=True)
        return [
            TextContent(
                type="text",
                text=to_json({"success": False, "error": str(exc)}),
            )
        ]


async def main():
    """Run the MCP server."""
    try:
        logger.info("=" * 60)
        logger.info("Starting Git MCP Server")
        logger.info("Python version: %s", sys.version)
        logger.info("Server script: %s", __file__)
        logger.info("Working directory: %s", Path.cwd())
        logger.info("=" * 60)

        async with stdio_server() as (read_stream, write_stream):
            init_options = app.create_initialization_options()
            await app.run(read_stream, write_stream, init_options)
    except Exception as exc:
        logger.error("Fatal error in main(): %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as exc:
        logger.error("Server crashed: %s", exc, exc_info=True)
        raise

