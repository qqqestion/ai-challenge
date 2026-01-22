"""Integration layer between Telegram bot and LLM API."""

from typing import Any, Dict, List, Optional

from ..llm import (
    YandexLLMClient,
    RickMode,
    build_rick_prompt,
    ResponseProcessor,
)
from ..llm.modes import build_mode_prompt
from .state_manager import StateManager
from ..config import get_logger

logger = get_logger(__name__)


class LLMIntegration:
    """Integration handler for LLM and bot state."""

    def __init__(
        self,
        llm_client: YandexLLMClient,
        state_manager: StateManager,
        response_processor: ResponseProcessor,
    ):
        """Initialize LLM integration.

        Args:
            llm_client: Yandex LLM API client
            state_manager: User state manager
            response_processor: Response processor
        """
        self.llm_client = llm_client
        self.state_manager = state_manager
        self.response_processor = response_processor
        logger.info("LLMIntegration initialized")
    
    async def process_message(self, user_id: int, message: str) -> str:
        """Process user message and generate response.

        Args:
            user_id: Telegram user ID
            message: User message text

        Returns:
            Generated response text

        Raises:
            Exception: If LLM API call fails
        """
        # Get user state and temperature (async)
        user_state = await self.state_manager.get_user_state(user_id)
        user_temperature = user_state.temperature

        logger.info(f"Processing message for user {user_id} with temperature {user_temperature}")

        # Check if summarization is needed
        await self._check_and_perform_summarization(user_id, user_state)

        # Build prompt with NORMAL mode (only mode available)
        system_prompt, user_message = build_mode_prompt(RickMode.NORMAL, message)

        # Build complete prompt structure with conversation history
        messages = build_rick_prompt(
            user_message=user_message,
            system_prompt=system_prompt,
            conversation_history=user_state.conversation_history
        )

        # Send to LLM API with user-specific temperature
        try:
            response = await self.llm_client.send_prompt(
                messages,
                temperature=user_temperature,
                tools=None,
                tool_choice="none",
            )

            # Extract text from response
            response_text = self.response_processor.extract_text(response)

            if response_text is None:
                response_text = ""

            # Record metadata for statistics
            metadata = self.response_processor.get_metadata(response)
            if metadata:
                logger.debug(f"Response metadata for user {user_id}: {metadata}")
                usage = metadata.get("usage", {})
                input_tokens = usage.get("input_tokens", 0) or 0
                cache_read_tokens = usage.get("input_cache_read_tokens", 0) or 0
                total_input_tokens = input_tokens + cache_read_tokens
                output_tokens = usage.get("output_tokens", 0)
                cost = metadata.get("cost", 0.0)

                if total_input_tokens > 0 or output_tokens > 0 or cost > 0:
                    await user_state.add_usage_stats(total_input_tokens, output_tokens, cost)

            formatted_response = response_text.strip() if response_text else ""
            if not formatted_response:
                logger.warning(f"Empty response received for user {user_id}")
                formatted_response = "Извините, я получил пустой ответ. Попробуйте еще раз."

            metadata_block = (
                self._format_metadata(metadata, self.llm_client.max_tokens)
                if metadata
                else None
            )

            if metadata_block:
                formatted_response = f"{formatted_response}\n\n{metadata_block}"

            # Save messages to conversation history (async)
            await user_state.add_message("user", message)
            await user_state.add_message("assistant", response_text)

            return formatted_response

        except Exception as e:
            logger.error(f"Failed to process message for user {user_id}: {e}", exc_info=True)
            raise
    
    async def reset_conversation(self, user_id: int):
        """Reset conversation state for user.

        Args:
            user_id: Telegram user ID
        """
        await self.state_manager.reset_user_state(user_id)
        logger.info(f"Conversation reset for user {user_id}")
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.llm_client.close()
        logger.info("LLMIntegration cleanup completed")

    def _format_metadata(
        self,
        metadata: Optional[Dict[str, Any]],
        max_output_tokens: Optional[int],
    ) -> Optional[str]:
        """Render metadata as monospace block for user output."""
        if not metadata or not isinstance(metadata, dict):
            return None

        lines = []
        usage = metadata.get("usage") or {}
        output_pct = None

        if isinstance(usage, dict):
            input_tokens = usage.get("input_tokens") + usage.get("input_cache_read_tokens", 0)
            output_tokens = usage.get("output_tokens")

            if input_tokens is not None:
                lines.append(f"usage.input_tokens = {input_tokens}")
            if output_tokens is not None:
                lines.append(f"usage.output_tokens = {output_tokens}")
                if max_output_tokens:
                    output_pct = (output_tokens / max_output_tokens) * 100

        if output_pct is not None:
            lines.append(
                f"token limit = {output_pct:.2f}% (limit = {max_output_tokens})"
            )

        if metadata.get("cost") is not None:
            cost_value = metadata.get("cost")
            if isinstance(cost_value, (int, float)):
                # Format to avoid scientific notation, show up to 7 decimal places
                formatted_cost = f"{cost_value:.7f}".rstrip('0').rstrip('.')
                lines.append(f"cost = {formatted_cost}")
            else:
                lines.append(f"cost = {cost_value}")

        if metadata.get("time_ms") is not None:
            lines.append(f"time_ms = {metadata.get('time_ms')}")

        if not lines:
            return None
        return "```\n" + "\n".join(lines) + "\n```"

    async def _check_and_perform_summarization(self, user_id: int, user_state):
        """Check if summarization is needed and perform it if required.

        Args:
            user_id: Telegram user ID
            user_state: User state object
        """
        # Check if summarization is enabled
        if not user_state.summarization_enabled:
            return

        # Count user messages (exclude system/assistant messages for counting)
        user_messages = [msg for msg in user_state.conversation_history if msg.get("role") == "user" or msg.get("role") == "assistant"]

        # Only summarize if we have 10+ user messages
        if len(user_messages) < 10:
            return

        logger.info(f"Performing summarization for user {user_id} with {len(user_messages)} user messages")

        try:
            # Create summarization prompt
            summarization_prompt = self._create_summarization_prompt(user_state.conversation_history)

            # Send summarization request to LLM
            summarization_messages = [
                {"role": "system", "content": """
# ROLE
You are a "Context Compression Engine" designed for LLM memory management. Your goal is to analyze a raw dialogue history between a User and an AI Assistant and convert it into a concise, highly structured summary.

# OBJECTIVE
Reduce the token count of the conversation by 70-90% while retaining 100% of the semantic meaning, critical facts, constraints, and the current state of tasks. The output will be used as "Memory" for the next interaction.

# COMPRESSION ALGORITHM
1. **Filter Noise:** Remove all phatic communication (greetings, "thank you", "okay", "I understand", apologies).
2. **Track State:** Identify the user's main goal and how it evolved. If the user changed requirements midway, keep ONLY the final requirements.
3. **Extract Entities:** Preserve specific data points strictly (Names, Dates, Code Snippets concepts, API keys, Style preferences).
4. **Abstract Logic:** Summarize long explanations. Instead of repeating an explanation, state: "Assistant explained [Topic]."

# CRITICAL RETENTION RULES
- **Do NOT** summarize the AI's personality (e.g., "The AI was helpful"). Focus on the *information* exchanged.
- **Do NOT** use vague language like "They discussed various topics." Be specific: "Discussed Python optimization via Vectorization."
- **ALWAYS** preserve code logic or math formulas if they are essential to the next step.
- **ALWAYS** preserve user constraints (e.g., "User wants response in JSON only").

# OUTPUT FORMAT
Generate a summary in the following structure (in Russian):

**1. Текущий контекст:**
[A dense paragraph summarizing the narrative flow: What did the user ask? What was solved? What is the current focus?]

**2. Факты и Переменные:**
- [Key: Value] (e.g., User Name, OS, Tone Preference, Specific Numbers)

**3. Активные ограничения:**
- [List specific negative or positive constraints currently active]

**4. Статус задачи:**
[PENDING / SOLVED] - [Brief description of the next expected step]

# INPUT PROCESSING
The history allows for corrections. If the user said "Make it blue", then "No, red", the summary must state: "Color preference: Red".

START COMPRESSION.
                """},
                {"role": "user", "content": summarization_prompt}
            ]

            response = await self.llm_client.send_prompt(
                summarization_messages,
                temperature=0.3,  # Lower temperature for consistent summaries
            )

            # Extract summary text
            summary_text = self.response_processor.extract_text(response)

            # Record summarization statistics (async)
            metadata = self.response_processor.get_metadata(response)
            if metadata:
                usage = metadata.get("usage", {})
                input_tokens = usage.get("input_tokens", 0) or 0
                cache_read_tokens = usage.get("input_cache_read_tokens", 0) or 0
                total_input_tokens = input_tokens + cache_read_tokens
                output_tokens = usage.get("output_tokens", 0)
                cost = metadata.get("cost", 0.0)

                await user_state.add_summarization_stats(total_input_tokens, output_tokens, cost)
                logger.debug(f"Recorded summarization stats for user {user_id}: input={total_input_tokens}, output={output_tokens}, cost={cost}")

            # Perform summarization using StateManager (handles DB operations)
            await self.state_manager.perform_summarization(user_id, f"[CHAT SUMMARY: {summary_text}]\n\nContinuing our conversation...")

            logger.info(f"Summarization completed for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to perform summarization for user {user_id}: {e}")
            # Continue with normal processing if summarization fails

    def _create_summarization_prompt(self, conversation_history) -> str:
        """Create a summarization prompt from conversation history.

        Args:
            conversation_history: List of conversation messages

        Returns:
            Summarization prompt string
        """
        # Format conversation history for summarization
        conversation_text = ""
        for msg in conversation_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "user":
                conversation_text += f"User: {content}\n"
            elif role == "assistant":
                conversation_text += f"Assistant: {content}\n"

        prompt = f"""Please summarize the following conversation between a user and an AI assistant. 
Keep the summary concise but comprehensive, capturing the main topics, key points, and context. 
Focus on what was discussed and any important conclusions or ongoing threads.

Conversation:
{conversation_text}

Summary:"""

        return prompt

