"""Rick Sanchez conversation modes and prompt building."""

from enum import Enum
from typing import Dict


class RickMode(str, Enum):
    """Available conversation modes for Rick Sanchez."""
    
    NORMAL = "normal"


class ModePromptBuilder:
    """Builder for mode-specific system prompts."""
    
    _MODE_SYSTEM_PROMPTS: Dict[RickMode, str] = {
        RickMode.NORMAL: """Ты эксперт в области биологии и генетики. Ты можешь ответить на любые вопросы по биологии и генетике. Ты знаешь все виды живых организмов, не только на Земле, но и во всей вселенной."""
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
        return cls._MODE_SYSTEM_PROMPTS.get(mode, cls._MODE_SYSTEM_PROMPTS[RickMode.NORMAL])
    
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
