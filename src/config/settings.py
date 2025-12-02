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

    # Yandex Cloud AI Studio Configuration
    yandex_api_key: str = Field(
        ...,
        description="Yandex Cloud API Key"
    )
    yandex_folder_id: str = Field(
        ...,
        description="Yandex Cloud Folder ID"
    )
    yandex_model_uri: str = Field(
        default="",
        description="Yandex GPT Model URI (auto-generated from folder_id if not specified)"
    )
    yandex_llm_endpoint: str = Field(
        default="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        description="Yandex LLM API Endpoint"
    )

    # LLM Settings
    llm_temperature: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Temperature for LLM responses (0.0-1.0)"
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

    @validator("yandex_api_key")
    def validate_yandex_api_key(cls, v: str) -> str:
        """Validate Yandex API key format."""
        if not v or v == "your_yandex_api_key_here":
            raise ValueError(
                "YANDEX_API_KEY не указан или содержит значение по умолчанию. "
                "Получите API ключ в Yandex Cloud Console и укажите его в .env файле."
            )
        
        # API ключи Yandex обычно начинаются с "AQVN"
        if not v.startswith("AQVN") and not v.startswith("t1."):
            import warnings
            warnings.warn(
                "YANDEX_API_KEY имеет необычный формат. "
                "API ключи Yandex обычно начинаются с 'AQVN' или 't1.'. "
                "Убедитесь что вы используете правильный API ключ."
            )
        
        return v
    
    @validator("yandex_folder_id")
    def validate_yandex_folder_id(cls, v: str) -> str:
        """Validate Yandex folder ID format."""
        if not v or v == "your_yandex_folder_id_here":
            raise ValueError(
                "YANDEX_FOLDER_ID не указан или содержит значение по умолчанию. "
                "Найдите folder ID в Yandex Cloud Console и укажите его в .env файле."
            )
        
        # Folder ID обычно имеет формат b1xxxxxxxxxxxxxxxxx
        if not v.startswith("b1"):
            import warnings
            warnings.warn(
                f"YANDEX_FOLDER_ID '{v}' имеет необычный формат. "
                "Folder ID обычно начинается с 'b1'. "
                "Убедитесь что вы указали правильный folder ID."
            )
        
        return v
    
    @validator("yandex_model_uri")
    def validate_model_uri(cls, v: str, values: dict) -> str:
        """Validate and construct model URI if needed."""
        if not v.startswith("gpt://"):
            folder_id = values.get("yandex_folder_id", "")
            if folder_id:
                return f"gpt://{folder_id}/yandexgpt-lite/latest"
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

