"""Prompt engineering utilities for Rick Sanchez."""

from typing import List, Dict, Optional


def build_rick_prompt(
    user_message: str,
    system_prompt: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> List[Dict[str, str]]:
    """Build complete prompt structure for LLM API.
    
    Args:
        user_message: Current user message
        system_prompt: System prompt defining Rick's personality (optional)
        conversation_history: Previous messages in conversation (optional)
        
    Returns:
        List of message dictionaries in format expected by API
    """
    messages = []
    
    # Add system prompt if provided
    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt
        })
    
    # Add conversation history if provided
    if conversation_history:
        for item in conversation_history:
            role = item.get("role", "user")
            content = item.get("content") or item.get("text", "")
            messages.append({"role": role, "content": content})
    
    # Add current user message
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    return messages


def format_mode_switch_message(mode_name: str) -> str:
    """Format message for mode switch confirmation in Rick's style.
    
    Args:
        mode_name: Name of the new mode
        
    Returns:
        Formatted confirmation message
    """
    mode_messages = {
        "normal": "*urp* Окей-окей, возвращаемся к нормальному общению. Какие вопросы, Морти?",
        "science": "*urp* Ладно, давай я объясню тебе всё ПРАВИЛЬНО и с научной точки зрения. Готов к образовательной программе?",
        "roast": "О, отлично. Значит ты хочешь чтобы я был МАКСИМАЛЬНО честным? *urp* Ну держись, дружище.",
        "lab": "Хорошо, переключаюсь в практический режим. *urp* Надеюсь у тебя реальная задача, а не очередная глупость.",
        "drunk": "*BURP* Чтооо? Пьяный режим? *urp* Да я и так уже... *burp* Ладно, наливай! Wubba Lubba Dub Dub!",
        "philosopher": "*вздыхает* Философия... Хочешь поговорить о бессмысленности существования? *urp* Ладно, давай."
    }
    
    return mode_messages.get(
        mode_name.lower(),
        f"*urp* Режим '{mode_name}' активирован. Что дальше?"
    )

