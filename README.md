
# 🔌 День 11: MCP (Model Context Protocol)

**Описание:** Установка MCP SDK/клиента и написание минимального кода для создания MCP-соединения и получения списка доступных инструментов.

Что сделать:
- Установить MCP SDK/клиент (или поднять MCP-сервер, если используете локальный вариант)
- Написать минимальный код, который создаёт MCP-соединение
- Реализовать получение списка доступных инструментов от MCP
- Результат: Код, который показывает список инструментов MCP

Как проверить:
1. Установить MCP SDK/клиент или запустить MCP-сервер
2. Запустить код для создания MCP-соединения
3. Убедиться, что список доступных инструментов корректно отображается
4. Проверить работоспособность полученного списка инструментов



## 📖 Описание задания

Интеграция с Model Context Protocol (MCP) для расширения возможностей AI моделей:

- **MCP SDK/Клиент** - установка и настройка MCP клиента
- **MCP-соединение** - создание соединения с MCP сервером
- **Инструменты MCP** - получение и использование списка доступных инструментов
- **Интеграция** - подключение MCP к существующему боту

## 🎯 Цели задания

1. **Освоить MCP** - изучить Model Context Protocol
2. **Настроить интеграцию** - установить и настроить MCP клиент/сервер
3. **Создать соединение** - реализовать базовое MCP-соединение
4. **Получить инструменты** - получить и отобразить список доступных инструментов

## 🔬 Технологии

- **Python 3.10+**
- **MCP SDK** - Model Context Protocol для интеграции с AI моделями
- **MCP Client/Server** - клиент или сервер для работы с MCP
- **httpx** - async HTTP клиент для замеров времени
- **python-telegram-bot** - для тестирования через Telegram бота

## 🧪 MCP Настройка

### MCP Компоненты

Для работы с MCP необходимо настроить следующие компоненты:

| Компонент | Описание | Тип |
|-----------|----------|-----|
| **MCP SDK** | SDK для работы с Model Context Protocol | Python пакет |
| **MCP Client** | Клиент для подключения к MCP серверам | Библиотека |
| **MCP Server** | Сервер предоставляющий инструменты | Опционально |
| **MCP Transport** | Протокол обмена данными | JSON-RPC 2.0 |

### MCP Инструменты

Примеры инструментов, которые могут быть доступны через MCP:

1. **File System** - работа с файлами и директориями
2. **Git** - операции с git репозиториями
3. **Database** - работа с базами данных
4. **HTTP Client** - выполнение HTTP запросов
5. **Shell** - выполнение команд в терминале

### MCP Метрики

| Метрика | Описание | Единица измерения |
|---------|----------|-------------------|
| **Connection Time** | Время установления соединения | ms |
| **Tool Count** | Количество доступных инструментов | шт |
| **Response Time** | Время выполнения инструмента | ms |
| **Success Rate** | Процент успешных операций | % |
| **Error Rate** | Процент ошибок | % |

## 📊 Методология интеграции

### Критерии успешной интеграции

1. **Соединение (Connection)** - успешное установление MCP-соединения
2. **Инструменты (Tools)** - корректное получение списка инструментов
3. **Функциональность (Functionality)** - работоспособность полученных инструментов
4. **Производительность (Performance)** - время отклика MCP операций
5. **Надежность (Reliability)** - стабильность соединения

### Формула оценки

```
MCP Integration Score = (Connection × 0.3) + (Tools × 0.3) + (Functionality × 0.2) + (Performance × 0.1) + (Reliability × 0.1)

```

## 🚀 Быстрый старт

### Требования

- **Python 3.10+**
- **MCP SDK** - Model Context Protocol SDK
- **MCP Client** - клиент для работы с MCP серверами
- **Telegram Bot Token** (от @BotFather) - опционально

### Установка

1. **Клонируйте репозиторий:**

```bash
git clone <repository-url>
cd ai-challenge
git checkout day_11_local_mcp

```

2. **Создайте виртуальное окружение:**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac

# или
venv\Scripts\activate  # Windows

```

3. **Установите зависимости:**

```bash
pip install -r requirements.txt

```

4. **Создайте файл `.env`:**

```bash
cp .env.example .env

```

5. **Заполните `.env` файл:**

```env

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# MCP Configuration
MCP_SERVER_URL=http://localhost:3000
MCP_API_KEY=your_mcp_api_key_here
MCP_CLIENT_ID=your_client_id

# Application Settings
LOG_LEVEL=INFO
MAX_MESSAGE_LENGTH=4000

```

### Запуск экспериментов

#### Ручной запуск

```bash
source venv/bin/activate
python run.py

