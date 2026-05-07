"""
services/voice/stt.py — Speech-to-Text через Groq Whisper.
"""

from __future__ import annotations
import os
import logging
import tempfile

logger = logging.getLogger(__name__)

LANG_TO_WHISPER = {
    "ru": "ru", "kz": "kk", "uz": "uz", "tj": "tg",
    "tm": "tk", "kg": "ky", "by": "be", "en": "en",
}


async def transcribe_voice(file_id: str, language: str, bot) -> str | None:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        logger.warning("[STT] GROQ_API_KEY not set")
        return None
    try:
        import openai

        file = await bot.get_file(file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name
        await bot.download_file(file.file_path, destination=tmp_path)

        client = openai.AsyncOpenAI(
            api_key=key,
            base_url="https://api.groq.com/openai/v1",
            max_retries=0,
        )
        lang = LANG_TO_WHISPER.get(language, "ru")
        with open(tmp_path, "rb") as f:
            response = await client.audio.transcriptions.create(
                model="whisper-large-v3", file=f, language=lang,
            )

        os.unlink(tmp_path)
        text = response.text.strip()
        logger.info(f"[STT] Groq transcribed: {text[:50]}")
        return text

    except Exception as e:
        logger.error(f"[STT] Groq error: {e}")
        return None
