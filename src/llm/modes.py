"""Rick Sanchez conversation modes and prompt building."""

from enum import Enum
from typing import Dict


class RickMode(str, Enum):
    """Available conversation modes for Rick Sanchez."""

    NORMAL = "normal"


class ModePromptBuilder:
    """Builder for mode-specific system prompts."""

    _MODE_SYSTEM_PROMPTS: Dict[RickMode, str] = {
        RickMode.NORMAL: """
# ROLE
Ты — Senior Assistant. Отвечай на вопросы пользователя по задачам и техническим реализациям в проекте с помощью MCP. 

# Examples
1. Вопрос по задаче
User: Как статус у задачи MAPI-44228
Assistant: Задача MAPI-44228 находится в статусе "In Progress"

2. Вопрос по технической реализации
User: Как подключить новый MCP сервер к боту?
Assistant: Для подключения нового MCP сервера к боту, необходимо выполнить следующие шаги:
*ТУТ ШАГИ, КОТОРЫЕ НУЖНО ВЫПОЛНИТЬ, ЧТОБЫ ПОДКЛЮЧИТЬ НОВЫЙ MCP СЕРВЕР К БОТУ*
        """
    }
    
    _MODE_PREFIXES: Dict[RickMode, str] = {
        RickMode.NORMAL: ""
    }
    
    @classmethod
    def get_mode_system_prompt(cls, mode: RickMode) -> str:
        """Get system prompt for specified mode.

        Args:
            mode: Rick conversation mode

        Returns:
            System prompt string
        """
        return cls._MODE_SYSTEM_PROMPTS.get(
            mode, cls._MODE_SYSTEM_PROMPTS[RickMode.NORMAL]
        )

    @classmethod
    def get_mode_prefix(cls, mode: RickMode) -> str:
        """Get response prefix for specified mode.

        Args:
            mode: Rick conversation mode

        Returns:
            Response prefix string
        """ 
        return cls._MODE_PREFIXES.get(mode, "")


def build_mode_prompt(mode: RickMode, message: str) -> tuple[str, str]:
    """Build complete prompt with mode-specific system prompt and user message.

    Args:
        mode: Rick conversation mode
        message: User message

    Returns:
        Tuple of (system_prompt, user_message)
    """
    system_prompt = ModePromptBuilder.get_mode_system_prompt(mode)
    return system_prompt, message
