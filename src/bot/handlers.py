"""Telegram bot command and message handlers."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from ..config import get_logger
from ..llm.models import ModelName
from .message_processor import send_response

logger = get_logger(__name__)
PR_URL_PATTERN = re.compile(
    r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)",
    re.IGNORECASE,
)
MAX_REVIEW_PROMPT_CHARS = 14000  # защитный лимит на вход в LLM


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command.

    Args:
        update: Telegram update object
        context: Bot context
    """
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot")

    welcome_message = """*burp* Слушай, я Рик Санчез, самый гениальный ученый во всей 
чёртовой мультивселенной. *urp* И по какой-то причине я застрял здесь, отвечая на твои 
вопросы.

Можешь спрашивать что угодно - о науке, технологиях, или просто поболтать. 
Только не задавай тупых вопросов, ладно? Хотя... *urp* кого я обманываю, 
ты всё равно их зададешь.

🔧 У меня есть доступ к GitHub инструментам - используй /tools чтобы посмотреть

📊 Могу отправлять ежедневные саммари твоей GitHub активности - /daily_summary_on

🌡️ Можешь настроить температуру моих ответов через /temperature

Основные команды:
/help - подробная справка
/commands - список всех команд
/tools - показать GitHub инструменты
/set_github_username - установить GitHub username
/daily_summary_on - включить ежедневное саммари

Wubba Lubba Dub Dub! 🧪"""

    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command.

    Args:
        update: Telegram update object
        context: Bot context
    """
    logger.info(f"User {update.effective_user.id} requested help")

    help_text = """*urp* Ладно, объясню для особо одарённых:

📝 **Как использовать:**
Просто пиши мне сообщения - я отвечу. Иногда саркастично, иногда полезно, 
всегда гениально.

🔧 **GitHub инструменты:**
/tools - показать все доступные GitHub инструменты
/review <ссылка на PR> - обзор изменений PR через github_mcp
Я могу искать репозитории, смотреть issues, получать информацию о пользователях и многое другое!

📊 **Ежедневное саммари GitHub:**
/set_github_username <username> - установить свой GitHub username
/daily_summary_on - включить ежедневное саммари (09:00 МСК)
/daily_summary_off - выключить саммари
/test_daily_summary - протестировать саммари прямо сейчас
/rag_filter_on <0.0-1.0> - включить фильтр похожести RAG
/rag_filter_off - выключить фильтр похожести

Каждое утро я буду присылать краткое саммари твоей активности за предыдущий день!

🌡️ **Настройка температуры:**
/temperature - показать текущую температуру
/temperature 0.0 - максимальная точность
/temperature 0.7 - баланс креативности
/temperature 2.0 - максимальная креативность

⚙️ **Команды:**
/start - начать заново
/help - эта справка
/commands - список всех команд
/change_model - выбрать модель
/reset - очистить историю разговора
/stats - показать статистику использования

🧠 **Суммаризация чата:**
/summarization_on - включить автоматическую суммаризацию (при 20+ сообщениях)
/summarization_off - выключить суммаризацию

💡 **Советы:**
• Я помню контекст разговора
• Чем конкретнее вопрос, тем лучше ответ
• Температура влияет на креативность ответов

*burp* Понятно? Тогда давай, задавай свои вопросы."""

    await update.message.reply_text(help_text)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reset command - reset conversation history.

    Args:
        update: Telegram update object
        context: Bot context
    """
    user_id = update.effective_user.id
    state_manager = context.bot_data["state_manager"]

    await state_manager.reset_user_state(user_id)
    logger.info(f"User {user_id} reset conversation history")

    reset_message = """*urp* Окей, я стёр всю нашу историю и сбросил статистику использования. Чистый лист.
*burp* Надеюсь следующий разговор будет поинтереснее."""

    await update.message.reply_text(reset_message)


