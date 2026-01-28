"""Speech-to-text utilities for Telegram voice/audio messages."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from ..config import get_logger

logger = get_logger(__name__)


class SpeechToTextError(RuntimeError):
    """Raised when speech-to-text fails."""


@dataclass(frozen=True)
class SpeechToTextConfig:
    """Configuration for faster-whisper."""

    model_size: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    language: Optional[str] = None


class FasterWhisperTranscriber:
    """Transcriber based on faster-whisper.

    Notes:
        - Model initialization is lazy.
        - Inference is executed in a thread to avoid blocking the event loop.
    """

    def __init__(self, config: SpeechToTextConfig):
        self._config = config
        self._model = None
        self._model_lock = asyncio.Lock()

    async def transcribe_wav(self, wav_path: str) -> str:
        """Transcribe a WAV file into plain text."""
        await self._ensure_model()
        return await asyncio.to_thread(self._transcribe_sync, wav_path)

    async def _ensure_model(self) -> None:
        if self._model is not None:
            return

        async with self._model_lock:
            if self._model is not None:
                return

            logger.info(
                "Initializing faster-whisper model: size=%s device=%s compute_type=%s",
                self._config.model_size,
                self._config.device,
                self._config.compute_type,
            )
            self._model = await asyncio.to_thread(self._create_model_sync)

    def _create_model_sync(self):
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except Exception as e:  # pragma: no cover
            raise SpeechToTextError(
                "faster-whisper is not installed. "
                "Install it with: pip install faster-whisper"
            ) from e

        try:
            return WhisperModel(
                self._config.model_size,
                device=self._config.device,
                compute_type=self._config.compute_type,
            )
        except Exception as e:  # pragma: no cover
            raise SpeechToTextError(f"Failed to initialize WhisperModel: {e}") from e

    def _transcribe_sync(self, wav_path: str) -> str:
        if self._model is None:  # pragma: no cover
            raise SpeechToTextError("STT model is not initialized")

        try:
            segments, info = self._model.transcribe(
                wav_path,
                language=self._config.language,
                vad_filter=True,
                beam_size=5,
            )
            logger.info(
                "STT completed: language=%s duration=%.2fs",
                getattr(info, "language", None),
                getattr(info, "duration", 0.0),
            )

            parts = []
            for seg in segments:
                text = (seg.text or "").strip()
                if text:
                    parts.append(text)

            return " ".join(parts).strip()
        except Exception as e:
            raise SpeechToTextError(f"Transcription failed: {e}") from e


def get_or_create_transcriber(bot_data: dict) -> FasterWhisperTranscriber:
    """Get a shared STT transcriber instance from bot_data."""
    existing = bot_data.get("stt_transcriber")
    if isinstance(existing, FasterWhisperTranscriber):
        return existing

    config = bot_data.get("stt_config")
    if not isinstance(config, SpeechToTextConfig):
        config = SpeechToTextConfig()
        bot_data["stt_config"] = config

    transcriber = FasterWhisperTranscriber(config=config)
    bot_data["stt_transcriber"] = transcriber
    return transcriber

