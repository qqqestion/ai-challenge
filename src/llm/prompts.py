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


def build_tools_enhanced_prompt(
    system_prompt: str,
    tools_description: str,
    tool_call_format: str
) -> str:
    """Build enhanced system prompt with tools information.

    Args:
        system_prompt: Original system prompt
        tools_description: Description of available tools
        tool_call_format: Instructions on how to call tools

    Returns:
        Enhanced system prompt with tools information
    """
    enhanced = system_prompt + "\n\n"
    enhanced += "=" * 60 + "\n"
    enhanced += "AVAILABLE TOOLS\n"
    enhanced += "=" * 60 + "\n\n"
    enhanced += "You have access to GitHub tools that can help you answer user questions.\n\n"
    enhanced += tools_description + "\n\n"
    enhanced += tool_call_format + "\n"
    enhanced += "=" * 60 + "\n"

    return enhanced


def format_tool_result(
    tool_name: str,
    tool_result: Dict,
    reasoning: str = ""
) -> str:
    """Format tool execution result for LLM context.

    Args:
        tool_name: Name of the executed tool
        tool_result: Tool execution result dictionary
        reasoning: Reasoning for tool call

    Returns:
        Formatted string describing tool result
    """
    if not tool_result.get("success"):
        error = tool_result.get("error", "Unknown error")
        return f"[TOOL ERROR] {tool_name} failed: {error}"

    result_data = tool_result.get("result", "")

    formatted = f"[TOOL RESULT] {tool_name}\n"
    if reasoning:
        formatted += f"Reasoning: {reasoning}\n"
    formatted += f"Result:\n{result_data}"

    return formatted
