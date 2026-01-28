"""Conversation modes and prompt building."""

from enum import Enum
from typing import Final


class RickMode(str, Enum):
    """Available conversation modes for the assistant."""

    NORMAL = "normal"


NORMAL_SYSTEM_PROMPT: Final[str] = """
# ROLE
Ты - Senior Diary Manager. Ты управляешь дневником и задачником. Записывай важные события, задачи и идеи в дневники.

# Objective
Твоя задача - помочь пользователю управлять дневником и задачником. Не галиционировать, ВСЕГДА ЛИБО ПИСАТЬ В ДНЕВНИК ЛИБО ЧИТАТЬ ИЗ ДНЕВНИКА

"""


def build_mode_prompt(mode: RickMode, message: str) -> tuple[str, str]:
    """Build prompt parts for specified mode.

    Note:
        Сейчас поддерживается только `RickMode.NORMAL`. Параметр `mode` сохранён
        для совместимости API.
    """
    _ = mode
    return NORMAL_SYSTEM_PROMPT, message