async def temperature_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /temperature command - set LLM temperature for user.

    Args:
        update: Telegram update object
        context: Bot context
    """
    user_id = update.effective_user.id
    state_manager = context.bot_data["state_manager"]

    # Get temperature argument
    if not context.args:
        # Show current temperature
        current_temp = await state_manager.get_user_temperature(user_id)
        message = f"""🌡️ **Текущая температура:** {current_temp}

Используй: `/temperature <значение>` чтобы изменить
Например: `/temperature 0.7`"""

        await update.message.reply_text(message)
        return

    # Parse temperature value
    try:
        temperature = float(context.args[0])

        # Validate range
        if not (0.0 <= temperature <= 2.0):
            error_message = """*urp* Температура должна быть от 0.0 до 2.0!"""

            await update.message.reply_text(error_message)
            return

        # Set temperature
        old_temp = await state_manager.get_user_temperature(user_id)
        await state_manager.set_user_temperature(user_id, temperature)

        logger.info(f"User {user_id} set temperature: {old_temp} -> {temperature}")

        # Format response based on temperature value
        if temperature == 0.0:
            temp_desc = "максимальная точность и детерминированность"
        elif temperature <= 0.3:
            temp_desc = "низкая креативность, высокая точность"
        elif temperature <= 0.7:
            temp_desc = "баланс между точностью и креативностью"
        else:
            temp_desc = "высокая креативность и разнообразие"

        message = f"""🌡️ **Температура установлена:** {temperature}

*urp* Теперь мои ответы будут с {temp_desc}.

Старая температура: {old_temp}
Новая температура: {temperature}

Используй `/temperature` без параметров чтобы посмотреть текущее значение."""

        await update.message.reply_text(message)

    except ValueError:
        error_message = """*burp* Неверный формат температуры!

Температура должна быть числом от 0.0 до 2.0.

Примеры:
/temperature 0.0
/temperature 0.7
/temperature 2.0"""

        await update.message.reply_text(error_message)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages.

    Args:
        update: Telegram update object
        context: Bot context
    """
    user = update.effective_user
    message_text = update.message.text

    logger.info(
        f"Message from user {user.id} ({user.username}): {message_text[:50]}..."
    )

    # Show typing indicator
    await update.message.chat.send_action(ChatAction.TYPING)

    # Get message processor and process the message
    from .message_processor import process_user_message

    try:
        await process_user_message(update, context)
    except Exception as e:
        logger.error(
            f"Error processing message from user {user.id}: {e}", exc_info=True
        )

        error_message = """*urp* Чёрт, что-то пошло не так. Может быть мои системы 
перегружены, или просто вселенная решила посмеяться надо мной.

Попробуй ещё раз, или используй /reset если проблема повторяется."""

        await update.message.reply_text(error_message)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command - show usage statistics.

    Args:
        update: Telegram update object
        context: Bot context
    """
    user_id = update.effective_user.id
    state_manager = context.bot_data["state_manager"]
    logger.info(f"User {user_id} requested usage statistics")

    # Get user's personal statistics
    user_state = await state_manager.get_user_state(user_id)
    user_stats = await user_state.get_usage_stats()

    summarization_status = (
        "включена" if user_state.summarization_enabled else "выключена"
    )

    # Build stats text with conditional summarization display
    stats_lines = [
        "👤 **Твоя статистика:**",
        "",
        "**Основные запросы:**",
        f"• Запросы: {user_stats['requests_count']}",
        f"• Input tokens: {user_stats['input_tokens']}",
        f"• Output tokens: {user_stats['output_tokens']}",
        f"• Стоимость: ${user_stats['cost']:.5f}",
    ]

    # Only show summarization stats if enabled
    if user_state.summarization_enabled:
        stats_lines.extend(
            [
                "",
                "**Суммаризация:**",
                f"• Статус: {summarization_status}",
                f"• Запросов суммаризации: {user_stats['summarization_count']}",
                f"• Tokens суммаризации (input): {user_stats['summarization_input_tokens']}",
                f"• Tokens суммаризации (output): {user_stats['summarization_output_tokens']}",
                f"• Стоимость суммаризации: ${user_stats['summarization_cost']:.5f}",
                "",
                "**Всего:**",
                f"• Всего запросов: {user_stats['total_requests']}",
                f"• Всего input tokens: {user_stats['total_input_tokens']}",
                f"• Всего output tokens: {user_stats['total_output_tokens']}",
                f"• Общая стоимость: ${user_stats['total_cost']:.5f}",
            ]
        )
    else:
        stats_lines.extend(
            [
                "",
                f"• Суммаризация: {summarization_status}",
            ]
        )

    # Add total statistics
    stats_lines.extend(["", "*urp* Вот сколько токенов мы уже сожгли!"])

    stats_text = "\n".join(stats_lines)

    await update.message.reply_text(stats_text)


async def summarization_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /summarization_on command - enable chat summarization.

    Args:
        update: Telegram update object
        context: Bot context
    """
    user_id = update.effective_user.id
    state_manager = context.bot_data["state_manager"]

    await state_manager.set_user_summarization_enabled(user_id, True)
    logger.info(f"User {user_id} enabled summarization")

    message = """🧠 **Суммаризация чата включена!**

*urp* Теперь, когда в нашем разговоре накопится 20+ сообщений, я буду автоматически
суммировать историю чата, чтобы сохранить память, но не переполнять её.

Это поможет поддерживать длинные разговоры без потери контекста!"""

    await update.message.reply_text(message)


