#!/usr/bin/env python3
"""
Diary MCP Server (Stub).

Provides stub tools for future diary/journal integration.
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
    diary_create_record,
    diary_list_pending_todos,
    diary_list_upcoming_events,
    to_json,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("diary-mcp-server")

app = Server("diary-mcp-server")

TOOLS = [
    Tool(
        name="diary_create_record",
        description="Create a diary record: todo / event / note (stored in separate diary.db).",
        inputSchema={
            "type": "object",
            "properties": {
                "entry_type": {
                    "type": "string",
                    "enum": ["todo", "event", "note"],
                    "description": "Record type.",
                },
                "title": {"type": "string", "description": "Optional title."},
                "content": {"type": "string", "description": "Optional content/body."},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags.",
                    "default": [],
                },
                "user_id": {
                    "type": "integer",
                    "description": "Optional user id (default 0).",
                    "default": 0,
                },
                "todo_due_at": {
                    "type": "string",
                    "description": "ISO datetime (UTC preferred). Only for entry_type=todo.",
                },
                "event_start_at": {
                    "type": "string",
                    "description": "ISO datetime (UTC preferred). Required for entry_type=event.",
                },
                "event_end_at": {
                    "type": "string",
                    "description": "ISO datetime (UTC preferred). Optional.",
                },
                "note_occurred_at": {
                    "type": "string",
                    "description": "ISO datetime (UTC preferred). Optional; defaults to now.",
                },
            },
            "required": ["entry_type"],
        },
    ),
    Tool(
        name="diary_list_upcoming_events",
        description="List upcoming events for the next N days (default 7), sorted by start time.",
        inputSchema={
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days ahead.", "default": 7},
                "from_at": {
                    "type": "string",
                    "description": "ISO datetime (UTC preferred). Optional; defaults to now.",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tag filter (matches any of provided tags).",
                    "default": [],
                },
                "user_id": {
                    "type": "integer",
                    "description": "Optional user id (default 0).",
                    "default": 0,
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="diary_list_pending_todos",
        description="List pending (not completed) todo items.",
        inputSchema={
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tag filter (matches any of provided tags).",
                    "default": [],
                },
                "user_id": {
                    "type": "integer",
                    "description": "Optional user id (default 0).",
                    "default": 0,
                },
            },
            "required": [],
        },
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    logger.info("call_tool() invoked: %s", name)
    logger.debug("Arguments: %s", arguments)

    try:
        if name == "diary_create_record":
            result = await diary_create_record(
                entry_type=arguments["entry_type"],
                title=arguments.get("title"),
                content=arguments.get("content"),
                tags=arguments.get("tags") or [],
                user_id=int(arguments.get("user_id") or 0),
                todo_due_at=arguments.get("todo_due_at"),
                event_start_at=arguments.get("event_start_at"),
                event_end_at=arguments.get("event_end_at"),
                note_occurred_at=arguments.get("note_occurred_at"),
            )
        elif name == "diary_list_upcoming_events":
            result = await diary_list_upcoming_events(
                days=int(arguments.get("days") or 7),
                from_at=arguments.get("from_at"),
                tags=arguments.get("tags") or [],
                user_id=int(arguments.get("user_id") or 0),
            )
        elif name == "diary_list_pending_todos":
            result = await diary_list_pending_todos(
                tags=arguments.get("tags") or [],
                user_id=int(arguments.get("user_id") or 0),
            )
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=to_json(result))]
    except Exception as exc:
        logger.error("Error executing tool %s: %s", name, exc, exc_info=True)
        return [TextContent(type="text", text=to_json({"success": False, "error": str(exc)}))]


async def main() -> None:
    try:
        logger.info("=" * 60)
        logger.info("Starting Diary MCP Server (Stub)")
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

