"""Error handling utilities for bot and LLM operations."""

import httpx
from telegram.error import TelegramError, NetworkError, TimedOut, BadRequest
from ..config import get_logger

logger = get_logger(__name__)


def format_error_message(error_type: str = "general") -> str:
    """Format user-friendly error message in Rick's style.
    
    Args:
        error_type: Type of error (general, network, api, timeout)
        
    Returns:
        Formatted error message
    """
    messages = {
        "general": """*urp* Чёрт, что-то пошло не так. Вероятно, проблема в квантовых 
флуктуациях или в том, что вселенная решила посмеяться надо мной. *burp*

Попробуй ещё раз через пару секунд.""",
        
        "network": """*burp* Окей, у меня проблемы с подключением к моим серверам. 
Может быть это межпространственные помехи, или просто интернет барахлит.

Попробуй снова через минуту.""",
        
        "api": """*urp* Мой AI модуль перегружен или временно недоступен. Даже гениям 
нужен перерыв на калибровку нейросетей.

Попытайся позже.""",
        
        "timeout": """*burp* Слушай, запрос занял слишком много времени. Может быть твой 
вопрос был настолько сложным, что даже мой гениальный мозг завис?

Попробуй сформулировать попроще или попытайся снова.""",
        
        "rate_limit": """*urp* Эй-эй, притормози! Ты задаёшь вопросы слишком быстро. 
Даже мой квантовый процессор не справляется с таким потоком.

Сделай паузу на минутку и попробуй снова.""",
        
        "invalid_request": """*burp* Что-то с твоим запросом не так. Проверь, что ты 
отправил корректное сообщение, а не какую-нибудь квантовую чушь.

Попробуй переформулировать."""
    }
    
    return messages.get(error_type, messages["general"])


def handle_llm_error(error: Exception) -> str:
    """Handle LLM API errors and return appropriate message.
    
    Args:
        error: Exception from LLM API call
        
    Returns:
        User-friendly error message
    """
    logger.error(f"LLM API error: {error}", exc_info=True)
    
    if isinstance(error, httpx.TimeoutException):
        return format_error_message("timeout")
    elif isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code
        
        if status_code == 429:
            return format_error_message("rate_limit")
        elif status_code >= 500:
            return format_error_message("api")
        elif status_code >= 400:
            return format_error_message("invalid_request")
        else:
            return format_error_message("api")
    elif isinstance(error, httpx.NetworkError):
        return format_error_message("network")
    else:
        return format_error_message("general")


def handle_telegram_error(error: Exception) -> str:
    """Handle Telegram API errors and return appropriate message.
    
    Args:
        error: Exception from Telegram API call
        
    Returns:
        User-friendly error message
    """
    logger.error(f"Telegram API error: {error}", exc_info=True)
    
    if isinstance(error, TimedOut):
        return format_error_message("timeout")
    elif isinstance(error, NetworkError):
        return format_error_message("network")
    elif isinstance(error, BadRequest):
        return format_error_message("invalid_request")
    elif isinstance(error, TelegramError):
        return format_error_message("api")
    else:
        return format_error_message("general")


def handle_network_error(error: Exception) -> str:
    """Handle general network errors.
    
    Args:
        error: Network exception
        
    Returns:
        User-friendly error message
    """
    logger.error(f"Network error: {error}", exc_info=True)
    return format_error_message("network")


class RickErrorHandler:
    """Centralized error handler for the bot."""
    
    @staticmethod
    def handle_error(error: Exception, context: str = "general") -> str:
        """Handle any error and return appropriate message.
        
        Args:
            error: Exception that occurred
            context: Context where error occurred
            
        Returns:
            User-friendly error message
        """
        logger.error(f"Error in {context}: {error}", exc_info=True)
        
        # Try specific handlers first
        if isinstance(error, (httpx.HTTPError, httpx.RequestError)):
            return handle_llm_error(error)
        elif isinstance(error, TelegramError):
            return handle_telegram_error(error)
        else:
            return format_error_message("general")

