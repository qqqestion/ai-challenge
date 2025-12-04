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
        # Get user state and history
        user_state = self.state_manager.get_user_state(user_id)
        conversation_history = user_state.get_history()
        
        # Use default mode (NORMAL)
        current_mode = RickMode.NORMAL
        logger.info(f"Processing message for user {user_id} (history: {len(conversation_history)} messages)")
        
        # Build mode-specific prompt
        system_prompt, user_message = build_mode_prompt(current_mode, message)
        
        # Build complete prompt structure with history
        messages = build_rick_prompt(
            user_message=user_message,
            system_prompt=system_prompt,
            conversation_history=conversation_history if conversation_history else None
        )
        
        # Send to LLM API
        try:
            response = await self.llm_client.send_prompt(messages)
            
            # Extract and clean text from response (техническое извлечение из API Yandex)
            # extract_text already includes markdown code block cleaning
            response_text = self.response_processor.extract_text(response)
            
            # Save user message and assistant response to history
            user_state.add_message("user", user_message)
            user_state.add_message("assistant", response_text)
            
            # Log original model response
            logger.info(f"Original model response for user {user_id}: {response_text[:200]}...")
            logger.debug(f"Full original response for user {user_id}: {response_text}")
            logger.debug(f"History updated for user {user_id}: {len(user_state.message_history)} messages")
            
            # Get usage info для логирования (НЕ добавляем в ответ)
            usage = self.response_processor.get_usage_info(response)
            if usage:
                logger.info(f"Token usage for user {user_id}: prompt={usage.get('inputTextTokens', 0)}, "
                           f"completion={usage.get('completionTokens', 0)}, "
                           f"total={usage.get('totalTokens', 0)}")
            
            # Отправляем RAW ответ от модели без какой-либо обработки
            return response_text
            
        except Exception as e:
            logger.error(f"Failed to process message for user {user_id}: {e}", exc_info=True)
            raise
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.llm_client.close()
        logger.info("LLMIntegration cleanup completed")

