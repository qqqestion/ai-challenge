"""Response processing utilities for LLM API responses."""

import json
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
    
    @staticmethod
    def parse_json_response(response_text: str) -> Dict:
        """Parse JSON response from LLM.
        
        Args:
            response_text: Response text from LLM (should be JSON)
            
        Returns:
            Parsed JSON dictionary with default values on error
        """
        try:
            # Очистить от markdown если есть
            cleaned = response_text.strip()
            
            # Убрать markdown форматирование
            if "```json" in cleaned:
                # Найти содержимое между ```json и ```
                start = cleaned.find("```json") + 7
                end = cleaned.find("```", start)
                if end != -1:
                    cleaned = cleaned[start:end]
            elif "```" in cleaned:
                # Найти содержимое между ``` и ```
                start = cleaned.find("```") + 3
                end = cleaned.find("```", start)
                if end != -1:
                    cleaned = cleaned[start:end]
            
            # Парсим JSON
            parsed = json.loads(cleaned.strip())
            
            # Валидация обязательных полей
            if not isinstance(parsed.get("text"), str):
                logger.warning("Missing or invalid 'text' field in JSON response")
                raise ValueError("Missing 'text' field")
            
            # Добавляем defaults для опциональных полей
            parsed.setdefault("emotion", "neutral")
            parsed.setdefault("sound_effects", [])
            
            logger.debug(f"Successfully parsed JSON response: emotion={parsed['emotion']}, effects={len(parsed['sound_effects'])}")
            return parsed
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response text: {response_text[:200]}...")
            
            # Fallback: вернуть как plain text
            return {
                "text": response_text,
                "emotion": "neutral",
                "sound_effects": []
            }
    
    @staticmethod
    def validate_json_response(response: Dict) -> bool:
        """Validate JSON response structure.
        
        Args:
            response: Parsed JSON response
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["text", "emotion", "sound_effects"]
        
        # Проверка наличия полей
        if not all(field in response for field in required_fields):
            logger.warning("Missing required fields in JSON response")
            return False
        
        # Проверка типов
        if not isinstance(response["text"], str):
            logger.warning("Field 'text' is not a string")
            return False
        if not isinstance(response["emotion"], str):
            logger.warning("Field 'emotion' is not a string")
            return False
        if not isinstance(response["sound_effects"], list):
            logger.warning("Field 'sound_effects' is not a list")
            return False
        
        # Проверка что text не пустой
        if not response["text"].strip():
            logger.warning("Field 'text' is empty")
            return False
        
        logger.debug("JSON response validated successfully")
        return True

