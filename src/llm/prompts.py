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
            "text": system_prompt
        })
    
    # Add conversation history if provided
    if conversation_history:
        messages.extend(conversation_history)
    
    # Add current user message
    messages.append({
        "role": "user",
        "text": user_message
    })
    
    return messages
