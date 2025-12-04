"""Response processing utilities for LLM API responses."""

from typing import Dict, Optional
from ..config import get_logger

logger = get_logger(__name__)


class ResponseProcessor:
    """Processor for LLM API responses."""
    
    @staticmethod
    def extract_text(response: Dict) -> str:
        """Extract text from Yandex LLM API response.
        
        Args:
            response: API response dictionary
            
        Returns:
            Extracted text content
            
        Raises:
            ValueError: If response format is invalid
        """
        try:
            # Yandex Cloud response format:
            # {
            #   "result": {
            #     "alternatives": [
            #       {
            #         "message": {
            #           "role": "assistant",
            #           "text": "..."
            #         },
            #         "status": "ALTERNATIVE_STATUS_FINAL"
            #       }
            #     ],
            #     "usage": {...},
            #     "modelVersion": "..."
            #   }
            # }
            
            result = response.get("result", {})
            alternatives = result.get("alternatives", [])
            
            if not alternatives:
                raise ValueError("No alternatives in response")
            
            first_alternative = alternatives[0]
            message = first_alternative.get("message", {})
            text = message.get("text", "")
            
            if not text:
                raise ValueError("Empty text in response")
            
            logger.debug(f"Extracted text: {len(text)} characters")
            cleaned_text = ResponseProcessor.clean_markdown_code_blocks(text)
            return cleaned_text.strip()
            
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Failed to extract text from response: {e}")
            logger.debug(f"Response structure: {response}")
            raise ValueError(f"Invalid response format: {e}")
    
    @staticmethod
    def clean_markdown_code_blocks(text: str) -> str:
        """Remove markdown code blocks (```) from text.
        
        Removes markdown code block markers from the beginning and end of text.
        Handles cases like:
        - ```json\n...\n```
        - ```\n...\n```
        - ```...```
        - ```json\n...```
        
        Args:
            text: Text that may contain markdown code blocks
            
        Returns:
            Cleaned text without markdown code block markers
        """
        if not text:
            return text
        
        # Strip whitespace first
        text = text.strip()
        
        # Check if text starts with ```
        if not text.startswith('```') and not text.endswith('```'):
            return text
        
        return text.replace('```json\n', '').replace('\n```', '').replace('```\n', '').strip()
    
    @staticmethod
    def get_usage_info(response: Dict) -> Optional[Dict]:
        """Extract usage information from response.
        
        Args:
            response: API response dictionary
            
        Returns:
            Usage information dictionary or None if not available
        """
        try:
            result = response.get("result", {})
            usage = result.get("usage", {})
            
            if usage:
                logger.debug(f"Token usage: {usage}")
                return usage
            
            return None
            
        except (KeyError, TypeError):
            return None
