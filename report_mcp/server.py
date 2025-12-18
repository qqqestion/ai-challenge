#!/usr/bin/env python3
"""
Report MCP Server.

Provides tools for creating report files.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

# Add current directory to path for imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from mcp.server import Server  # noqa: E402
from mcp.server.stdio import stdio_server  # noqa: E402
from mcp.types import Tool, TextContent  # noqa: E402

from tools import create_report  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("report-mcp-server")

# Create server instance
app = Server("report-mcp-server")

# Define available tools
TOOLS = [
    Tool(
        name="create_report",
        description="Create a report file with given name, title, and content.",
        inputSchema={
            "type": "object",
            "properties": {
                "report_name": {
                    "type": "string",
                    "description": "Report file name (extension .md will be added if missing).",
                },
                "title": {
                    "type": "string",
                    "description": "Report title (first line of the file).",
                },
                "content": {
                    "type": "string",
                    "description": "Report content placed after an empty line.",
                },
            },
            "required": ["report_name", "title", "content"],
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
    logger.info(f"call_tool() invoked: {name}")
    logger.debug(f"Arguments: {arguments}")

    try:
        if name == "create_report":
            result = await create_report(
                arguments["report_name"],
                arguments["title"],
                arguments["content"],
            )
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=str(result))]

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server."""
    try:
        logger.info("=" * 60)
        logger.info("Starting Report MCP Server")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Server script: {__file__}")
        logger.info(f"Working directory: {Path.cwd()}")
        logger.info("=" * 60)

        async with stdio_server() as (read_stream, write_stream):
            init_options = app.create_initialization_options()
            await app.run(read_stream, write_stream, init_options)

    except Exception as e:
        logger.error(f"Fatal error in main(): {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server crashed: {e}", exc_info=True)
        raise