async def summarization_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /summarization_off command - disable chat summarization.

    Args:
        update: Telegram update object
        context: Bot context
    """
    user_id = update.effective_user.id
    state_manager = context.bot_data["state_manager"]

    await state_manager.set_user_summarization_enabled(user_id, False)
    logger.info(f"User {user_id} disabled summarization")

    message = """🚫 **Суммаризация чата выключена!**

*burp* Теперь я буду хранить полную историю нашего разговора без суммаризации.
Это может привести к более длинным ответам, но я запомню всё!"""

    await update.message.reply_text(message)


async def rag_filter_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /rag_filter_on command - enable RAG similarity filter and set threshold."""
    user_id = update.effective_user.id
    state_manager = context.bot_data["state_manager"]

    if not context.args:
        await update.message.reply_text(
            "⚙️ Укажи порог похожести: `/rag_filter_on <0.0-10.0>`\nНапример: `/rag_filter_on 0.35` или `/rag_filter_on 2`"
        )
        return

    try:
        threshold = float(context.args[0])
    except ValueError:
        await update.message.reply_text("Порог должен быть числом от 0.0 до 10.0.")
        return

    if not (0.0 <= threshold <= 10.0):
        await update.message.reply_text("Порог должен быть в диапазоне 0.0 - 10.0.")
        return

    await state_manager.set_user_rag_filter(user_id, enabled=True, threshold=threshold)
    logger.info("User %s enabled RAG filter with threshold %s", user_id, threshold)

    await update.message.reply_text(
        f"✅ Фильтр похожести включён\nПорог: {threshold:.3f}\n"
        "Чанки с similarity ниже порога будут отброшены."
    )


