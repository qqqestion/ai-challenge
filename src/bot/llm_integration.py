"""Integration layer between Telegram bot and LLM API."""

from typing import Any, Dict, Optional

from ..llm import (
    YandexLLMClient,
    RickMode,
    build_rick_prompt,
    ResponseProcessor,
)
from ..llm.models import ModelName
from ..llm.response_parsers import (
    ClaudeResponseParser,
    GPTResponseParser,
    GrokResponseParser,
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
        response_processor: ResponseProcessor
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
        # Get user state and temperature
        user_state = self.state_manager.get_user_state(user_id)
        user_temperature = user_state.temperature
        
        logger.info(f"Processing message for user {user_id} with temperature {user_temperature}")
        
        # Build prompt with NORMAL mode (only mode available)
        system_prompt, user_message = build_mode_prompt(RickMode.NORMAL, message)
        
        # Build complete prompt structure (without history)
        messages = build_rick_prompt(
            user_message=user_message,
            system_prompt=system_prompt,
            conversation_history=None
        )
        
        # Send to LLM API with user-specific temperature
        try:
            response = await self.llm_client.send_prompt(
                messages,
                temperature=user_temperature,
                model=user_state.model,
            )
            
            # Extract text from response
            self.response_processor.parser = self._select_parser(user_state.model)
            response_text = self.response_processor.extract_text(response)
            
            # Format response (no prefix needed for NORMAL mode)
            formatted_response = response_text.strip()
            
            # Extract metadata for logging and user output
            metadata = self.response_processor.get_metadata(response)
            if metadata:
                logger.debug(f"Response metadata for user {user_id}: {metadata}")

            metadata_block = self._format_metadata(metadata)
            if metadata_block:
                formatted_response = f"{formatted_response}\n\n{metadata_block}"
            
            logger.info(f"Generated response for user {user_id}: {len(formatted_response)} chars")
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"Failed to process message for user {user_id}: {e}", exc_info=True)
            raise
    
    async def reset_conversation(self, user_id: int):
        """Reset conversation state for user.
        
        Args:
            user_id: Telegram user ID
        """
        self.state_manager.reset_user_state(user_id)
        logger.info(f"Conversation reset for user {user_id}")
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.llm_client.close()
        logger.info("LLMIntegration cleanup completed")

    @staticmethod
    def _format_metadata(metadata: Optional[Dict[str, Any]]) -> Optional[str]:
        """Render metadata as monospace block for user output."""
        if not metadata or not isinstance(metadata, dict):
            return None

        lines = []
        usage = metadata.get("usage") or {}
        if isinstance(usage, dict):
            if usage.get("input_tokens") is not None:
                lines.append(f"usage.input_tokens = {usage.get('input_tokens')}")
            if usage.get("output_tokens") is not None:
                lines.append(f"usage.output_tokens = {usage.get('output_tokens')}")

        if metadata.get("cost") is not None:
            lines.append(f"cost = {metadata.get('cost')}")

        if metadata.get("time_ms") is not None:
            lines.append(f"time_ms = {metadata.get('time_ms')}")

        if not lines:
            return None
        return "```\n" + "\n".join(lines) + "\n```"

    @staticmethod
    def _select_parser(model: ModelName) -> Any:
        """Select parser based on model."""
        model_name = model.value if isinstance(model, ModelName) else str(model)
        lower_name = model_name.lower()

        if "claude" in lower_name:
            return ClaudeResponseParser()
        if "grok" in lower_name:
            return GrokResponseParser()
        return GPTResponseParser()

