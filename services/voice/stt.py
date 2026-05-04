"""
services/voice/stt.py — Speech-to-Text.
Провайдеры: OpenAI Whisper (основной) → AssemblyAI (fallback).
"""

from __future__ import annotations
import os
import asyncio
import logging
import tempfile

logger = logging.getLogger(__name__)

LANG_TO_WHISPER = {
    "ru": "ru", "kz": "kk", "uz": "uz", "tj": "tg",
    "tm": "tk", "kg": "ky", "by": "be", "en": "en",
}

LANG_TO_ASSEMBLYAI = {
    "ru": "ru", "kz": "kk", "uz": "uz", "en": "en",
}


async def transcribe_via_whisper(file_path: str, language: str) -> str | None:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    try:
        import openai
        client = openai.AsyncOpenAI(api_key=key, max_retries=0)
        whisper_lang = LANG_TO_WHISPER.get(language, "ru")
        with open(file_path, "rb") as f:
            response = await client.audio.transcriptions.create(
                model="whisper-1", file=f, language=whisper_lang,
            )
        return response.text.strip()
    except Exception as e:
        logger.warning(f"[STT] Whisper error: {e}")
        return None


async def transcribe_via_assemblyai(file_path: str, language: str = "ru") -> str | None:
    key = os.getenv("ASSEMBLYAI_KEY") or os.getenv("ASSEMBLYAI_API_KEY")
    if not key:
        return None
    try:
        import httpx

        def _transcribe():
            headers = {"authorization": key}

            # 1. Загружаем файл
            with open(file_path, "rb") as f:
                upload_resp = httpx.post(
                    "https://api.assemblyai.com/v2/upload",
                    headers=headers,
                    content=f.read(),
                )
            upload_resp.raise_for_status()
            audio_url = upload_resp.json()["upload_url"]

            # 2. Создаём транскрипцию
            lang_code = LANG_TO_ASSEMBLYAI.get(language, "ru")
            transcript_resp = httpx.post(
                "https://api.assemblyai.com/v2/transcript",
                headers=headers,
                json={"audio_url": audio_url, "language_code": lang_code},
            )
            transcript_resp.raise_for_status()
            transcript_id = transcript_resp.json()["id"]

            # 3. Поллинг результата
            import time
            for _ in range(60):
                result = httpx.get(
                    f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                    headers=headers,
                )
                data = result.json()
                if data["status"] == "completed":
                    return data.get("text", "")
                elif data["status"] == "error":
                    raise RuntimeError(data.get("error", "Unknown error"))
                time.sleep(2)

            raise RuntimeError("AssemblyAI timeout")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _transcribe)
    except Exception as e:
        logger.warning(f"[STT] AssemblyAI error: {e}")
        return None


async def transcribe_voice(file_id: str, language: str, bot) -> str | None:
    try:
        file = await bot.get_file(file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name
        await bot.download_file(file.file_path, destination=tmp_path)

        text = await transcribe_via_whisper(tmp_path, language)
        if not text:
            logger.info("[STT] Whisper unavailable, trying AssemblyAI...")
            text = await transcribe_via_assemblyai(tmp_path, language)

        os.unlink(tmp_path)
        return text
    except Exception as e:
        logger.error(f"[STT] Failed to transcribe voice: {e}")
        return None
