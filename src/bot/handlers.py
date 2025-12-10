"""Telegram bot command and message handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from ..config import get_logger
from ..llm.models import ModelName

logger = get_logger(__name__)


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

🌡️ Можешь настроить температуру моих ответов через /temperature

Команды:
/start - это сообщение
/help - справка
/commands - список всех команд
/temperature - настройка температуры ответов
/change_model - выбрать модель
/reset - очистить историю

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

🌡️ **Настройка температуры:**
/temperature - показать текущую температуру
/temperature 0.0 - максимальная точность
/temperature 0.7 - баланс креативности
/temperature 2.0 - максимальная креативность

⚙️ **Команды:**
/start - начать заново
/help - эта справка
/change_model - выбрать модель
/reset - очистить историю разговора

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
    
    state_manager.reset_user_state(user_id)
    logger.info(f"User {user_id} reset conversation history")
    
    reset_message = """*urp* Окей, я стёр всю нашу историю. Чистый лист. 
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
        current_temp = state_manager.get_user_temperature(user_id)
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
        old_temp = state_manager.get_user_temperature(user_id)
        state_manager.set_user_temperature(user_id, temperature)
        
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
    
    logger.info(f"Message from user {user.id} ({user.username}): {message_text[:50]}...")
    
    # Show typing indicator
    await update.message.chat.send_action(ChatAction.TYPING)
    
    # Get message processor and process the message
    from .message_processor import process_user_message
    
    try:
        await process_user_message(update, context)
    except Exception as e:
        logger.error(f"Error processing message from user {user.id}: {e}", exc_info=True)
        
        error_message = """*urp* Чёрт, что-то пошло не так. Может быть мои системы 
перегружены, или просто вселенная решила посмеяться надо мной.

Попробуй ещё раз, или используй /reset если проблема повторяется."""
        
        await update.message.reply_text(error_message)


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

🌡️ **Настройки:**
/temperature - показать текущую температуру
/temperature <0.0-2.0> - установить температуру ответов

⚙️ **Управление:**
/reset - очистить историю разговора
/change_model - выбрать модель для ответов

💬 **Использование:**
Просто напиши любое сообщение (не команду) - я отвечу с установленной температурой.

*urp* Всё понятно? Используй команды и наслаждайся общением!"""
    
    await update.message.reply_text(commands_text)


def build_model_keyboard(active_model: ModelName | None) -> InlineKeyboardMarkup:
    """Build inline keyboard with available models.

    Args:
        active_model: Currently selected model to highlight.
    """
    buttons = []
    row = []
    for idx, model in enumerate(ModelName):
        label = f"✅ {model.value}" if active_model and model == active_model else model.value
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
    current_model = state_manager.get_user_model(user_id)
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

    model_id = data[len(prefix):]
    model = next((m for m in ModelName if m.value == model_id), None)
    if not model:
        await query.edit_message_text("Неизвестная модель. Попробуй ещё раз через /change_model.")
        return

    user_id = query.from_user.id
    state_manager = context.bot_data["state_manager"]
    state_manager.set_user_model(user_id, model)
    keyboard = build_model_keyboard(model)

    await query.edit_message_text(
        f"Модель установлена: {model.value}",
        reply_markup=keyboard,
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in bot updates.
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    logger.error(f"Update {update} caused error: {context.error}", exc_info=context.error)
    
    if update and update.effective_message:
        error_message = """*burp* Произошла какая-то ошибка. Не моя вина, конечно. 
Вероятно, проблема в квантовых флуктуациях или в твоём подключении к интернету.

Попробуй ещё раз."""
        
        try:
            await update.effective_message.reply_text(error_message)
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

