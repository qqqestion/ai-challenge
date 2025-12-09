"""Response parser abstractions and GPT implementation."""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any

from ..config import get_logger

logger = get_logger(__name__)


class ResponseParser(ABC):
    """Abstract response parser."""

    @abstractmethod
    def extract_text(self, response: Dict[str, Any]) -> str:
        """Extract assistant text from raw response."""

    @abstractmethod
    def validate_response(self, response: Dict[str, Any]) -> bool:
        """Validate response structure and content."""

    @abstractmethod
    def get_usage_info(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get token usage information if present."""


class GPTResponseParser(ResponseParser):
    """Parser for GPT-style responses (OpenAI-compatible)."""

    @staticmethod
    def _unwrap(response: Dict[str, Any]) -> Dict[str, Any]:
        """Support raw responses wrapped under 'response' key (as in gpt_response.json)."""
        if "response" in response and isinstance(response["response"], dict):
            return response["response"]
        return response

    def extract_text(self, response: Dict[str, Any]) -> str:
        payload = self._unwrap(response)

        choices = payload.get("choices", [])
        if not choices:
            raise ValueError("No choices in response")

        first_choice = choices[0]
        message = first_choice.get("message", {})
        content = message.get("content", "")

        if isinstance(content, list):
            text = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        else:
            text = str(content)

        text = text.strip()
        if not text:
            raise ValueError("Empty text in response")

        logger.debug(f"Extracted text: {len(text)} characters")
        return text

    def validate_response(self, response: Dict[str, Any]) -> bool:
        try:
            payload = self._unwrap(response)
            choices = payload.get("choices", [])
            if not choices:
                return False

            message = choices[0].get("message", {})
            content = message.get("content", "")

            if isinstance(content, list):
                text = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            else:
                text = str(content)

            return bool(text and text.strip())
        except (KeyError, IndexError, TypeError):
            return False

    def get_usage_info(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        payload = self._unwrap(response)
        usage = payload.get("usage", {})
        if usage:
            logger.debug(f"Token usage: {usage}")
            return usage
        return None


