"""casino/games/riddle.py — Загадки."""

import random

RIDDLES_RU = [
    ("Что можно увидеть с закрытыми глазами?", "Сон"),
    ("У меня есть города, но нет домов. Есть горы, но нет деревьев. Есть вода, но нет рыбы. Что я?", "Карта"),
    ("Чем больше из неё берёшь, тем больше она становится. Что это?", "Яма"),
    ("Всегда перед тобой, но не увидеть. Что это?", "Будущее"),
    ("Что становится мокрым, пока сушит?", "Полотенце"),
]


async def get_riddle(language: str) -> str:
    question, answer = random.choice(RIDDLES_RU)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    # Ответ скрыт в спойлере (Markdown v2)
    return f"🧩 *Загадка*\n\n{question}\n\n||Ответ: {answer}||"
