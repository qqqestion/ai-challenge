#!/usr/bin/env python3
"""
Example of integrating MCP tools with AI model.

This demonstrates a simple pattern for using MCP tools
to enhance AI model capabilities.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class SimpleAIWithTools:
    """
    Simple AI assistant with access to MCP tools.

    This is a simplified example showing the pattern.
    In production, you would use actual LLM API.
    """

    def __init__(self, mcp_session: ClientSession):
        self.mcp_session = mcp_session
        self.tools = []

    async def initialize(self):
        """Load available tools from MCP server."""
        tools_result = await self.mcp_session.list_tools()
        self.tools = tools_result.tools
        print(f"✅ Loaded {len(self.tools)} MCP tools")

    def _analyze_intent(self, user_message: str) -> Optional[Dict[str, Any]]:
        """
        Simple intent analysis to determine if we need to call a tool.

        In production, this would be done by the LLM itself.

        Returns:
            Dict with tool_name and arguments, or None
        """
        message_lower = user_message.lower()

        # Pattern matching for demo purposes
        if "user" in message_lower and "info" in message_lower:
            # Extract username (simplified)
            words = user_message.split()
            username = "octocat"  # default
            for i, word in enumerate(words):
                if word.lower() in ["user", "пользователя", "username"]:
                    if i + 1 < len(words):
                        username = words[i + 1].strip("'\"")
                        break

            return {"tool": "get_user", "args": {"username": username}}

        elif "repos" in message_lower or "репозиториев" in message_lower:
            words = user_message.split()
            username = "octocat"
            for i, word in enumerate(words):
                if word.lower() in ["user", "пользователя"]:
                    if i + 1 < len(words):
                        username = words[i + 1].strip("'\"")
                        break

            return {"tool": "get_user_repos", "args": {"username": username, "limit": 5}}

        elif "search" in message_lower or "найди" in message_lower:
            # Extract search query
            query_start = (
                message_lower.find("search") + 6
                if "search" in message_lower
                else message_lower.find("найди") + 5
            )
            query = user_message[query_start:].strip("'\" ")

            return {"tool": "search_repos", "args": {"query": query, "limit": 5}}

        return None

    def _format_tool_result(self, tool_name: str, result_json: str) -> str:
        """Format tool result for presentation."""
        data = json.loads(result_json)

        if tool_name == "get_user":
            return (
                f"👤 Пользователь GitHub:\n"
                f"   Логин: {data['login']}\n"
                f"   Имя: {data['name']}\n"
                f"   Публичных репозиториев: {data['public_repos']}\n"
                f"   Подписчиков: {data['followers']}\n"
                f"   Подписок: {data['following']}\n"
                f"   Профиль: {data['html_url']}"
            )

        elif tool_name == "get_user_repos":
            repos = data["repositories"]
            result = f"📚 Репозитории пользователя {data['username']}:\n"
            for repo in repos:
                result += (
                    f"   • {repo['name']} ({repo['language']}) "
                    f"⭐ {repo['stars']} 🍴 {repo['forks']}\n"
                )
            return result

        elif tool_name == "search_repos":
            items = data["items"]
            result = f"🔍 Результаты поиска '{data['query']}':\n"
            for item in items:
                result += f"   • {item['name']} ({item['language']}) ⭐ {item['stars']}\n"
            return result

        # Fallback: return raw JSON
        return json.dumps(data, indent=2, ensure_ascii=False)

    async def process_message(self, user_message: str) -> str:
        """
        Process user message and return response.

        This is a simplified AI assistant that:
        1. Analyzes user intent
        2. Calls appropriate MCP tool if needed
        3. Formats and returns result
        """
        print(f"\n💬 User: {user_message}")

        # Analyze intent
        intent = self._analyze_intent(user_message)

        if not intent:
            return (
                "Я могу помочь вам с GitHub! Попробуйте:\n"
                "- 'Покажи информацию о пользователе octocat'\n"
                "- 'Покажи репозитории пользователя octocat'\n"
                "- 'Найди репозитории telegram bot'"
            )

        # Call MCP tool
        tool_name = intent["tool"]
        args = intent["args"]

        print(f"🔧 Calling tool: {tool_name} with {args}")

        try:
            result = await self.mcp_session.call_tool(tool_name, args)
            result_text = result.content[0].text if result.content else ""

            # Format result
            formatted = self._format_tool_result(tool_name, result_text)

            return formatted

        except Exception as e:
            return f"❌ Ошибка при вызове инструмента: {e}"


async def connect_to_mcp_server() -> tuple:
    """Connect to local MCP server."""
    server_params = StdioServerParameters(
        command="python",
        args=[str(Path(__file__).parent / "server.py")],
        env=None,
    )

    stdio_transport = await stdio_client(server_params)
    stdio, write = stdio_transport

    session = ClientSession(stdio, write)
    await session.initialize()

    return session, stdio_transport


async def main():
    """Interactive demo of AI with MCP tools."""
    print("=" * 60)
    print("🤖 AI Assistant with MCP Tools - Interactive Demo")
    print("=" * 60)
    print("\nПодключение к MCP серверу...")

    session = None
    try:
        # Connect to MCP
        session, transport = await connect_to_mcp_server()
        print("✅ Подключено к MCP серверу")

        # Initialize AI
        ai = SimpleAIWithTools(session)
        await ai.initialize()

        print("\n" + "=" * 60)
        print("Готов к работе! Введите запрос (или 'exit' для выхода)")
        print("=" * 60)

        # Demo queries
        demo_queries = [
            "Покажи информацию о пользователе octocat",
            "Покажи репозитории пользователя octocat",
            "Найди репозитории telegram bot",
        ]

        for query in demo_queries:
            response = await ai.process_message(query)
            print(f"\n🤖 Assistant:\n{response}\n")
            print("-" * 60)

        print("\n💡 Совет: В реальной интеграции LLM сама анализирует")
        print("   запрос и решает, какие инструменты вызвать.")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()

    finally:
        if session:
            print("\n🔌 Закрытие соединения...")
            await session.__aexit__(None, None, None)
            print("✅ Соединение закрыто")


if __name__ == "__main__":
    asyncio.run(main())

