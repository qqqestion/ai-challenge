"""LLM model definitions."""

from enum import Enum
from typing import Dict, Optional, Union


class ModelName(str, Enum):
    """Supported LLM models."""

    GPT_4_O_MINI = "gpt-4o-mini"
    CLAUDE_OPUS_4_5 = "claude-opus-4-5"
    GROK = "grok-2-vision"


# Default endpoints
DEFAULT_GPT_ENDPOINT = "/openai/v1/chat/completions"
DEFAULT_GROK_ENDPOINT = "/xai/v1/chat/completions"
DEFAULT_CLAUDE_ENDPOINT = "/anthropic/v1/messages"

# Built-in mapping for known enum models
MODEL_ENDPOINTS: Dict[ModelName, str] = {
    ModelName.GPT_4_O_MINI: DEFAULT_GPT_ENDPOINT,
    ModelName.GROK: DEFAULT_GROK_ENDPOINT,
    ModelName.CLAUDE_OPUS_4_5: DEFAULT_CLAUDE_ENDPOINT,
}

# External mapping for models that are not part of the enum
# Key: model name (str), Value: endpoint (str)
EXTERNAL_MODEL_ENDPOINTS: Dict[str, str] = {}