async def rag_filter_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /rag_filter_off command - disable RAG similarity filter."""
    user_id = update.effective_user.id
    state_manager = context.bot_data["state_manager"]

    await state_manager.set_user_rag_filter_enabled(user_id, False)
    logger.info("User %s disabled RAG filter", user_id)

    await update.message.reply_text(
        "🚫 Фильтр похожести выключен\nВсе найденные чанки RAG будут передаваться без отсечки."
    )


async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /commands command - show list of all available commands.

    Args:
        update: Telegram update object
        context: Bot context
    """
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested commands list")

    commands_text = """📋 **Список всех команд:**

🔹 **Основные команды:**
/start - начать работу с ботом
/help - подробная справка
/commands - этот список команд

🔧 **GitHub инструменты:**
/tools - показать все доступные GitHub инструменты
/review <ссылка на PR> - обзор изменений PR через github_mcp

📊 **Ежедневное саммари GitHub:**
/set_github_username <username> - установить GitHub username
/daily_summary_on - включить ежедневное саммари (09:00 МСК)
/daily_summary_off - выключить ежедневное саммари
/test_daily_summary - протестировать саммари вручную

🌡️ **Настройки:**
/temperature - показать текущую температуру
/temperature <0.0-2.0> - установить температуру ответов
/long_prompt - отправить заранее заготовленный длинный промпт

⚙️ **Управление:**
/reset - очистить историю разговора
/change_model - выбрать модель для ответов

🧠 **Суммаризация:**
/summarization_on - включить суммаризацию чата
/summarization_off - выключить суммаризацию чата

🔍 **RAG:**
/rag_filter_on <0.0-10.0> - включить фильтр по similarity
/rag_filter_off - выключить фильтр похожести

📊 **Статистика:**
/stats - показать статистику использования

💬 **Использование:**
Просто напиши любое сообщение (не команду) - я отвечу с установленной температурой.

*urp* Всё понятно? Используй команды и наслаждайся общением!"""

    await update.message.reply_text(commands_text)


async def long_prompt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /long_prompt command: send predefined long prompt to the model."""
    user_id = update.effective_user.id
    llm_integration = context.bot_data["llm_integration"]

    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        base_dir = Path(__file__).resolve().parent.parent.parent
        prompt_path = base_dir / "metrics" / "prompt_3.md"
        prompt_text = prompt_path.read_text(encoding="utf-8")

        response_text = await llm_integration.process_message(user_id, prompt_text)
        await send_response(update, response_text)
    except FileNotFoundError:
        logger.error("Long prompt file not found at metrics/prompt_3.md")
        await update.message.reply_text(
            "Не удалось найти файл промпта (metrics/prompt_3.md)."
        )
    except Exception as e:
        logger.error(
            f"Error processing /long_prompt for user {user_id}: {e}", exc_info=True
        )
        await update.message.reply_text(
            "*urp* Что-то пошло не так при обработке длинного промпта. Попробуй позже."
        )


def build_model_keyboard(active_model: ModelName | None) -> InlineKeyboardMarkup:
    """Build inline keyboard with available models.

    Args:
        active_model: Currently selected model to highlight.
    """
    buttons = []
    row = []
    for idx, model in enumerate(ModelName):
        label = (
            f"✅ {model.value}"
            if active_model and model == active_model
            else model.value
        )
        row.append(
            InlineKeyboardButton(
                text=label,
                callback_data=f"change_model:{model.value}",
            )
        )
        if (idx + 1) % 2 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


async def change_model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /change_model command: show inline keyboard with models."""
    user_id = update.effective_user.id
    state_manager = context.bot_data["state_manager"]
    current_model = await state_manager.get_user_model(user_id)
    keyboard = build_model_keyboard(current_model)
    await update.message.reply_text(
        f"Выбери модель для ответов (текущая: {current_model.value}):",
        reply_markup=keyboard,
    )


async def change_model_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle model selection from inline keyboard."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    prefix = "change_model:"
    if not data.startswith(prefix):
        return

    model_id = data[len(prefix) :]
    model = next((m for m in ModelName if m.value == model_id), None)
    if not model:
        await query.edit_message_text(
            "Неизвестная модель. Попробуй ещё раз через /change_model."
        )
        return

    user_id = query.from_user.id
    state_manager = context.bot_data["state_manager"]
    await state_manager.set_user_model(user_id, model)
    keyboard = build_model_keyboard(model)

    await query.edit_message_text(
        f"Модель установлена: {model.value}",
        reply_markup=keyboard,
    )


