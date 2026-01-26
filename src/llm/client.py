"""LLM client for local Ollama (OpenAI-ish response shape)."""

import time
from typing import Any, Dict, List, Optional, Union

import httpx

from ..config import get_logger
from .models import ModelName

logger = get_logger(__name__)

DEFAULT_OLLAMA_MODEL = "gpt-oss:20b"
DEFAULT_OLLAMA_CHAT_ENDPOINT = "/v1/chat/completions"


class YandexLLMClient:
    """Client for local Ollama running on standard port.

    Notes:
        - Keeps the class name for backward compatibility.
        - Returns responses in OpenAI Chat Completions-like shape to match existing parsers:
          {"choices": [{"message": {"role": "...", "content": "...", "tool_calls": [...]}}], "usage": {...}}
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        temperature: float = 0.8,
        model_name: Union[str, ModelName] = ModelName.GPT_4_O_MINI,
        max_tokens: int = 2000,
        timeout: float = 60.0,
        ssl_verify: bool = False,
        external_model_endpoints: Optional[Dict[str, str]] = None,
    ):
        """Initialize Ollama LLM client.

        Args:
            api_key: Unused for Ollama (kept for compatibility)
            base_url: Ollama base URL, e.g. "http://localhost:11434"
            model_name: Ignored; Ollama model is forced to DEFAULT_OLLAMA_MODEL
            temperature: Sampling temperature (0.0-2.0) - REQUIRED
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
            ssl_verify: Verify SSL certificates (False for self-signed certs)
            external_model_endpoints: Unused for Ollama (kept for compatibility)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.ssl_verify = ssl_verify
        self.external_model_endpoints = external_model_endpoints

        requested_model_name = (
            model_name.value if isinstance(model_name, ModelName) else str(model_name)
        )
        self.model_name = DEFAULT_OLLAMA_MODEL
        self._chat_url = f"{self.base_url}{DEFAULT_OLLAMA_CHAT_ENDPOINT}"

        if requested_model_name != self.model_name:
            logger.info(
                "LLM client uses Ollama model '%s' (ignoring requested model '%s')",
                self.model_name,
                requested_model_name,
            )
        else:
            logger.info("LLM client uses Ollama model '%s'", self.model_name)

        if not self.ssl_verify:
            logger.warning("=" * 60)
            logger.warning("⚠️  SSL VERIFICATION DISABLED")
            logger.warning("SSL сертификаты НЕ проверяются!")
            logger.warning("Это небезопасно для продакшена!")
            logger.warning("Используйте только для разработки с корпоративными прокси.")
            logger.warning("=" * 60)
        
        # Initialize async HTTP client
        logger.debug("Initializing HTTP client for Ollama")
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            verify=self.ssl_verify
        )

    @staticmethod
    def _normalize_openai_usage(response_json: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize OpenAI-compatible usage into input_tokens/output_tokens.

        Ollama's OpenAI-compatible endpoint typically returns:
            usage: {prompt_tokens, completion_tokens, total_tokens}
        Our code expects:
            usage: {input_tokens, output_tokens}
        """
        if not isinstance(response_json, dict):
            return response_json

        usage = response_json.get("usage")
        if not isinstance(usage, dict):
            return response_json

        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")

        normalized = dict(usage)
        if prompt_tokens is not None and normalized.get("input_tokens") is None:
            normalized["input_tokens"] = prompt_tokens
        if completion_tokens is not None and normalized.get("output_tokens") is None:
            normalized["output_tokens"] = completion_tokens

        response_json["usage"] = normalized
        return response_json

    async def send_prompt(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int] = None,
        model: Optional[Union[str, ModelName]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
    ) -> Dict:
        """Send prompt to local Ollama and return OpenAI-ish response dict.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            temperature: Sampling temperature (0.0-2.0) - REQUIRED
            max_tokens: Override default max_tokens
            model: Ignored; Ollama model is forced to DEFAULT_OLLAMA_MODEL
            tools: List of tools in OpenAI function calling format (optional)
            tool_choice: Ignored for Ollama (kept for compatibility)
            
        Returns:
            API response as dictionary
            
        Raises:
            Exception: If API request fails
        """
        logger.info(
            "Sending request to Ollama: %s messages, temperature=%s, tools=%s",
            len(messages),
            temperature,
            len(tools) if tools else 0,
        )

        selected_model = self.model_name
        payload: Dict[str, Any] = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": False,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        headers = {"Content-Type": "application/json"}
        started_at = time.time()

        try:
            response = await self.client.post(
                self._chat_url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()

            logger.debug("Received response from Ollama")
            response_json = response.json()

            if isinstance(response_json, dict) and response_json.get("error"):
                raise RuntimeError(f"Ollama error: {response_json.get('error')}")

            # Add request timing for our existing metadata extractor.
            elapsed_ms = int((time.time() - started_at) * 1000)
            if isinstance(response_json, dict) and response_json.get("elapsed_time_ms") is None:
                response_json["elapsed_time_ms"] = elapsed_ms

            return self._normalize_openai_usage(response_json)

        except httpx.HTTPStatusError as e:
            body = e.response.text if e.response else "no response body"
            logger.error(
                "Ollama returned HTTP error: %s - %s",
                e.response.status_code if e.response else "unknown",
                body,
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error("Failed to get response from Ollama: %s", e, exc_info=True)
            raise
    
    async def close(self):
        """Close HTTP client."""
        logger.debug("Closing YandexLLMClient HTTP client")
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

