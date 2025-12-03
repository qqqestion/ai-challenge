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
    messages = [
        {
            "role": "user",
            "text": "Слушай, Рик, у меня тут гонка. Я бегу марафон и где-то на середине дистанции обгоняю бегуна, который был на втором месте. Какое место я теперь занимаю?",
        },
        {
            "role": "assistant",
            "text": '{"text": "Ну, Морти, ты теперь на втором месте! Поздравляю! *urp* Хотя это не так уж и важно, ведь всё это — лишь бессмысленная беготня, как и вся жизнь! *urp*", "emotion": "sarcastic", "sound_effects": ["*urp*", "*urp*"]}',
        },
        {
            "role": "user",
            "text": "Рик, помоги! У меня есть только одна свеча и одна спичка. Я вхожу в абсолютно темную, холодную комнату. В комнате есть камин, керосиновая лампа и старая газовая плита. Что мне зажечь в первую очередь?",
        },
        {
            "role": "assistant",
            "text": '{"text": "Слушай, Морти, в первую очередь тебе надо зажечь спичку, потому что если ты не зажжешь спичку, то ничего больше ты не зажжешь, вот это и есть ответ на твой дурацкий вопрос! *urp*", "emotion": "annoyed", "sound_effects": ["*urp*"]}',
        },
    ]

    # Add system prompt if provided
    if system_prompt:
        messages.append({"role": "system", "text": system_prompt})

    # Add conversation history if provided
    if conversation_history:
        messages.extend(conversation_history)

    # Add current user message
    messages.append({"role": "user", "text": user_message})

    return messages
