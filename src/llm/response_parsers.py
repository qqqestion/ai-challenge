"""Response parser abstractions and GPT implementation."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

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
    def get_metadata(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get metadata (usage, cost, time) from raw response."""

    def get_usage_info(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Backward-compatible usage extraction via metadata."""
        metadata = self.get_metadata(response) or {}
        usage = metadata.get("usage")
        if usage:
            logger.debug(f"Token usage: {usage}")
        return usage


def _unwrap_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Support raw responses wrapped under 'response' key (as in saved *.json)."""
    if "response" in response and isinstance(response["response"], dict):
        return response["response"]
    return response


def _build_metadata_from_root(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Collect metadata from the root-level fields."""
    if not isinstance(response, dict):
        return None

    metadata: Dict[str, Any] = {}

    root_usage = response.get("usage") or {}
    if isinstance(root_usage, dict):
        usage: Dict[str, Any] = {}
        if root_usage.get("input_tokens") is not None:
            usage["input_tokens"] = root_usage.get("input_tokens")
        if root_usage.get("output_tokens") is not None:
            usage["output_tokens"] = root_usage.get("output_tokens")
        if usage:
            metadata["usage"] = usage

    if response.get("cost") is not None:
        metadata["cost"] = response.get("cost")

    if response.get("elapsed_time_ms") is not None:
        metadata["time_ms"] = response.get("elapsed_time_ms")

    return metadata or None


class GPTResponseParser(ResponseParser):
    """Parser for GPT-style responses (OpenAI-compatible)."""

    def extract_text(self, response: Dict[str, Any]) -> str:
        payload = _unwrap_response(response)

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
            payload = _unwrap_response(response)
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

    def get_metadata(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return _build_metadata_from_root(response)


class GrokResponseParser(ResponseParser):
    """Parser for Grok-style responses."""

    def extract_text(self, response: Dict[str, Any]) -> str:
        payload = _unwrap_response(response)

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
            payload = _unwrap_response(response)
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

    def get_metadata(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return _build_metadata_from_root(response)


class ClaudeResponseParser(ResponseParser):
    """Parser for Claude-style responses."""

    def extract_text(self, response: Dict[str, Any]) -> str:
        payload = _unwrap_response(response)

        content = payload.get("content") or []
        if not isinstance(content, list):
            raise ValueError("Content is not a list in Claude response")

        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_part = item.get("text", "")
                if text_part:
                    parts.append(str(text_part))
            elif isinstance(item, str):
                parts.append(item)

        text = "".join(parts).strip()
        if not text:
            raise ValueError("Empty text in Claude response")

        logger.debug(f"Extracted text: {len(text)} characters")
        return text

    def validate_response(self, response: Dict[str, Any]) -> bool:
        try:
            payload = _unwrap_response(response)
            content = payload.get("content") or []
            if not isinstance(content, list) or not content:
                return False

            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_part = item.get("text", "")
                    if text_part:
                        parts.append(str(text_part))
                elif isinstance(item, str):
                    parts.append(item)

            text = "".join(parts).strip()
            return bool(text)
        except (KeyError, IndexError, TypeError):
            return False

    def get_metadata(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return _build_metadata_from_root(response)


