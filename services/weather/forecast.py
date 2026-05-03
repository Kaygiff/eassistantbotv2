"""
services/weather/forecast.py — Прогноз погоды через OpenWeatherMap.
Кэш в Redis на 30 минут.
"""

from __future__ import annotations
import os
import logging

import httpx

from db.redis import get_redis, weather_cache_key

logger = logging.getLogger(__name__)
OWM_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
CACHE_TTL = 1800  # 30 минут

WEATHER_ICONS = {
    "Clear": "☀️", "Clouds": "☁️", "Rain": "🌧", "Drizzle": "🌦",
    "Thunderstorm": "⛈", "Snow": "❄️", "Mist": "🌫", "Fog": "🌫",
    "Haze": "🌫", "Smoke": "💨", "Dust": "💨", "Sand": "💨",
    "Tornado": "🌪", "Squall": "💨",
}

LANG_MAP = {
    "ru": "ru", "kz": "ru", "by": "ru", "uz": "uz",
    "tj": "ru", "tm": "ru", "kg": "ru", "en": "en",
}


async def get_weather(city: str, language: str = "ru") -> str:
    """Возвращает отформатированный прогноз погоды для города."""
    import json

    redis = get_redis()
    cache_key = weather_cache_key(city, language)

    # Проверяем кэш
    cached = await redis.get(cache_key)
    if cached:
        return cached

    if not OWM_KEY:
        return "❌ Погодный сервис не настроен."

    try:
        lang = LANG_MAP.get(language, "ru")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": city, "appid": OWM_KEY, "units": "metric", "lang": lang},
            )
            if resp.status_code == 404:
                return f"🔍 Город *{city}* не найден."
            resp.raise_for_status()
            data = resp.json()

        weather_main = data["weather"][0]["main"]
        icon = WEATHER_ICONS.get(weather_main, "🌡")
        desc = data["weather"][0]["description"].capitalize()
        temp = round(data["main"]["temp"])
        feels = round(data["main"]["feels_like"])
        humidity = data["main"]["humidity"]
        wind = round(data["wind"]["speed"])
        city_name = data["name"]
        country = data["sys"]["country"]

        text = (
            f"{icon} *{city_name}, {country}*\n\n"
            f"🌡 Температура: *{temp}°C* (ощущается {feels}°C)\n"
            f"💧 Влажность: {humidity}%\n"
            f"💨 Ветер: {wind} м/с\n"
            f"📋 {desc}"
        )

        # Кэшируем
        await redis.setex(cache_key, CACHE_TTL, text)
        return text

    except httpx.HTTPError as e:
        logger.warning(f"[Weather] HTTP error for '{city}': {e}")
        return "❌ Не удалось получить прогноз погоды."
    except Exception as e:
        logger.error(f"[Weather] Unexpected error: {e}")
        return "❌ Ошибка сервиса погоды."