```

## 🔌 Программная интеграция MCP

### Подключение MCP через API

MCP можно интегрировать с AI моделями программно, используя MCP клиент для подключения к локальному или удаленному MCP серверу. Это позволяет расширить возможности AI моделей, предоставив им доступ к внешним инструментам и данным.

### Архитектура интеграции

```
┌─────────────────┐
│  Telegram Bot   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│   AI Model API  │◄────►│   MCP Client    │
│  (Yandex GPT)   │      └────────┬────────┘
└─────────────────┘               │
                                  ▼
                         ┌─────────────────┐
                         │   MCP Server    │
                         │   (Local/stub)  │
                         └────────┬────────┘
                                  │
                         ┌────────┴────────┐
                         │  MCP Tools:     │
                         │  - get_user     │
                         │  - get_repos    │
                         │  - search_repos │
                         │  - etc.         │
                         └─────────────────┘
```

### Шаг 1: Запуск локального MCP сервера

Сначала запустите локальный MCP сервер с GitHub инструментами (stub):

```bash
cd mcp
python server.py
```

Сервер будет ожидать подключения через stdio.

### Шаг 2: Создание MCP клиента

Создайте Python скрипт для подключения к MCP серверу:

```python
import asyncio
import json
from typing import List, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def connect_to_mcp_server() -> tuple[ClientSession, Any]:
    """Подключение к локальному MCP серверу."""
    
    # Параметры запуска MCP сервера
    server_params = StdioServerParameters(
        command="python",
        args=["mcp/server.py"],
        env=None
    )
    
    # Создание клиента и подключение
    stdio_transport = await stdio_client(server_params)
    stdio, write = stdio_transport
    
    async with ClientSession(stdio, write) as session:
        # Инициализация сессии
        await session.initialize()
        
        return session, stdio_transport


async def list_available_tools(session: ClientSession) -> List[Dict[str, Any]]:
    """Получение списка доступных MCP инструментов."""
    
    # Запрос списка инструментов
    tools_result = await session.list_tools()
    
    tools = []
    for tool in tools_result.tools:
        tools.append({
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        })
    
    return tools


async def call_mcp_tool(
    session: ClientSession,
    tool_name: str,
    arguments: Dict[str, Any]
) -> str:
    """Вызов MCP инструмента."""
    
    result = await session.call_tool(tool_name, arguments)
    
    # Результат возвращается как список TextContent
    if result.content:
        return result.content[0].text
    
    return ""


