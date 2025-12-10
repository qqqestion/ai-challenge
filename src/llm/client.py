"""Eliza REST LLM API client."""

from typing import List, Dict, Optional, Any, Union

import httpx

from ..config import get_logger
from .models import ModelName, get_model_endpoint

logger = get_logger(__name__)


class YandexLLMClient:
    """Client for Eliza OpenAI-compatible REST API."""
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        temperature: float = 0.8,
        model_name: Union[str, ModelName] = ModelName.GPT_4_O_MINI,
        max_tokens: int = 2000,
        timeout: float = 60.0,
        ssl_verify: bool = True,
        external_model_endpoints: Optional[Dict[str, str]] = None,
    ):
        """Initialize Eliza LLM client.
        
        Args:
            api_key: Eliza OAuth token
            base_url: REST API base URL (host, without model-specific path)
            model_name: Model name (default: gpt-4o-mini)
            temperature: Sampling temperature (0.0-2.0) - REQUIRED
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
            ssl_verify: Verify SSL certificates (False for self-signed certs)
            external_model_endpoints: Mapping for non-enum models to endpoints
        """
        self.api_key = api_key
        self.model_name = (
            model_name.value if isinstance(model_name, ModelName) else str(model_name)
        )
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.ssl_verify = ssl_verify
        self.external_model_endpoints = external_model_endpoints
        
        logger.info(f"YandexLLMClient initialized with model: {model_name}, temperature: {temperature}")
        
        if not self.ssl_verify:
            logger.warning("=" * 60)
            logger.warning("⚠️  SSL VERIFICATION DISABLED")
            logger.warning("SSL сертификаты НЕ проверяются!")
            logger.warning("Это небезопасно для продакшена!")
            logger.warning("Используйте только для разработки с корпоративными прокси.")
            logger.warning("=" * 60)
        
        # Initialize async HTTP client
        logger.debug("Initializing HTTP client for Eliza REST API")
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            verify=self.ssl_verify
        )

    @staticmethod
    def _is_claude_model(model_name: str) -> bool:
        """Detect Claude/Anthropic models by name."""
        return "claude" in model_name.lower()
    
    async def send_prompt(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int] = None,
        model: Optional[Union[str, ModelName]] = None,
    ) -> Dict:
        """Send prompt to Eliza REST API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            temperature: Sampling temperature (0.0-2.0) - REQUIRED
            max_tokens: Override default max_tokens
            model: Override model for this request
            
        Returns:
            API response as dictionary
            
        Raises:
            Exception: If API request fails
        """
        logger.info(f"Sending request to Eliza REST API: {len(messages)} messages, temperature: {temperature}")
        
        selected_model = (
            model.value if isinstance(model, ModelName) else model
        ) or self.model_name

        payload: Dict[str, Any] = {
            "model": selected_model,
            "temperature": temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        if self._is_claude_model(selected_model):
            # Claude expects system prompt in top-level "system" field, not as a message
            system_prompt: Optional[str] = None
            stripped_messages: List[Dict[str, str]] = []

            for message in messages:
                if message.get("role") == "system":
                    content = message.get("content")
                    if content:
                        system_prompt = f"{system_prompt}\n\n{content}" if system_prompt else content
                    continue
                stripped_messages.append(message)

            payload["messages"] = stripped_messages
            if system_prompt:
                payload["system"] = system_prompt
        else:
            payload["messages"] = messages

        headers = {
            "Authorization": f"OAuth {self.api_key}",
            "Content-Type": "application/json",
        }

        endpoint = get_model_endpoint(selected_model, self.external_model_endpoints)
        url = f"{self.base_url}{endpoint}"

        try:
            response = await self.client.post(
                url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()

            logger.debug("Received response from Eliza REST API")
            return response.json()

        except httpx.HTTPStatusError as e:
            body = e.response.text if e.response else "no response body"
            logger.error(f"Eliza API returned HTTP error: {e.response.status_code if e.response else 'unknown'} - {body}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Failed to get response from Eliza REST API: {e}", exc_info=True)
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

