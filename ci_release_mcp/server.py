#!/usr/bin/env python3
"""
CI Release MCP Server.

Provides tools to create release branches, run tests, and start the server for a
hardcoded repository path.
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

from tools import (  # noqa: E402
    create_release_branch,
    run_tests_on_release_branch,
    start_server_on_release_branch,
    to_json,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ci-release-mcp-server")

app = Server("ci-release-mcp-server")

TOOLS = [
    Tool(
        name="ci_release_create_branch",
        description="Create (or reset) release/<version> branch in ai-challenge-server repo.",
        inputSchema={
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "description": "Release version, used in branch name release/<version>.",
                }
            },
            "required": ["version"],
        },
    ),
    Tool(
        name="ci_release_run_tests",
        description="Checkout release/<version> and run `python manage.py test` with repo environment.",
        inputSchema={
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "description": "Release version, used in branch name release/<version>.",
                }
            },
            "required": ["version"],
        },
    ),
    Tool(
        name="ci_release_start_server",
        description="Checkout release/<version> and run stub server start script (hardcoded path).",
        inputSchema={
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "description": "Release version, used in branch name release/<version>.",
                }
            },
            "required": ["version"],
        },
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    logger.info("call_tool() invoked: %s", name)
    logger.debug("Arguments: %s", arguments)

    try:
        if name == "ci_release_create_branch":
            result = await create_release_branch(arguments["version"])
        elif name == "ci_release_run_tests":
            result = await run_tests_on_release_branch(arguments["version"])
        elif name == "ci_release_start_server":
            result = await start_server_on_release_branch(arguments["version"])
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
        logger.info("Starting CI Release MCP Server")
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


