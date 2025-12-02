"""Telegram bot command and message handlers."""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from ..llm.modes import RickMode, ModePromptBuilder
from ..config import get_logger

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

Команды:
/start - это сообщение
/help - справка
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

⚙️ **Команды:**
/start - начать заново
/help - эта справка
/reset - очистить историю разговора

💡 **Советы:**
• Я помню контекст разговора
• Чем конкретнее вопрос, тем лучше ответ

*burp* Понятно? Тогда давай, задавай свои вопросы."""
    
    await update.message.reply_text(help_text)


async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mode command - show current mode.
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    user_id = update.effective_user.id
    logger.info(f"User {user_id} checking mode")
    
    message = f"""🎭 {ModePromptBuilder.get_mode_description(RickMode.NORMAL)}

*urp* Я всегда в этом режиме. Баланс сарказма и знаний, Морти."""
    
    await update.message.reply_text(message)


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

