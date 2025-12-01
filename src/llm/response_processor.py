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
            return text.strip()
            
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Failed to extract text from response: {e}")
            logger.debug(f"Response structure: {response}")
            raise ValueError(f"Invalid response format: {e}")
    
    @staticmethod
    def validate_response(response: Dict) -> bool:
        """Validate response structure.
        
        Args:
            response: API response dictionary
            
        Returns:
            True if response is valid, False otherwise
        """
        try:
            result = response.get("result", {})
            alternatives = result.get("alternatives", [])
            
            if not alternatives:
                return False
            
            first_alternative = alternatives[0]
            message = first_alternative.get("message", {})
            text = message.get("text", "")
            
            return bool(text and text.strip())
            
        except (KeyError, IndexError, TypeError):
            return False
    
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
    
    @staticmethod
    def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
        """Sanitize and truncate text if needed.
        
        Args:
            text: Text to sanitize
            max_length: Maximum allowed length (optional)
            
        Returns:
            Sanitized text
        """
        # Remove excessive whitespace
        text = " ".join(text.split())
        
        # Truncate if needed
        if max_length and len(text) > max_length:
            text = text[:max_length - 3] + "..."
            logger.warning(f"Text truncated to {max_length} characters")
        
        return text