async def main():
    """Пример использования MCP клиента."""
    
    # Подключение к серверу
    session, transport = await connect_to_mcp_server()
    
    try:
        # Получение списка инструментов
        tools = await list_available_tools(session)
        print("📋 Доступные MCP инструменты:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        # Пример вызова инструмента
        print("\n🔧 Вызов инструмента 'get_user':")
        result = await call_mcp_tool(
            session,
            "get_user",
            {"username": "octocat"}
        )
        print(json.dumps(json.loads(result), indent=2))
        
    finally:
        # Закрытие соединения
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### Шаг 3: Интеграция с AI моделью

Интегрируйте MCP инструменты с вашей AI моделью через API:

```python
from typing import List, Dict, Any, Optional
from src.llm.client import YandexLLMClient
from mcp import ClientSession


class AIWithMCPTools:
    """AI модель с доступом к MCP инструментам."""
    
    def __init__(
        self,
        llm_client: YandexLLMClient,
        mcp_session: ClientSession
    ):
        self.llm_client = llm_client
        self.mcp_session = mcp_session
        self.available_tools = []
    
    async def initialize(self):
        """Инициализация: получение списка доступных инструментов."""
        tools_result = await self.mcp_session.list_tools()
        self.available_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            }
            for tool in tools_result.tools
        ]
    
    async def send_message_with_tools(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7
    ) -> str:
        """
        Отправка сообщения в AI модель с возможностью вызова MCP инструментов.
        
        Примечание: Требуется поддержка function calling в модели.
        """
        
        # Добавляем информацию о доступных инструментах в системный промпт
        system_message = {
            "role": "system",
            "content": f"""У тебя есть доступ к следующим инструментам:

{self._format_tools_description()}

Если тебе нужно использовать инструмент, укажи это в своем ответе в формате:
TOOL_CALL: <имя_инструмента>
ARGUMENTS: <JSON с аргументами>
"""
        }
        
        # Добавляем системное сообщение в начало
        full_messages = [system_message] + messages
        
        # Отправляем запрос к модели
        response = await self.llm_client.send_prompt(
            messages=full_messages,
            temperature=temperature
        )
        
        # Получаем текст ответа
        response_text = response["choices"][0]["message"]["content"]
        
        # Проверяем, нужно ли вызвать инструмент
        if "TOOL_CALL:" in response_text:
            return await self._handle_tool_call(response_text, messages, temperature)
        
        return response_text
    
    def _format_tools_description(self) -> str:
        """Форматирование описания инструментов для промпта."""
        descriptions = []
        for tool in self.available_tools:
            func = tool["function"]
            descriptions.append(
                f"- {func['name']}: {func['description']}\n"
                f"  Параметры: {func['parameters']}"
            )
        return "\n".join(descriptions)
    
    async def _handle_tool_call(
        self,
        response_text: str,
        original_messages: List[Dict[str, str]],
        temperature: float
    ) -> str:
        """Обработка вызова инструмента моделью."""
        
        # Парсим имя инструмента и аргументы из ответа
        # (упрощенная реализация, в реальности нужен более надежный парсинг)
        import re
        import json
        
        tool_match = re.search(r'TOOL_CALL:\s*(\w+)', response_text)
        args_match = re.search(r'ARGUMENTS:\s*(\{.*?\})', response_text, re.DOTALL)
        
        if not tool_match or not args_match:
            return response_text
        
        tool_name = tool_match.group(1)
        arguments = json.loads(args_match.group(1))
        
        # Вызываем MCP инструмент
        tool_result = await self.mcp_session.call_tool(tool_name, arguments)
        tool_output = tool_result.content[0].text if tool_result.content else ""
        
        # Добавляем результат инструмента в контекст и запрашиваем финальный ответ
        updated_messages = original_messages + [
            {
                "role": "assistant",
                "content": f"Использую инструмент {tool_name}"
            },
            {
                "role": "user",
                "content": f"Результат выполнения инструмента:\n{tool_output}\n\nТеперь дай ответ пользователю на основе этих данных."
            }
        ]
        
        # Получаем финальный ответ
        final_response = await self.llm_client.send_prompt(
            messages=updated_messages,
            temperature=temperature
        )
        
        return final_response["choices"][0]["message"]["content"]


# Пример использования
async def example_usage():
    """Пример интеграции AI модели с MCP инструментами."""
    
    # Инициализация LLM клиента
    llm_client = YandexLLMClient(
        api_key="your_api_key",
        base_url="https://llm.api.cloud.yandex.net",
        temperature=0.7
    )
    
    # Подключение к MCP серверу
    mcp_session, _ = await connect_to_mcp_server()
    
    try:
        # Создание AI с инструментами
        ai = AIWithMCPTools(llm_client, mcp_session)
        await ai.initialize()
        
        # Отправка сообщения
        response = await ai.send_message_with_tools(
            messages=[
                {
                    "role": "user",
                    "content": "Покажи информацию о пользователе GitHub с именем octocat"
                }
            ]
        )
        
        print(response)
        
    finally:
        await mcp_session.close()
        await llm_client.close()
```

### Шаг 4: Интеграция с существующим ботом

Для интеграции MCP в существующий бот, добавьте MCP клиент в инициализацию:

```python
# src/bot/llm_integration.py

from mcp import ClientSession
from typing import Optional


class LLMIntegration:
    def __init__(self, llm_client: YandexLLMClient):
        self.llm_client = llm_client
        self.mcp_session: Optional[ClientSession] = None
    
    async def initialize_mcp(self):
        """Инициализация MCP соединения."""
        if not self.mcp_session:
            self.mcp_session, _ = await connect_to_mcp_server()
            logger.info("MCP session initialized")
    
    async def process_with_tools(self, message: str) -> str:
        """Обработка сообщения с использованием MCP инструментов."""
        if not self.mcp_session:
            await self.initialize_mcp()
        
        # Используйте AIWithMCPTools для обработки
        ai = AIWithMCPTools(self.llm_client, self.mcp_session)
        await ai.initialize()
        
        return await ai.send_message_with_tools([
            {"role": "user", "content": message}
        ])
```

### Доступные MCP инструменты (stub)

Текущий MCP сервер предоставляет следующие stub-инструменты:

| Инструмент | Описание | Параметры |
|------------|----------|-----------|
| `get_user` | Получение информации о пользователе GitHub | `username: str` |
| `get_user_repos` | Список репозиториев пользователя | `username: str, limit: int` |
| `get_repo_info` | Детальная информация о репозитории | `owner: str, repo: str` |
| `search_repos` | Поиск репозиториев | `query: str, limit: int` |
| `get_repo_issues` | Получение issues репозитория | `owner: str, repo: str, state: str, limit: int` |

**Примечание:** Все инструменты возвращают mock-данные. Для работы с реальным GitHub API потребуется добавить GitHub token и заменить stub-реализации.

### Полезные ссылки

- 📚 [MCP Documentation](https://modelcontextprotocol.io/)
- 🔧 [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- 📖 [Подключение MCP к Claude Desktop](mcp/README.md)

## 📈 Результаты и выводы

TODO

## 🔧 Конфигурация

### Переменные окружения

| Переменная | Обязательна | Описание | По умолчанию |
|------------|-------------|----------|--------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Токен Telegram бота | - |
| `MCP_SERVER_URL` | ✅ | URL MCP сервера | http://localhost:3000 |
| `MCP_API_KEY` | ✅ | API ключ для MCP | - |
| `MCP_CLIENT_ID` | ❌ | Идентификатор MCP клиента | - |

### Просмотр логов

```bash

# Последние логи
tail -50 logs/rick_bot.log

# Следить за логами в реальном времени
tail -f logs/rick_bot.log

# Поиск ошибок
grep ERROR logs/rick_bot.log

```

