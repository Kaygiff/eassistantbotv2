"""casino/games/truth_dare.py — Правда или действие."""

from __future__ import annotations
import random

TRUTHS_RU = [
    "Какой твой самый большой страх?",
    "Что самое смешное, что ты когда-либо делал?",
    "Какой твой любимый фильм?",
    "Что бы ты сделал с миллионом долларов?",
]

DARES_RU = [
    "Напиши смешной стикер и отправь в чат!",
    "Назови трёх знаменитостей, на которых ты похож.",
    "Напиши стихотворение из 4 строк прямо сейчас.",
    "Опиши свой день в трёх эмодзи.",
]


async def get_truth_dare(language: str) -> str:
    import random
    choice = random.choice(["truth", "dare"])
    if choice == "truth":
        q = random.choice(TRUTHS_RU)
        return f"🤔 *Правда*\n\n{q}"
    else:
        d = random.choice(DARES_RU)
        return f"😈 *Действие*\n\n{d}"