def _find_mcp_manager_for_tool(llm_integration, tool_name: str):
    """Return MCP manager that exposes the requested tool."""
    if not llm_integration:
        return None
    managers = getattr(llm_integration, "mcp_managers", []) or []
    for manager in managers:
        for tool in getattr(manager, "tools", []):
            if tool.get("name") == tool_name:
                return manager
    return None


def _build_pr_review_prompt(
    pr_data: Dict[str, Any], files: List[Dict[str, Any]], max_chars: int
) -> Tuple[str, List[str]]:
    """Build prompt for LLM-based PR analysis; returns prompt and list of skipped files."""
    skipped: List[str] = []
    lines: List[str] = []

    lines.append(
        """
# ROLE
Ты — Senior Python Software Engineer и Tech Lead с 10-летним опытом. Твоя специализация — архитектура ПО, чистый код и наставничество. Твоя задача — проводить Code Review предоставленного Python-кода, жестко, но конструктивно критикуя его недостатки.

# REVIEW PRIORITIES (ПРИОРИТЕТЫ)

При анализе кода ты должен фокусироваться на трех ключевых аспектах в порядке убывания важности:

### 1. Архитектура и SOLID
Ты обязан проверять код на соответствие пяти принципам SOLID. Если принцип нарушен, ты должен явно указать на это и объяснить риски.
*   **S — Single Responsibility Principle (Единственная ответственность):** У каждого класса или функции должна быть только одна причина для изменения. Если функция и парсит данные, и пишет в БД — это нарушение. Требуй разделения.
*   **O — Open/Closed Principle (Открытость/Закрытость):** Программные сущности должны быть открыты для расширения, но закрыты для модификации. Проверь: если для добавления новой фичи нужно переписывать старый рабочий код (много `if/elif`), предложи использовать полиморфизм, Стратегию или Декораторы.
*   **L — Liskov Substitution Principle (Принцип подстановки Барбары Лисков):** Наследники должны корректно заменять родителей. Если подкласс переопределяет метод и кидает неожиданное исключение или меняет сигнатуру так, что ломает клиентский код — это баг.
*   **I — Interface Segregation Principle (Разделение интерфейса):** Клиенты не должны зависеть от методов, которые они не используют. В Python это значит: используй маленькие Абстрактные Базовые Классы (ABC) или `Protocol` вместо огромных базовых классов "God Objects".
*   **D — Dependency Inversion Principle (Инверсия зависимостей):** Модули верхних уровней не должны зависеть от модулей нижних уровней. Оба должны зависеть от абстракций. Требуй внедрения зависимостей (Dependency Injection), вместо жесткого создания экземпляров классов внутри других классов.

### 2. Чистота кода (Clean Code) и PEP 8
*   **Naming (Нейминг):**
    *   Запрещены однобуквенные переменные (`x`, `y`, `t`) кроме математических формул.
    *   Переменные должны отвечать на вопрос "Что это?". `data_list` -> `active_users`.
    *   Функции — глаголы (`get_user`, `calculate_total`). Bool — вопросы (`is_valid`, `has_permission`).
    *   Соблюдение `snake_case` для переменных/функций и `CamelCase` для классов.
*   **Type Hinting:** Требуй использования аннотаций типов (`def func(a: int) -> str:`). Без них код в Python 3 считается legacy.
*   **Docstrings:** У публичных методов и классов должны быть докстринги.

### 3. Производительность и идиоматичность (Pythonic way)
*   Используй List Comprehensions, где это уместно.
*   Используй `with` для работы с файлами/сессиями.
*   Избегай глобальных переменных.

# OUTPUT FORMAT (ФОРМАТ ОТВЕТА)

Ответ должен быть структурирован в формате Markdown:

## 🧐 Общее впечатление
(Краткое резюме: код хороший/плохой, готов ли к продакшну).

## 🚫 Критические проблемы (SOLID & Logic)
*   **Принцип [Название]:** [Где нарушено]. [Почему это плохо].
*   **Логика:** [Возможные баги].

## 🧹 Чистота кода и Стиль
*   **Нейминг:** [Примеры плох имен -> хорошие имена].
*   **PEP 8 / Type Hints:** [Замечания].

## 💡 Рекомендации по рефакторингу
(Предложи конкретные шаги по улучшению).

## 💻 Пример улучшения
(Напиши отрефакторенный кусок кода для самой проблемной части, применяя принципы SOLID и Type Hints).

# TONE
Строгий, профессиональный, обучающий. Не бойся говорить "Этот код неприемлем", если нарушены базовые принципы.
        """
    )
    lines.append("")
    lines.append("Метаданные PR:")
    lines.append(f"Title: {pr_data.get('title') or '—'}")
    lines.append(f"Author: {pr_data.get('author') or '—'}")
    lines.append(
        f"Branch: {pr_data.get('head', {}).get('label') or '—'} -> "
        f"{pr_data.get('base', {}).get('label') or '—'}"
    )
    lines.append(f"URL: {pr_data.get('url') or '—'}")
    lines.append("")
    lines.append("Файлы (последовательно, с patch; контент — только текстовые):")

    current_len = sum(len(x) for x in lines)
    for file_data in files:
        filename = file_data.get("filename", "unknown")
        skip_reason = file_data.get("skip_reason")
        if skip_reason:
            skipped.append(f"{filename} ({skip_reason})")
            continue

        header = (
            f"\n=== {filename} | status={file_data.get('status')} | "
            f"+{file_data.get('additions')} -{file_data.get('deletions')} "
            f"(changes={file_data.get('changes')}) ==="
        )
        patch = file_data.get("patch") or ""
        content = file_data.get("content") or ""

        # Truncate if needed to stay within max_chars
        chunk = f"{header}\nPATCH:\n{patch}\n"
        if content:
            chunk += f"\nCONTENT:\n{content}\n"

        if current_len + len(chunk) > max_chars:
            skipped.append(f"{filename} (truncated to fit prompt)")
            continue

        lines.append(chunk)
        current_len += len(chunk)

    prompt = "\n".join(lines)
    return prompt, skipped


