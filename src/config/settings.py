"""Application settings management."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Telegram Bot Configuration
    telegram_bot_token: str = Field(
        ...,
        description="Telegram Bot Token from @BotFather"
    )

    # Eliza REST API Configuration
    eliza_token: str = Field(
        ...,
        description="OAuth token for Eliza OpenAI-compatible API"
    )
    llm_base_url: str = Field(
        ...,
        description="Base URL for Eliza REST API (host only, endpoint is derived by model)"
    )

    # LLM Settings
    llm_temperature: float = Field(
        default=0.8,
        ge=0.0,
        le=2.0,
        description="Temperature for LLM responses (0.0-2.0)"
    )
    llm_max_tokens: int = Field(
        default=2000,
        gt=0,
        description="Maximum tokens in LLM response"
    )

    # Application Settings
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    max_message_length: int = Field(
        default=4000,
        gt=0,
        description="Maximum message length from user"
    )
    user_state_cleanup_hours: int = Field(
        default=24,
        gt=0,
        description="Hours of inactivity before cleaning user state"
    )
    
    # SSL Settings
    ssl_verify: bool = Field(
        default=True,
        description="Verify SSL certificates (set to False for corporate proxies with self-signed certs)"
    )
    telegram_ssl_verify: bool = Field(
        default=False,
        description="Verify SSL certificates for Telegram API requests"
    )
    
    # MCP Settings
    mcp_enabled: bool = Field(
        default=True,
        description="Enable MCP (Model Context Protocol) tools integration"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @validator("telegram_bot_token")
    def validate_telegram_token(cls, v: str) -> str:
        """Validate Telegram bot token format."""
        if not v or v == "your_telegram_bot_token_here":
            raise ValueError(
                "TELEGRAM_BOT_TOKEN не указан или содержит значение по умолчанию. "
                "Получите токен через @BotFather в Telegram и укажите его в .env файле."
            )
        
        # Базовая проверка формата токена (число:строка)
        if ":" not in v:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN имеет неверный формат. "
                "Ожидается формат: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
            )
        
        parts = v.split(":", 1)
        if not parts[0].isdigit():
            raise ValueError(
                "TELEGRAM_BOT_TOKEN имеет неверный формат. "
                "Первая часть токена должна быть числом."
            )
        
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level value."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v_upper
    
    @validator("eliza_token")
    def validate_eliza_token(cls, v: str) -> str:
        """Validate Eliza token presence."""
        if not v or v == "your_eliza_token_here":
            raise ValueError(
                "ELIZA_TOKEN не указан или содержит значение по умолчанию. "
                "Получите токен доступа и укажите его в .env файле."
            )
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Returns:
        Settings: Application settings
        
    Raises:
        ValidationError: If required settings are missing or invalid
    """
    return Settings()


class YandexCloudSettings(BaseSettings):
    """Yandex Cloud settings loaded from environment variables.

    This is intentionally separate from `Settings` so standalone scripts (e.g. `yandex_cloud.py`)
    can run without requiring Telegram/Eliza-related env vars.
    """

    yandex_api_key: str = Field(
        ...,
        description="Yandex Cloud API key for OpenAI-compatible endpoint",
    )
    yandex_folder_id: str = Field(
        ...,
        description="Yandex Cloud folder id used in gpt://{folder}/... model URIs",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_yandex_cloud_settings() -> YandexCloudSettings:
    """Get cached Yandex Cloud settings instance."""
    return YandexCloudSettings()

