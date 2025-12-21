#!/usr/bin/env python3
"""
Android MCP Server.

Provides tools to control an Android emulator/device:
- open_deeplink
- open_app
- kill_app
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

from tools import kill_app, open_app, open_deeplink  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("android-mcp-server")

# Create server instance
app = Server("android-mcp-server")

# Define available tools
TOOLS = [
    Tool(
        name="open_deeplink",
        description="Open a deeplink on the connected Android device/emulator.",
        inputSchema={
            "type": "object",
            "properties": {
                "deeplink": {
                    "type": "string",
                    "description": "Full deeplink URI to open.",
                },
                "package_name": {
                    "type": "string",
                    "description": "Optional target package to handle the deeplink.",
                },
            },
            "required": ["deeplink"],
        },
    ),
    Tool(
        name="open_app",
        description="Launch an Android application.",
        inputSchema={
            "type": "object",
            "properties": {
                "package_name": {
                    "type": "string",
                    "description": "Application package name.",
                },
                "activity": {
                    "type": "string",
                    "description": "Optional activity (e.g., .MainActivity or pkg/.Activity).",
                },
                "use_monkey": {
                    "type": "boolean",
                    "description": "If true and activity is absent, use monkey to launch.",
                    "default": False,
                },
            },
            "required": ["package_name"],
        },
    ),
    Tool(
        name="kill_app",
        description="Force-stop an Android application.",
        inputSchema={
            "type": "object",
            "properties": {
                "package_name": {
                    "type": "string",
                    "description": "Application package name.",
                },
            },
            "required": ["package_name"],
        },
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    logger.debug("list_tools() called, returning %s tools", len(TOOLS))
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    logger.info("call_tool() invoked: %s", name)
    logger.debug("Arguments: %s", arguments)

    try:
        if name == "open_deeplink":
            result = await open_deeplink(
                arguments["deeplink"],
                arguments.get("package_name"),
            )
        elif name == "open_app":
            result = await open_app(
                arguments["package_name"],
                arguments.get("activity"),
                arguments.get("use_monkey", False),
            )
        elif name == "kill_app":
            result = await kill_app(arguments["package_name"])
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=str(result))]

    except Exception as e:
        logger.error("Error executing tool %s: %s", name, e, exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server."""
    try:
        logger.info("=" * 60)
        logger.info("Starting Android MCP Server")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Server script: {__file__}")
        logger.info(f"Working directory: {Path.cwd()}")
        logger.info("=" * 60)

        async with stdio_server() as (read_stream, write_stream):
            init_options = app.create_initialization_options()
            await app.run(read_stream, write_stream, init_options)

    except Exception as e:
        logger.error("Fatal error in main(): %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server crashed: {e}", exc_info=True)
        raise