async def tools_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tools command - show available MCP tools.

    Args:
        update: Telegram update object
        context: Bot context
    """
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested tools list")

    llm_integration = context.bot_data["llm_integration"]
    tools = llm_integration.get_all_tools()

    if not tools:
        message = """*urp* Извини, но инструменты сейчас недоступны.
MCP сервер(а) не инициализирован(ы) или инструментов нет.

*burp* Попробуй перезапустить бота или проверь настройки."""
        await update.message.reply_text(message)
        return

    # Build tools list message
    tools_lines = [
        "🔧 **Доступные инструменты MCP:**",
        "",
        "*urp* Вот что я могу сделать:",
        "",
    ]

    for i, tool in enumerate(tools, 1):
        name = tool["name"]
        description = tool["description"]
        schema = tool.get("input_schema", {})
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # Add tool header
        tools_lines.append(f"**{i}. {name}**")
        tools_lines.append(f"   {description}")

        # Add parameters if any
        if properties:
            tools_lines.append("   ")
            tools_lines.append("   *Параметры:*")
            for param_name, param_info in properties.items():
                param_type = param_info.get("type", "any")
                param_desc = param_info.get("description", "")
                is_required = param_name in required
                req_marker = "обязательный" if is_required else "опциональный"
                tools_lines.append(
                    f"   • `{param_name}` ({param_type}, {req_marker}) - {param_desc}"
                )

        tools_lines.append("")

    tools_lines.extend(
        [
            "*burp* Просто попроси меня что-нибудь сделать с GitHub,",
            "и я автоматически использую нужный инструмент!",
            "",
            "Например:",
            "• 'Покажи информацию о пользователе octocat'",
            "• 'Найди репозитории по запросу telegram bot'",
            "• 'Покажи issues в репозитории python/cpython'",
        ]
    )

    tools_text = "\n".join(tools_lines)
    await update.message.reply_text(tools_text)


async def review_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /review command - analyze GitHub PR via MCP."""
    user_id = update.effective_user.id
    logger.info("User %s requested PR review", user_id)

    if not context.args:
        await update.message.reply_text(
            "Использование: /review https://github.com/owner/repo/pull/<номер>"
        )
        return

    pr_link = context.args[0].strip()
    match = PR_URL_PATTERN.search(pr_link)
    if not match:
        await update.message.reply_text(
            "Неверный формат ссылки. Ожидаю: "
            "https://github.com/<owner>/<repo>/pull/<номер>"
        )
        return

    owner = match.group("owner")
    repo = match.group("repo")
    pull_number = int(match.group("number"))

    llm_integration = context.bot_data.get("llm_integration")
    manager = _find_mcp_manager_for_tool(llm_integration, "get_pull_request_files")
    if not manager:
        await update.message.reply_text(
            "*urp* Инструмент github_mcp не инициализирован. "
            "Проверь настройки MCP.",
            parse_mode=None,
        )
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    tool_result = await manager.call_tool(
        "get_pull_request_files",
        {
            "owner": owner,
            "repo": repo,
            "pull_number": pull_number,
            "include_contents": True,
            "max_file_size": 200000,
        },
        timeout=30.0,
    )

    if not tool_result.get("success"):
        await update.message.reply_text(
            f"Не удалось получить данные PR: {tool_result.get('error')}"
        )
        return

    try:
        payload = json.loads(tool_result.get("result") or "{}")
    except json.JSONDecodeError:
        await update.message.reply_text("Не смог распарсить ответ MCP.")
        return

    pr_data = payload.get("pull_request") or {}
    files = pr_data.get("files") or []

    llm_integration = context.bot_data.get("llm_integration")
    if not llm_integration:
        await update.message.reply_text("LLM не инициализирован.")
        return

    prompt, skipped_files = _build_pr_review_prompt(
        pr_data, files, max_chars=MAX_REVIEW_PROMPT_CHARS
    )
    if skipped_files:
        prompt += "\n\n[NOTICE] Пропущены файлы/части из-за ограничений: " + ", ".join(
            skipped_files[:10]
        )

    try:
        response_text = await llm_integration.process_message(user_id, prompt)
    except Exception as exc:
        logger.error("LLM analysis failed: %s", exc, exc_info=True)
        await update.message.reply_text("Не удалось выполнить анализ через LLM.")
        return

    max_len = context.bot_data.get("max_message_length", 3500)
    if len(response_text) > max_len:
        response_text = (
            response_text[: max_len - 20] + "\n\n…сообщение усечено по длине."
        )

    await update.message.reply_text(
        response_text, disable_web_page_preview=True, parse_mode=None
    )


