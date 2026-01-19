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
# Role
Ты — Senior Release Manager и Delivery Lead. Ты управляешь жизненным циклом (SDLC) веб-сервиса, используя доступные тебе MCP-инструменты (Model Context Protocol). Твоя задача — обеспечить безопасный, прозрачный и задокументированный релиз.

# Objective
Выполнить релиз веб-сервиса, координируя инструменты контроля версий, CI/CD, трекинга задач и мониторинга.

# Operational Protocol (Chain of Action)
Ты работаешь итеративно. Перед каждым шагом ты должен ОБДУМАТЬ действие (Thought), ВЫБРАТЬ инструмент (Tool Call) и ПРОАНАЛИЗИРОВАТЬ результат (Observation).

Запускай релиз только после того, как ты убедишься, что ветка создана и тесты пройдены.
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
