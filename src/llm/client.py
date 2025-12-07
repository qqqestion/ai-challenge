"""Yandex Cloud LLM API client."""

import asyncio
from typing import List, Dict, Optional
from yandex_cloud_ml_sdk import YCloudML
from ..config import get_logger

logger = get_logger(__name__)


class YandexLLMClient:
    """Client for Yandex Cloud Foundation Models API using official SDK."""
    
    def __init__(
        self,
        api_key: str,
        folder_id: str,
        model_uri: str,
        endpoint: str,
        temperature: float = 0.8,
        max_tokens: int = 2000,
        timeout: float = 60.0,
        max_retries: int = 3,
        ssl_verify: bool = True
    ):
        """Initialize Yandex LLM client.
        
        Args:
            api_key: Yandex Cloud API key
            folder_id: Yandex Cloud folder ID
            model_uri: Model URI (e.g., gpt://folder_id/yandexgpt-lite/latest)
            endpoint: API endpoint URL (not used with SDK, kept for compatibility)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts (not used with SDK)
            ssl_verify: Verify SSL certificates (False for self-signed certs)
        """
        self.api_key = api_key
        self.folder_id = folder_id
        self.model_uri = model_uri
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        if not ssl_verify:
            logger.warning("=" * 60)
            logger.warning("⚠️  SSL VERIFICATION DISABLED")
            logger.warning("SSL сертификаты НЕ проверяются!")
            logger.warning("Это небезопасно для продакшена!")
            logger.warning("Используйте только для разработки с корпоративными прокси.")
            logger.warning("=" * 60)
        
        # Initialize Yandex Cloud ML SDK
        logger.debug("Initializing YCloudML SDK")
        self.sdk = YCloudML(
            folder_id=folder_id,
            auth=api_key
        )
        
        # Extract model name from model_uri (e.g., "gpt://folder/yandexgpt/latest" -> "yandexgpt")
        # Model URI format: gpt://folder_id/model_name/version
        model_name = "yandexgpt"  # default
        if model_uri and "://" in model_uri:
            parts = model_uri.split("://")[1].split("/")
            if len(parts) >= 2:
                model_name = parts[1]
        
        logger.debug(f"Using model: {model_name}")
        self.model_name = model_name
        self._model = None
    
    def _get_model(self):
        """Get or create model instance with current settings."""
        # Create new model instance with current temperature/max_tokens
        return self.sdk.models.completions(self.model_name).configure(
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
    
    async def send_prompt(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """Send prompt to Yandex LLM API using SDK.
        
        Args:
            messages: List of message dictionaries with 'role' and 'text' keys
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            
        Returns:
            API response as dictionary with SDK result format
            
        Raises:
            Exception: If API request fails
        """
        logger.debug(f"Sending request to Yandex LLM API: {len(messages)} messages")
        
        # Get model with configuration
        model = self.sdk.models.completions(self.model_name).configure(
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens
        )
        
        try:
            # Run deferred operation (asynchronous)
            operation = model.run_deferred(messages)
            
            # Wait for completion with polling
            # SDK's wait() is synchronous, so we run it in executor
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                operation.wait
            )
            
            logger.debug("Received response from Yandex LLM API")
            
            # Convert SDK result to dictionary format expected by response processor
            # SDK returns GPTModelResult object, we need to convert it
            response_dict = self._convert_sdk_result_to_dict(result)
            
            return response_dict
            
        except Exception as e:
            logger.error(f"Failed to get response from Yandex LLM API: {e}", exc_info=True)
            raise
    
    def _convert_sdk_result_to_dict(self, result) -> Dict:
        """Convert SDK result object to dictionary format.
        
        Args:
            result: SDK GPTModelResult object
            
        Returns:
            Dictionary in format compatible with response processor
        """
        # SDK returns GPTModelResult with alternatives
        # We need to convert it to the format expected by ResponseProcessor
        try:
            # Get first alternative
            if hasattr(result, 'alternatives') and result.alternatives:
                alternative = result.alternatives[0]
                
                response_dict = {
                    "result": {
                        "alternatives": [
                            {
                                "message": {
                                    "role": alternative.role if hasattr(alternative, 'role') else "assistant",
                                    "text": alternative.text if hasattr(alternative, 'text') else str(alternative)
                                },
                                "status": alternative.status if hasattr(alternative, 'status') else "ALTERNATIVE_STATUS_FINAL"
                            }
                        ],
                        "usage": result.usage.__dict__ if hasattr(result, 'usage') else {},
                        "modelVersion": result.model_version if hasattr(result, 'model_version') else ""
                    }
                }
            else:
                # Fallback: try to extract text directly
                text = str(result)
                response_dict = {
                    "result": {
                        "alternatives": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "text": text
                                },
                                "status": "ALTERNATIVE_STATUS_FINAL"
                            }
                        ],
                        "usage": {},
                        "modelVersion": ""
                    }
                }
            
            logger.debug(f"Converted SDK result to dict: {len(response_dict.get('result', {}).get('alternatives', [{}])[0].get('message', {}).get('text', ''))} chars")
            return response_dict
            
        except Exception as e:
            logger.error(f"Failed to convert SDK result to dict: {e}", exc_info=True)
            # Return minimal valid structure
            return {
                "result": {
                    "alternatives": [
                        {
                            "message": {
                                "role": "assistant",
                                "text": str(result)
                            },
                            "status": "ALTERNATIVE_STATUS_FINAL"
                        }
                    ],
                    "usage": {},
                    "modelVersion": ""
                }
            }
    
    async def close(self):
        """Close SDK client (no-op for SDK, kept for compatibility)."""
        logger.debug("Closing YandexLLMClient (SDK cleanup)")
        # SDK doesn't require explicit cleanup
        pass
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

