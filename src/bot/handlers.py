"""Telegram bot command and message handlers."""

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from ..config import get_logger

logger = get_logger(__name__)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command.

    Args:
        update: Telegram update object
        context: Bot context
    """
    logger.info(f"User {update.effective_user.id} requested help")

    help_text = """*urp* Ладно, объясню для особо одарённых:

📝 **Как использовать:**
Просто пиши мне сообщения — я отвечу. Иногда саркастично, иногда полезно, 
всегда гениально.

🌡️ **Температура:**
/temperature — показать текущую температуру
/temperature <0.0-2.0> — установить температуру ответов

🧠 **Контекст (Ollama):**
/context — показать текущий размер контекста (или auto)
/context <число> — установить num_ctx (размер контекстного окна)
/context auto — вернуть в auto (по умолчанию)

✂️ **Лимит ответа (Ollama):**
/max_tokens — показать текущий лимит
/max_tokens <число> — установить max_tokens

📌 **Текущие настройки:**
/llm_settings — показать все параметры модели

⚙️ **Прочее:**
/reset — очистить историю разговора
/stats — показать статистику использования
/help — эта справка

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


async def max_tokens_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /max_tokens command - set max_tokens for user (normal responses only)."""
    user_id = update.effective_user.id
    state_manager = context.bot_data["state_manager"]

    if not context.args:
        current_value = await state_manager.get_user_max_tokens(user_id)
        message = f"""✂️ **Текущий max_tokens:** {current_value}

Используй: `/max_tokens <число>` чтобы изменить
Например: `/max_tokens 512`"""
        await update.message.reply_text(message)
        return

    try:
        value = int(context.args[0])
        if value <= 0:
            await update.message.reply_text("*urp* max_tokens должен быть > 0!")
            return

        old_value = await state_manager.get_user_max_tokens(user_id)
        await state_manager.set_user_max_tokens(user_id, value)

        await update.message.reply_text(
            f"✂️ **max_tokens установлен:** {value}\n\n"
            f"Старое значение: {old_value}\n"
            f"Новое значение: {value}\n\n"
            "Используй `/max_tokens` без параметров чтобы посмотреть текущее значение."
        )
    except ValueError:
        await update.message.reply_text(
            "*burp* Неверный формат!\n\n"
            "Используй: `/max_tokens <целое число>`\n"
            "Например: `/max_tokens 512`"
        )


async def context_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /context command - set num_ctx (context window) for user (normal responses only)."""
    user_id = update.effective_user.id
    state_manager = context.bot_data["state_manager"]

    if not context.args:
        current_value = await state_manager.get_user_num_ctx(user_id)
        current_display = "auto" if current_value is None else str(current_value)
        message = f"""🧠 **Текущий контекст (num_ctx):** {current_display}

Используй:
`/context <число>` чтобы изменить
`/context auto` чтобы вернуть в auto (по умолчанию)

Например: `/context 8192`"""
        await update.message.reply_text(message)
        return

    arg = context.args[0].strip().lower()
    if arg in {"auto", "default"}:
        old_value = await state_manager.get_user_num_ctx(user_id)
        await state_manager.set_user_num_ctx(user_id, None)
        old_display = "auto" if old_value is None else str(old_value)
        await update.message.reply_text(
            "🧠 **Контекст сброшен в auto**\n\n"
            f"Старое значение: {old_display}\n"
            "Новое значение: auto"
        )
        return

    try:
        value = int(arg)
        if value <= 0:
            await update.message.reply_text("*urp* num_ctx должен быть > 0 (или используй `auto`)!")
            return

        old_value = await state_manager.get_user_num_ctx(user_id)
        await state_manager.set_user_num_ctx(user_id, value)
        old_display = "auto" if old_value is None else str(old_value)
        await update.message.reply_text(
            f"🧠 **num_ctx установлен:** {value}\n\n"
            f"Старое значение: {old_display}\n"
            f"Новое значение: {value}\n\n"
            "Используй `/context` без параметров чтобы посмотреть текущее значение."
        )
    except ValueError:
        await update.message.reply_text(
            "*burp* Неверный формат!\n\n"
            "Используй:\n"
            "`/context <целое число>` или `/context auto`\n"
            "Например: `/context 8192`"
        )


async def llm_settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /llm_settings command - show current per-user LLM settings."""
    user_id = update.effective_user.id
    state_manager = context.bot_data["state_manager"]

    state = await state_manager.get_user_state(user_id)
    num_ctx_display = "auto" if state.num_ctx is None else str(state.num_ctx)

    message = (
        "📌 **Твои настройки LLM (только обычные ответы):**\n\n"
        f"🌡️ temperature = {state.temperature}\n"
        f"✂️ max_tokens = {state.max_tokens}\n"
        f"🧠 num_ctx = {num_ctx_display}\n\n"
        "Команды:\n"
        "- `/temperature <0.0-2.0>`\n"
        "- `/max_tokens <число>`\n"
        "- `/context <число|auto>`"
    )

    await update.message.reply_text(message)


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
