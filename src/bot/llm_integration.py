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
        # Get user state and current mode
        user_state = self.state_manager.get_user_state(user_id)
        current_mode = user_state.current_mode
        
        logger.info(f"Processing message for user {user_id} in mode {current_mode.value}")
        
        # Build mode-specific prompt
        system_prompt, user_message = build_mode_prompt(current_mode, message)
        
        # Build complete prompt structure (without history)
        messages = build_rick_prompt(
            user_message=user_message,
            system_prompt=system_prompt,
            conversation_history=None
        )
        
        # Send to LLM API
        try:
            response = await self.llm_client.send_prompt(messages)
            
            # Extract raw text from response (техническое извлечение из API Yandex)
            response_text = self.response_processor.extract_text(response)
            
            # Log original model response
            logger.info(f"Original model response for user {user_id}: {response_text[:200]}...")
            logger.debug(f"Full original response for user {user_id}: {response_text}")
            
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
    
    async def change_mode(self, user_id: int, new_mode: RickMode) -> str:
        """Change conversation mode for user.
        
        Args:
            user_id: Telegram user ID
            new_mode: New Rick mode
            
        Returns:
            Confirmation message in new mode style
        """
        old_mode = self.state_manager.get_user_mode(user_id)
        self.state_manager.set_user_mode(user_id, new_mode)
        
        logger.info(f"User {user_id} mode changed: {old_mode.value} -> {new_mode.value}")
        
        # Generate confirmation in new mode style
        from ..llm.prompts import format_mode_switch_message
        confirmation = format_mode_switch_message(new_mode.value)
        
        return confirmation
    
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

