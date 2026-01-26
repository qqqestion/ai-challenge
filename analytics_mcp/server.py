#!/usr/bin/env python3
"""
Analytics MCP Server.

Provides tools for searching local analytics digest JSON via grep-like interface.
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

from tools import grep  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("analytics-mcp-server")

# Create server instance
app = Server("analytics-mcp-server")

TOOLS = [
    Tool(
        name="grep",
        description=(
            "Grep-like search over user analytics events file. User already specified, no id needed. "
            "Returns matching lines, optionally with context and line numbers."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Search pattern."},
                "ignore_case": {
                    "type": "boolean",
                    "description": "Case-insensitive search (like grep -i).",
                    "default": False,
                },
                "regex": {
                    "type": "boolean",
                    "description": "Treat pattern as a regular expression.",
                    "default": False,
                },
                "line_numbers": {
                    "type": "boolean",
                    "description": "Include line numbers (like grep -n).",
                    "default": True,
                },
                "max_matches": {
                    "type": "integer",
                    "description": "Maximum number of matched lines to return.",
                    "default": 50,
                    "minimum": 1,
                },
                "before_context": {
                    "type": "integer",
                    "description": "Lines of context before each match (like grep -B).",
                    "default": 0,
                    "minimum": 0,
                },
                "after_context": {
                    "type": "integer",
                    "description": "Lines of context after each match (like grep -A).",
                    "default": 0,
                    "minimum": 0,
                },
            },
            "required": ["pattern"],
        },
    )
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    logger.debug("list_tools() called")
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    logger.info("call_tool() invoked: %s", name)
    logger.debug("Arguments: %s", arguments)

    try:
        if name != "grep":
            raise ValueError(f"Unknown tool: {name}")

        result = await grep(
            pattern=arguments["pattern"],
            ignore_case=arguments.get("ignore_case", False),
            regex=arguments.get("regex", False),
            line_numbers=arguments.get("line_numbers", True),
            max_matches=arguments.get("max_matches", 50),
            before_context=arguments.get("before_context", 0),
            after_context=arguments.get("after_context", 0),
        )
        return [TextContent(type="text", text=result)]
    except Exception as exc:
        logger.error("Error executing tool %s: %s", name, exc, exc_info=True)
        return [TextContent(type="text", text=f"Error: {exc}")]


async def main() -> None:
    """Run the MCP server."""
    try:
        logger.info("=" * 60)
        logger.info("Starting Analytics MCP Server")
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