async def set_github_username_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /set_github_username command - set GitHub username for user.

    Args:
        update: Telegram update object
        context: Bot context
    """
    user_id = update.effective_user.id
    state_manager = context.bot_data["state_manager"]
    db_manager = state_manager.db_manager

    # Check if username is provided
    if not context.args:
        # Show current username
        current_username = await db_manager.get_github_username(user_id)
        if current_username:
            message = f"""🐙 **Текущий GitHub username:** `{current_username}`

Чтобы изменить, используй:
`/set_github_username <новый_username>`"""
        else:
            message = """🐙 **GitHub username не установлен**

Установи свой GitHub username для получения ежедневных саммари:
`/set_github_username <твой_username>`

Например: `/set_github_username octocat`"""

        await update.message.reply_text(message)
        return

    # Set new username
    username = context.args[0].strip()

    # Remove @ if present
    if username.startswith("@"):
        username = username[1:]

    try:
        await db_manager.set_github_username(user_id, username)
        logger.info(f"User {user_id} set GitHub username: {username}")

        message = f"""✅ **GitHub username установлен:** `{username}`

*urp* Теперь можешь включить ежедневное саммари:
`/daily_summary_on`

Или протестируй саммари прямо сейчас:
`/test_daily_summary`"""

        await update.message.reply_text(message)

    except Exception as e:
        logger.error(f"Error setting GitHub username for user {user_id}: {e}")
        await update.message.reply_text(
            "*burp* Что-то пошло не так при установке username. Попробуй ещё раз."
        )


async def daily_summary_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /daily_summary_on command - enable daily GitHub summary.

    Args:
        update: Telegram update object
        context: Bot context
    """
    user_id = update.effective_user.id
    state_manager = context.bot_data["state_manager"]
    db_manager = state_manager.db_manager

    # Check if GitHub username is set
    github_username = await db_manager.get_github_username(user_id)
    if not github_username:
        message = """⚠️ **GitHub username не установлен!**

*urp* Сначала нужно указать свой GitHub username:
`/set_github_username <твой_username>`

Например: `/set_github_username octocat`"""
        await update.message.reply_text(message)
        return

    # Enable daily summary
    await db_manager.set_daily_summary_enabled(user_id, True)
    logger.info(f"User {user_id} enabled daily GitHub summary")

    message = f"""✅ **Ежедневное саммари GitHub включено!**

*burp* Теперь каждый день в **09:00 МСК** я буду отправлять тебе краткое саммари 
твоей активности в GitHub (@{github_username}) за предыдущий день.

📊 Включает:
• Количество коммитов
• Pull requests
• Issues
• Комментарии
• Другую активность

Можешь протестировать саммари прямо сейчас:
`/test_daily_summary`

Чтобы выключить: `/daily_summary_off`"""

    await update.message.reply_text(message)


