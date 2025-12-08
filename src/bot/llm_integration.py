"""Integration layer between Telegram bot and LLM API."""

from ..llm import YandexLLMClient, RickMode, build_rick_prompt, ResponseProcessor
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
                temperature=user_temperature
            )
            
            # Extract text from response
            response_text = self.response_processor.extract_text(response)
            
            # Format response (no prefix needed for NORMAL mode)
            formatted_response = response_text.strip()
            
            # Log usage info
            usage = self.response_processor.get_usage_info(response)
            if usage:
                logger.debug(f"Token usage for user {user_id}: {usage}")
            
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

