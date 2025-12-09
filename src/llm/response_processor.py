"""Response processing utilities for LLM API responses."""

from typing import Dict, Optional
from ..config import get_logger
from .response_parsers import ResponseParser, GPTResponseParser

logger = get_logger(__name__)


class ResponseProcessor:
    """Processor for LLM API responses using pluggable parsers."""

    def __init__(self, parser: Optional[ResponseParser] = None):
        self.parser = parser or GPTResponseParser()
        logger.debug(f"ResponseProcessor initialized with parser: {self.parser.__class__.__name__}")

    def extract_text(self, response: Dict) -> str:
        """Extract text using configured parser."""
        try:
            return self.parser.extract_text(response)
        except Exception as e:
            logger.error(f"Failed to extract text from response: {e}")
            logger.debug(f"Response structure: {response}")
            raise

    def validate_response(self, response: Dict) -> bool:
        """Validate response structure using configured parser."""
        return self.parser.validate_response(response)

    def get_usage_info(self, response: Dict) -> Optional[Dict]:
        """Extract usage information using configured parser."""
        return self.parser.get_usage_info(response)

    @staticmethod
    def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
        """Sanitize and truncate text if needed."""
        text = " ".join(text.split())

        if max_length and len(text) > max_length:
            text = text[:max_length - 3] + "..."
            logger.warning(f"Text truncated to {max_length} characters")

        return text

