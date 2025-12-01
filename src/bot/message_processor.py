"""Message processing logic for bot responses."""

from telegram import Update
from telegram.ext import ContextTypes
from ..config import get_logger

logger = get_logger(__name__)


async def process_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process user message and generate Rick's response.
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Get dependencies from context
    state_manager = context.bot_data["state_manager"]
    llm_integration = context.bot_data["llm_integration"]
    max_message_length = context.bot_data.get("max_message_length", 4000)
    
    # Validate message length
    if len(message_text) > max_message_length:
        logger.warning(f"User {user_id} sent message exceeding max length")
        await update.message.reply_text(
            f"*urp* Слушай, твоё сообщение слишком длинное. "
            f"Сократи до {max_message_length} символов, ладно?"
        )
        return
    
    # Check for spam/flood (basic check)
    user_state = state_manager.get_user_state(user_id)
    if user_state.message_count > 100:  # Simple rate limit
        logger.warning(f"User {user_id} might be spamming (message count: {user_state.message_count})")
    
    try:
        # Process message through LLM integration
        response_text = await llm_integration.process_message(user_id, message_text)
        
        # Send response (split if too long for Telegram)
        await send_response(update, response_text)
        
    except Exception as e:
        logger.error(f"Error generating response for user {user_id}: {e}", exc_info=True)
        raise


async def send_response(update: Update, text: str, chunk_size: int = 4000):
    """Send response to user, splitting into chunks if needed.
    
    Args:
        update: Telegram update object
        text: Response text to send
        chunk_size: Maximum size of each message chunk
    """
    # Telegram message limit is 4096 characters
    if len(text) <= chunk_size:
        await update.message.reply_text(text)
        return
    
    # Split into chunks
    chunks = split_text_into_chunks(text, chunk_size)
    
    logger.info(f"Splitting response into {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks):
        if i == 0:
            await update.message.reply_text(chunk)
        else:
            # Send subsequent chunks as replies to the original message
            await update.message.reply_text(f"...продолжение:\n\n{chunk}")


def split_text_into_chunks(text: str, chunk_size: int) -> list:
    """Split text into chunks at sentence boundaries.
    
    Args:
        text: Text to split
        chunk_size: Maximum size of each chunk
        
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by sentences (rough approach)
    sentences = text.replace(". ", ".|").replace("! ", "!|").replace("? ", "?|").split("|")
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def format_response_text(text: str, mode_prefix: str = "") -> str:
    """Format response text with optional mode prefix.
    
    Args:
        text: Response text
        mode_prefix: Prefix to add (e.g., "[НАУЧНЫЙ РЕЖИМ]")
        
    Returns:
        Formatted text
    """
    if mode_prefix:
        return f"{mode_prefix}{text}"
    return text

