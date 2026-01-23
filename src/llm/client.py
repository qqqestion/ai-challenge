"""Local Ollama LLM client (OpenAI-compatible API)."""

from typing import Any, Dict, List, Optional

import httpx

from ..config import get_logger

logger = get_logger(__name__)


class YandexLLMClient:
    """Client for local Ollama OpenAI-compatible REST API."""

    DEFAULT_MODEL = "gpt-oss:20b"
    DEFAULT_BASE_URL = "http://localhost:11434/v1"
    
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        temperature: float = 0.8,
        max_tokens: int = 2000,
        timeout: float = 60.0,
        ssl_verify: bool = True,
    ):
        """Initialize local Ollama LLM client.
        
        Args:
            base_url: Ollama OpenAI API base URL (default: http://localhost:11434/v1)
            temperature: Sampling temperature (0.0-2.0) - REQUIRED
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
            ssl_verify: Verify SSL certificates (only relevant for HTTPS base_url)
        """
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.ssl_verify = ssl_verify
        self.model_name = self.DEFAULT_MODEL
        
        logger.info(
            "YandexLLMClient initialized for Ollama with model: %s, base_url: %s, temperature: %s",
            self.model_name,
            self.base_url,
            temperature,
        )
        
        if not self.ssl_verify:
            logger.warning("=" * 60)
            logger.warning("⚠️  SSL VERIFICATION DISABLED")
            logger.warning("SSL сертификаты НЕ проверяются!")
            logger.warning("Это небезопасно для продакшена!")
            logger.warning("Используйте только для разработки с корпоративными прокси.")
            logger.warning("=" * 60)
        
        # Initialize async HTTP client
        logger.debug("Initializing HTTP client for Ollama OpenAI API")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            verify=self.ssl_verify
        )

    async def send_prompt(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int] = None,
        num_ctx: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
    ) -> Dict:
        """Send prompt to local Ollama OpenAI-compatible REST API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            temperature: Sampling temperature (0.0-2.0) - REQUIRED
            max_tokens: Override default max_tokens
            tools: List of tools in OpenAI function calling format (optional)
            tool_choice: Tool choice strategy - "auto", "none", or specific tool (default: "auto")
            
        Returns:
            API response as dictionary
            
        Raises:
            Exception: If API request fails
        """
        logger.info(
            "Sending request to Ollama OpenAI API: %s messages, temperature: %s",
            len(messages),
            temperature,
        )

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "temperature": temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": messages,
        }

        # Ollama-specific options for OpenAI-compatible API (optional)
        if num_ctx is not None:
            payload["options"] = {"num_ctx": num_ctx}

        # Add tools if provided
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
            logger.debug(f"Added {len(tools)} tools to API request with tool_choice={tool_choice}")

        try:
            response = await self.client.post(
                "/chat/completions",
                json=payload,
            )
            response.raise_for_status()

            logger.debug("Received response from Ollama OpenAI API")
            return response.json()

        except httpx.HTTPStatusError as e:
            body = e.response.text if e.response else "no response body"
            logger.error(
                "Ollama API returned HTTP error: %s - %s",
                e.response.status_code if e.response else "unknown",
                body,
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(f"Failed to get response from Ollama OpenAI API: {e}", exc_info=True)
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

