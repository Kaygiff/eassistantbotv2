"""
brain/handlers/media.py — Музыка, погода, переводчик, энциклопедия, книги, аниме, изображения.
"""

import re
from bot.brain.router import register
from bot.brain.intent import Intent
from bot.brain.context import BrainContext
from core.i18n import t


@register(Intent.MUSIC_SEARCH)
async def handle_music(ctx: BrainContext, bot) -> None:
    # Извлекаем запрос: убираем триггерные слова
    query = re.sub(
        r"(найди музыку|скачай|включи|поставь песню|музыка|трек|скачать песню)\s*",
        "", ctx.text, flags=re.IGNORECASE
    ).strip() or ctx.text

    await bot.send_chat_action(ctx.chat_id, "upload_audio")
    from services.music.downloader import search_and_send
    await search_and_send(ctx.chat_id, query, ctx.language, bot)


@register(Intent.WEATHER)
async def handle_weather(ctx: BrainContext, bot) -> None:
    city = re.sub(
        r"(погода|прогноз погоды|какая погода|температура|/weather)\s*",
        "", ctx.text, flags=re.IGNORECASE
    ).strip() or "Москва"

    from services.weather.forecast import get_weather
    text = await get_weather(city, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.TRANSLATE)
async def handle_translate(ctx: BrainContext, bot) -> None:
    from services.translator.translate import translate_text
    result = await translate_text(ctx.text, ctx.language)
    await bot.send_message(ctx.chat_id, result)


@register(Intent.ENCYCLOPEDIA)
async def handle_encyclopedia(ctx: BrainContext, bot) -> None:
    query = re.sub(
        r"(что такое|расскажи о|кто такой|кто такая|энциклопедия|wikipedia)\s*",
        "", ctx.text, flags=re.IGNORECASE
    ).strip() or ctx.text

    from services.encyclopedia.wiki import get_article
    text = await get_article(query, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.BOOK_SEARCH)
async def handle_book_search(ctx: BrainContext, bot) -> None:
    query = re.sub(
        r"(найди книгу|рекомендуй книгу|книги|/book)\s*",
        "", ctx.text, flags=re.IGNORECASE
    ).strip() or ctx.text

    from services.library.books import search_books
    text = await search_books(query, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.ANIME_SEARCH)
async def handle_anime_search(ctx: BrainContext, bot) -> None:
    query = re.sub(
        r"(найди аниме|аниме|anime|/anime)\s*",
        "", ctx.text, flags=re.IGNORECASE
    ).strip() or ctx.text

    from services.library.anime import search_anime
    text = await search_anime(query, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.IMAGE_GEN)
async def handle_image_gen(ctx: BrainContext, bot) -> None:
    prompt = re.sub(
        r"(нарисуй|создай картинку|сгенерируй|генерировать изображение)\s*",
        "", ctx.text, flags=re.IGNORECASE
    ).strip() or ctx.text

    await bot.send_chat_action(ctx.chat_id, "upload_photo")
    from services.image.generator import generate_image
    image_url = await generate_image(prompt)
    if image_url:
        await bot.send_photo(ctx.chat_id, image_url)
    else:
        await bot.send_message(ctx.chat_id, t(ctx.language, "common.error"))


@register(Intent.VOICE_TO_TEXT)
async def handle_voice(ctx: BrainContext, bot) -> None:
    # Голосовые обрабатываются в router.py до классификации
    # Этот хэндлер — fallback если голосовое пришло как команда
    await bot.send_message(ctx.chat_id, "🎤 Отправь голосовое сообщение, и я переведу его в текст.")
