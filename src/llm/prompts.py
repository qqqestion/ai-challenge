"""Prompt engineering utilities for Rick Sanchez."""

from typing import List, Dict, Optional


def build_rick_prompt(
    user_message: str,
    system_prompt: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
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
