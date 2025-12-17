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

        elif "repo" in message_lower and "info" in message_lower:
            # Extract owner and repo name
            words = user_message.split()
            owner = "octocat"
            repo = "Hello-World"
            for i, word in enumerate(words):
                if "/" in word:
                    parts = word.split("/")
                    if len(parts) == 2:
                        owner = parts[0].strip("'\"")
                        repo = parts[1].strip("'\"")
                        break

            return {"tool": "get_repo_info", "args": {"owner": owner, "repo": repo}}

        elif "events" in message_lower or "события" in message_lower:
            words = user_message.split()

            # Check if it's a user events or repo events
            if "user" in message_lower or "пользователя" in message_lower:
                username = "octocat"
                for i, word in enumerate(words):
                    if word.lower() in ["user", "пользователя"]:
                        if i + 1 < len(words):
                            username = words[i + 1].strip("'\"")
                            break

                return {"tool": "get_user_events", "args": {"username": username, "limit": 5}}

            elif "repo" in message_lower or "репозитория" in message_lower:
                owner = "octocat"
                repo = "Hello-World"
                for i, word in enumerate(words):
                    if "/" in word:
                        parts = word.split("/")
                        if len(parts) == 2:
                            owner = parts[0].strip("'\"")
                            repo = parts[1].strip("'\"")
                            break

                return {"tool": "get_repo_events", "args": {"owner": owner, "repo": repo, "limit": 5}}

        return None

    def _format_tool_result(self, tool_name: str, result_json: str) -> str:
        """Format tool result for presentation."""
        data = json.loads(result_json)

        # Check for errors
        if "error" in data:
            return f"❌ Ошибка: {data['error']}"

        if tool_name == "get_user":
            return (
                f"👤 Пользователь GitHub:\n"
                f"   Логин: {data['login']}\n"
                f"   Имя: {data.get('name', 'N/A')}\n"
                f"   Публичных репозиториев: {data['public_repos']}\n"
                f"   Подписчиков: {data['followers']}\n"
                f"   Подписок: {data['following']}\n"
                f"   Профиль: {data['html_url']}"
            )

        elif tool_name == "get_user_repos":
            repos = data["repositories"]
            result = f"📚 Репозитории пользователя {data['username']}:\n"
            for repo in repos:
                lang = repo.get('language') or 'N/A'
                result += (
                    f"   • {repo['name']} ({lang}) "
                    f"⭐ {repo['stargazers_count']} 🍴 {repo['forks_count']}\n"
                )
            return result

        elif tool_name == "get_repo_info":
            lang = data.get('language') or 'N/A'
            desc = data.get('description') or 'Нет описания'
            return (
                f"📦 Репозиторий GitHub:\n"
                f"   Название: {data['full_name']}\n"
                f"   Описание: {desc}\n"
                f"   Язык: {lang}\n"
                f"   Звезды: {data['stargazers_count']} ⭐\n"
                f"   Форки: {data['forks_count']} 🍴\n"
                f"   Открытые issue: {data['open_issues_count']}\n"
                f"   Ссылка: {data['html_url']}"
            )

        elif tool_name == "get_user_events":
            events = data["events"]
            result = f"📅 События пользователя {data['username']}:\n"
            for event in events:
                event_type = event['type']
                repo_name = event['repo']['name']
                created_at = event['created_at']
                result += f"   • {event_type} в {repo_name} ({created_at})\n"
            return result

        elif tool_name == "get_repo_events":
            events = data["events"]
            result = f"📅 События репозитория {data['owner']}/{data['repo']}:\n"
            for event in events:
                event_type = event['type']
                actor = event['actor']['login']
                created_at = event['created_at']
                result += f"   • {event_type} от {actor} ({created_at})\n"
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
                "- 'Покажи информацию о репозитории octocat/Hello-World'\n"
                "- 'Покажи события пользователя octocat'\n"
                "- 'Покажи события репозитория octocat/Hello-World'"
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
            "Покажи информацию о репозитории octocat/Hello-World",
            "Покажи события пользователя octocat",
            "Покажи события репозитория octocat/Hello-World",
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