async def daily_summary_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /daily_summary_off command - disable daily GitHub summary.

    Args:
        update: Telegram update object
        context: Bot context
    """
    user_id = update.effective_user.id
    state_manager = context.bot_data["state_manager"]
    db_manager = state_manager.db_manager

    # Disable daily summary
    await db_manager.set_daily_summary_enabled(user_id, False)
    logger.info(f"User {user_id} disabled daily GitHub summary")

    message = """🚫 **Ежедневное саммари GitHub выключено**

*urp* Больше не буду отправлять тебе ежедневные саммари.

Чтобы снова включить: `/daily_summary_on`"""

    await update.message.reply_text(message)


async def test_daily_summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /test_daily_summary command - test daily summary generation.

    Args:
        update: Telegram update object
        context: Bot context
    """
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested test daily summary")

    # Get daily summary manager from bot_data
    daily_summary_manager = context.bot_data.get("daily_summary_manager")

    if not daily_summary_manager:
        await update.message.reply_text(
            "*burp* Саммари менеджер не инициализирован. Попробуй перезапустить бота."
        )
        return

    # Show typing indicator
    await update.message.chat.send_action(ChatAction.TYPING)

    # Send test summary
    await update.message.reply_text(
        "🧪 *urp* Генерирую тестовое саммари... Подожди пару секунд..."
    )

    success = await daily_summary_manager.send_daily_summary_to_user(user_id)

    if not success:
        # Error message already sent by send_daily_summary_to_user
        logger.warning(f"Failed to send test summary to user {user_id}")
    else:
        logger.info(f"Successfully sent test summary to user {user_id}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in bot updates.

    Args:
        update: Telegram update object
        context: Bot context
    """
    logger.error(
        f"Update {update} caused error: {context.error}", exc_info=context.error
    )

    if update and update.effective_message:
        error_message = """*burp* Произошла какая-то ошибка. Не моя вина, конечно. 
Вероятно, проблема в квантовых флуктуациях или в твоём подключении к интернету.

Попробуй ещё раз."""

        try:
            await update.effective_message.reply_text(error_message)
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")
