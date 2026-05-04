"""
services/voice/stt.py — Speech-to-Text.
Провайдеры: OpenAI Whisper (основной) → AssemblyAI (fallback).
"""

from __future__ import annotations
import os
import logging
import tempfile

logger = logging.getLogger(__name__)

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
ASSEMBLYAI_KEY = os.getenv("ASSEMBLYAI_API_KEY")

LANG_TO_WHISPER = {
    "ru": "ru", "kz": "kk", "uz": "uz", "tj": "tg",
    "tm": "tk", "kg": "ky", "by": "be", "en": "en",
}


async def transcribe_via_whisper(file_path: str, language: str) -> str | None:
    """Транскрибирует через OpenAI Whisper."""
    if not OPENAI_KEY:
        return None
    try:
        import openai
        client = openai.AsyncOpenAI(api_key=OPENAI_KEY)
        whisper_lang = LANG_TO_WHISPER.get(language, "ru")
        with open(file_path, "rb") as f:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language=whisper_lang,
            )
        return response.text.strip()
    except Exception as e:
        logger.warning(f"[STT] Whisper error: {e}")
        return None


async def transcribe_via_assemblyai(file_path: str) -> str | None:
    """Транскрибирует через AssemblyAI."""
    if not ASSEMBLYAI_KEY:
        return None
    try:
        import assemblyai as aai
        aai.settings.api_key = ASSEMBLYAI_KEY
        config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.universal)
        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe(file_path)
        return transcript.text
    except Exception as e:
        logger.warning(f"[STT] AssemblyAI error: {e}")
        return None


async def transcribe_voice(file_id: str, language: str, bot) -> str | None:
    """
    Скачивает голосовое сообщение и транскрибирует его.
    Возвращает текст или None при ошибке.
    """
    try:
        # Скачиваем файл от Telegram
        file = await bot.get_file(file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name

        await bot.download_file(file.file_path, destination=tmp_path)

        # Пробуем Whisper
        text = await transcribe_via_whisper(tmp_path, language)

        # Fallback — AssemblyAI
        if not text:
            text = await transcribe_via_assemblyai(tmp_path)

        import os
        os.unlink(tmp_path)

        return text

    except Exception as e:
        logger.error(f"[STT] Failed to transcribe voice: {e}")
        return None
