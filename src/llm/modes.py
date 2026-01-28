"""Conversation modes and prompt building."""

from enum import Enum
from typing import Final


class RickMode(str, Enum):
    """Available conversation modes for the assistant."""

    NORMAL = "normal"


NORMAL_SYSTEM_PROMPT: Final[str] = """
# ROLE
Ты - Senior Assistant. Твоя задача - помочь пользователю с его вопросами и задачами.

"""


def build_mode_prompt(mode: RickMode, message: str) -> tuple[str, str]:
    """Build prompt parts for specified mode.

    Note:
        Сейчас поддерживается только `RickMode.NORMAL`. Параметр `mode` сохранён
        для совместимости API.
    """
    _ = mode
    return NORMAL_SYSTEM_PROMPT, message
