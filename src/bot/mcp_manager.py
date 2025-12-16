"""MCP (Model Context Protocol) Manager for tool integration."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..config import get_logger

logger = get_logger(__name__)


class MCPManager:
    """Manager for MCP server connection and tool execution."""

    def __init__(self, server_script_path: Optional[str] = None):
        """Initialize MCP Manager.

        Args:
            server_script_path: Path to MCP server script (default: github_mcp/server.py)
        """
        self.server_script_path = server_script_path or str(
            Path(__file__).parent.parent.parent / "github_mcp" / "server.py"
        )
        self.session: Optional[ClientSession] = None
        self.transport = None
        self.read_stream = None
        self.write_stream = None
        self.tools: List[Dict[str, Any]] = []
        self._initialized = False
        logger.info(f"MCPManager created with server path: {self.server_script_path}")

    async def initialize(self) -> bool:
        """Initialize MCP connection and load tools.

        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            logger.warning("MCPManager already initialized")
            return True

        try:
            logger.info("=" * 60)
            logger.info("Initializing MCP server connection...")
            logger.info(f"Server script: {self.server_script_path}")

            # Server parameters - use current Python interpreter to ensure venv is used
            python_executable = sys.executable
            logger.info(f"Using Python interpreter: {python_executable}")

            server_params = StdioServerParameters(
                command=python_executable,
                args=[self.server_script_path],
                env=None,
            )
            logger.debug(f"Server parameters: command={server_params.command}, args={server_params.args}")

            # Create client and connect using async context manager
            # IMPORTANT: We keep the context open by storing the context manager
            logger.debug("Creating stdio_client...")
            self.transport = stdio_client(server_params)
            
            logger.debug("Entering stdio_transport context...")
            self.read_stream, self.write_stream = await self.transport.__aenter__()
            logger.debug(f"stdio_transport context entered successfully")
            logger.debug(f"Read stream type: {type(self.read_stream)}")
            logger.debug(f"Write stream type: {type(self.write_stream)}")

            logger.debug("Creating ClientSession...")
            self.session = ClientSession(self.read_stream, self.write_stream)
            logger.debug("ClientSession created")
            
            # Enter session context
            logger.debug("Entering session context...")
            await self.session.__aenter__()
            logger.debug("Session context entered")
            
            logger.debug("Initializing session (15s timeout)...")
            await asyncio.wait_for(
                self.session.initialize(),
                timeout=15.0
            )
            logger.debug("Session initialized successfully")

            logger.info("✓ Connected to MCP server")

            # Load available tools
            logger.debug("Loading tools (5s timeout)...")
            await asyncio.wait_for(
                self._load_tools(),
                timeout=5.0
            )

            self._initialized = True
            logger.info(f"✓ MCPManager initialized with {len(self.tools)} tools")
            logger.info("=" * 60)
            return True

        except asyncio.TimeoutError as e:
            logger.error("=" * 60)
            logger.error("MCP initialization TIMEOUT")
            logger.error("The MCP server did not respond in time.")
            logger.error("This could mean:")
            logger.error("  1. Server is hanging during initialization")
            logger.error("  2. Import errors in server.py or tools.py")
            logger.error("  3. Server process failed to start")
            logger.error("=" * 60)
            logger.error(f"Timeout details: {e}", exc_info=True)
            
            # Cleanup on failure
            await self._cleanup_on_error()
            return False
            
        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"Failed to initialize MCP server: {e}")
            logger.error("=" * 60)
            logger.error("Full traceback:", exc_info=True)
            
            # Cleanup on failure
            await self._cleanup_on_error()
            return False
    
    async def _cleanup_on_error(self):
        """Cleanup resources after initialization error."""
        try:
            if self.session:
                try:
                    await asyncio.wait_for(
                        self.session.__aexit__(None, None, None),
                        timeout=1.0
                    )
                except:
                    pass
            
            if self.transport:
                try:
                    await asyncio.wait_for(
                        self.transport.__aexit__(None, None, None),
                        timeout=1.0
                    )
                except:
                    pass
        finally:
            self.session = None
            self.transport = None
            self.read_stream = None
            self.write_stream = None

    async def _load_tools(self):
        """Load available tools from MCP server."""
        if not self.session:
            logger.error("Cannot load tools: session not initialized")
            return

        try:
            logger.debug("Calling session.list_tools()...")
            tools_result = await self.session.list_tools()
            logger.debug(f"list_tools() returned: {tools_result}")

            self.tools = []
            for tool in tools_result.tools:
                tool_info = {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                }
                self.tools.append(tool_info)
                logger.debug(f"Loaded tool: {tool.name}")

            logger.info(f"✓ Loaded {len(self.tools)} tools from MCP server")

        except Exception as e:
            logger.error(f"Failed to load tools: {e}", exc_info=True)
            self.tools = []

    def get_tools_description(self) -> str:
        """Get formatted description of available tools for LLM prompt.

        Returns:
            Formatted string describing all available tools
        """
        if not self.tools:
            return ""

        lines = ["Available GitHub tools:"]
        for i, tool in enumerate(self.tools, 1):
            name = tool["name"]
            description = tool["description"]
            schema = tool.get("input_schema", {})
            properties = schema.get("properties", {})
            required = schema.get("required", [])

            # Build parameter list
            params = []
            for param_name, param_info in properties.items():
                param_type = param_info.get("type", "any")
                param_desc = param_info.get("description", "")
                is_required = param_name in required
                req_marker = " (required)" if is_required else " (optional)"
                params.append(f"  - {param_name}: {param_type}{req_marker} - {param_desc}")

            tool_desc = f"{i}. {name}() - {description}"
            if params:
                tool_desc += "\n" + "\n".join(params)

            lines.append(tool_desc)

        return "\n".join(lines)

    def get_tool_call_format(self) -> str:
        """Get instructions for LLM on how to call tools.

        Returns:
            Formatted string with tool calling instructions
        """
        return """
To use a tool, respond with JSON in this format:
{
  "tool_call": {
    "name": "tool_name",
    "arguments": {"arg1": "value1", "arg2": "value2"}
  },
  "reasoning": "Brief explanation why you need this tool"
}

After receiving tool results, you can either:
- Call another tool if needed (same JSON format)
- Provide final answer to user in natural language

Important:
- You can call maximum 3 tools per user message
- If tool is not needed, just respond normally without JSON
- Tool results will be provided as context for your next response
"""

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Call an MCP tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments as dictionary
            timeout: Timeout in seconds

        Returns:
            Dictionary with tool result:
            {
                "success": bool,
                "result": str or dict,
                "error": str (if failed)
            }
        """
        if not self.session:
            return {
                "success": False,
                "error": "MCP session not initialized"
            }

        logger.info(f"Calling MCP tool: {tool_name} with arguments: {arguments}")

        try:
            # Call tool with timeout
            result = await asyncio.wait_for(
                self.session.call_tool(tool_name, arguments),
                timeout=timeout
            )

            # Extract result text
            if result.content:
                result_text = result.content[0].text
                logger.debug(f"Tool {tool_name} returned: {result_text[:200]}...")

                return {
                    "success": True,
                    "result": result_text
                }
            else:
                logger.warning(f"Tool {tool_name} returned empty result")
                return {
                    "success": False,
                    "error": "Tool returned empty result"
                }

        except asyncio.TimeoutError:
            logger.error(f"Tool {tool_name} timed out after {timeout}s")
            return {
                "success": False,
                "error": f"Tool execution timed out after {timeout}s"
            }

        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def parse_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response for tool call request.

        Args:
            text: LLM response text

        Returns:
            Parsed tool call dict or None if no tool call found
        """
        try:
            # Try to find JSON in response
            text = text.strip()

            # Check if response starts with JSON
            if text.startswith("{") and "tool_call" in text:
                # Find the JSON block
                brace_count = 0
                json_end = 0
                for i, char in enumerate(text):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break

                if json_end > 0:
                    json_str = text[:json_end]
                    data = json.loads(json_str)

                    if "tool_call" in data:
                        tool_call = data["tool_call"]
                        if "name" in tool_call and "arguments" in tool_call:
                            logger.info(f"Parsed tool call: {tool_call['name']}")
                            return {
                                "name": tool_call["name"],
                                "arguments": tool_call["arguments"],
                                "reasoning": data.get("reasoning", "")
                            }

            return None

        except json.JSONDecodeError as e:
            logger.debug(f"No valid tool call JSON found in response: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing tool call: {e}", exc_info=True)
            return None

    async def cleanup(self):
        """Cleanup MCP connection."""
        if not self._initialized:
            logger.debug("MCP manager not initialized, skipping cleanup")
            return
            
        logger.info("=" * 60)
        logger.info("Cleaning up MCP manager...")
        
        # Close session first
        if self.session:
            try:
                logger.debug("Exiting MCP session context...")
                await asyncio.wait_for(
                    self.session.__aexit__(None, None, None),
                    timeout=2.0
                )
                logger.debug("✓ MCP session closed")
            except asyncio.TimeoutError:
                logger.warning("⚠ MCP session cleanup timed out")
            except Exception as e:
                logger.warning(f"⚠ Error closing MCP session: {e}")
        
        # Close transport
        if self.transport:
            try:
                logger.debug("Exiting MCP transport context...")
                await asyncio.wait_for(
                    self.transport.__aexit__(None, None, None),
                    timeout=2.0
                )
                logger.debug("✓ MCP transport closed")
            except asyncio.TimeoutError:
                logger.warning("⚠ MCP transport cleanup timed out")
            except Exception as e:
                logger.warning(f"⚠ Error closing MCP transport: {e}")
        
        # Reset state
        self.session = None
        self.transport = None
        self.read_stream = None
        self.write_stream = None
        self._initialized = False
        
        logger.info("✓ MCP manager cleanup complete")
        logger.info("=" * 60)

    @property
    def is_initialized(self) -> bool:
        """Check if MCP manager is initialized."""
        return self._initialized and self.session is not None

