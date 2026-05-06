"""casino/games/slots.py — Игровые автоматы.

Улучшенная версия:
- Взвешенные символы для контроля RTP (~92%)
- Wild-символ (⭐) заменяет любой символ
- Scatter (🎁) — 3 штуки дают фриспины независимо от позиций
- Стрик-система: после 5 проигрышей подряд — небольшой буст
- Анимация через редактирование сообщения
- Красивая ASCII-рамка с подсветкой выигрыша
- Кнопки «Крутить снова» и «Таблица выплат»
"""

from __future__ import annotations

import asyncio
import random
import uuid
from typing import Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infra.db.supabase import get_supabase_admin
from world.economy.wallet import credit, debit, get_balance
from core.i18n import t

# ---------------------------------------------------------------------------
# Конфигурация символов
# ---------------------------------------------------------------------------

# (символ, вес для рандома)
# Чем ниже вес — тем реже выпадает символ
SYMBOL_WEIGHTS: list[tuple[str, int]] = [
    ("🍒", 30),   # Вишня      — очень часто
    ("🍋", 25),   # Лимон      — часто
    ("🍊", 20),   # Апельсин   — часто
    ("🍇", 15),   # Виноград   — средне
    ("💎", 6),    # Алмаз      — редко
    ("7️⃣", 3),    # Семёрка    — очень редко
    ("⭐", 5),    # Wild       — редко (заменяет любой)
    ("🎁", 4),    # Scatter    — редко (фриспины)
]

SYMBOLS = [s for s, _ in SYMBOL_WEIGHTS]
WEIGHTS = [w for _, w in SYMBOL_WEIGHTS]

WILD = "⭐"
SCATTER = "🎁"

# ---------------------------------------------------------------------------
# Таблица выплат (множитель от ставки при 3 одинаковых)
# ---------------------------------------------------------------------------

PAYOUTS_3: dict[str, int] = {
    "7️⃣": 50,   # Джекпот
    "💎": 20,
    "🍇": 8,
    "🍊": 5,
    "🍋": 4,
    "🍒": 3,
    "⭐": 15,   # 3 wild подряд — особый бонус
}

PAYOUTS_2: dict[str, float] = {
    "7️⃣": 3.0,
    "💎": 2.0,
    "🍇": 1.0,
    "🍊": 0.5,
    "🍋": 0.5,
    "🍒": 0.3,
}

SCATTER_FREESPINS = 3        # Сколько фриспинов дают 3 scatter
HOUSE_FEE_PERCENT = 3        # Снижен с 5% до 3% для лучшего RTP
STREAK_BOOST_AFTER = 5       # После скольких проигрышей активируется буст
STREAK_BOOST_EXTRA_WEIGHT = 20  # Сколько добавить к весу выигрышных символов

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _spin_reel(boost: bool = False) -> str:
    """Крутим один барабан. При бусте повышаем веса ценных символов."""
    if boost:
        boosted = [
            w + (STREAK_BOOST_EXTRA_WEIGHT if s in ("7️⃣", "💎", "🍇") else 0)
            for s, w in SYMBOL_WEIGHTS
        ]
        return random.choices(SYMBOLS, weights=boosted, k=1)[0]
    return random.choices(SYMBOLS, weights=WEIGHTS, k=1)[0]


def _resolve_wilds(reels: list[str]) -> list[str]:
    """Заменяем Wild на наиболее частый не-wild символ в барабанах."""
    non_wild = [s for s in reels if s not in (WILD, SCATTER)]
    if not non_wild:
        return reels
    base = max(set(non_wild), key=non_wild.count)
    return [base if s == WILD else s for s in reels]


def _calculate_result(reels: list[str]) -> tuple[float, str, int]:
    """
    Возвращает (multiplier, win_type, scatter_count).
    win_type: 'jackpot' | 'triple' | 'double' | 'scatter' | 'loss'
    """
    scatter_count = reels.count(SCATTER)

    # Scatter-выигрыш (не зависит от позиций)
    if scatter_count >= 3:
        return 0.0, "scatter", scatter_count

    # Убираем scatter перед проверкой линий
    effective = [s if s != SCATTER else WILD for s in reels]
    resolved = _resolve_wilds(effective)

    # Тройное совпадение
    if resolved[0] == resolved[1] == resolved[2]:
        sym = resolved[0]
        mult = PAYOUTS_3.get(sym, 2)
        win_type = "jackpot" if sym == "7️⃣" else "triple"
        return float(mult), win_type, scatter_count

    # Двойное совпадение (первые два или последние два)
    for i in range(2):
        if resolved[i] == resolved[i + 1] and resolved[i] not in (SCATTER,):
            sym = resolved[i]
            mult = PAYOUTS_2.get(sym, 0.3)
            return mult, "double", scatter_count

    return 0.0, "loss", scatter_count


def _get_streak(user_id: str) -> int:
    """Получаем текущий стрик проигрышей из БД."""
    try:
        result = (
            get_supabase_admin()
            .table("casino_rounds")
            .select("outcome")
            .eq("user_id", user_id)
            .eq("game_type", "slots")
            .order("created_at", desc=True)
            .limit(STREAK_BOOST_AFTER)
            .execute()
        )
        rounds = result.data or []
        streak = 0
        for r in rounds:
            if r["outcome"] == "loss":
                streak += 1
            else:
                break
        return streak
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Визуализация
# ---------------------------------------------------------------------------

SPIN_FRAMES = [
    ["❓", "❓", "❓"],
    ["🔄", "❓", "❓"],
    ["🔄", "🔄", "❓"],
]

def _render_slots(
    reels: list[str],
    win_type: str,
    multiplier: float,
    payout: int,
    bet: int,
    balance: int,
    freespins: int = 0,
    is_freespin: bool = False,
) -> tuple[str, InlineKeyboardMarkup]:
    """Рендерим финальное сообщение со слотами."""

    # Рамка
    top    = "╔═══════════════╗"
    mid    = "║               ║"
    bottom = "╚═══════════════╝"

    reel_str = "  ".join(reels)
    reel_line = f"║   {reel_str}   ║"

    # Заголовок
    spin_label = "🆓 ФРИСПИН" if is_freespin else "🎰 СЛОТЫ"

    # Результат
    if win_type == "jackpot":
        result_line = f"🎆 ДЖЕКПОТ! × {int(multiplier)} → +{payout} Ecoins"
    elif win_type == "triple":
        result_line = f"✨ Тройка! × {int(multiplier)} → +{payout} Ecoins"
    elif win_type == "double":
        result_line = f"👍 Пара! × {multiplier} → +{payout} Ecoins"
    elif win_type == "scatter":
        result_line = f"🎁 SCATTER! +{freespins} фриспинов!"
    else:
        result_line = f"😔 Не повезло. -{bet} Ecoins"

    text = (
        f"*{spin_label}*\n\n"
        f"`{top}`\n"
        f"`{mid}`\n"
        f"`{reel_line}`\n"
        f"`{mid}`\n"
        f"`{bottom}`\n\n"
        f"{result_line}\n\n"
        f"💰 Баланс: *{balance} Ecoins*"
    )

    if freespins > 0 and win_type != "scatter":
        text += f"\n🆓 Фриспинов: *{freespins}*"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"🔄 Крутить снова ({bet} Ecoins)",
                callback_data=f"slots:spin:{bet}",
            ),
        ],
        [
            InlineKeyboardButton(text="📊 Выплаты", callback_data="slots:paytable"),
            InlineKeyboardButton(text="🎰 Казино", callback_data="profile:casino"),
        ],
    ])

    return text, keyboard


def _render_spinning(frame: list[str]) -> str:
    """Рамка во время анимации."""
    top    = "╔═══════════════╗"
    mid    = "║               ║"
    bottom = "╚═══════════════╝"
    reel_str = "  ".join(frame)
    reel_line = f"║   {reel_str}   ║"
    return (
        f"*🎰 СЛОТЫ*\n\n"
        f"`{top}`\n"
        f"`{mid}`\n"
        f"`{reel_line}`\n"
        f"`{mid}`\n"
        f"`{bottom}`\n\n"
        f"_Крутится..._"
    )


def paytable_text() -> str:
    return (
        "📊 *Таблица выплат*\n\n"
        "```\n"
        "7️⃣ 7️⃣ 7️⃣  →  × 50  ДЖЕКПОТ\n"
        "💎 💎 💎  →  × 20\n"
        "⭐ ⭐ ⭐  →  × 15  (Wild×3)\n"
        "🍇 🍇 🍇  →  × 8\n"
        "🍊 🍊 🍊  →  × 5\n"
        "🍋 🍋 🍋  →  × 4\n"
        "🍒 🍒 🍒  →  × 3\n"
        "─────────────────\n"
        "7️⃣ 7️⃣  ?  →  × 3  (пара)\n"
        "💎 💎  ?  →  × 2  (пара)\n"
        "🍇 🍇  ?  →  × 1  (пара)\n"
        "─────────────────\n"
        "🎁 🎁 🎁  →  фриспины\n"
        "⭐        →  Wild (замена)\n"
        "```\n\n"
        "_RTP ≈ 92%  |  Комиссия казино: 3%_"
    )


# ---------------------------------------------------------------------------
# Основная функция (с анимацией)
# ---------------------------------------------------------------------------

async def play_slots(
    user_id: str,
    bet: int,
    language: str,
    bot: Bot,
    chat_id: int,
    message_id: Optional[int] = None,
    freespins_left: int = 0,
    is_freespin: bool = False,
) -> None:
    """
    Запускает слоты с анимацией.
    Если message_id передан — редактирует существующее сообщение.
    Если is_freespin=True — ставка не списывается.
    """
    # Списываем ставку (если не фриспин)
    if not is_freespin:
        success, balance = await debit(user_id, bet, "casino_bet")
        if not success:
            msg = t(language, "economy.insufficient_funds", balance=balance)
            if message_id:
                await bot.edit_message_text(msg, chat_id=chat_id, message_id=message_id, parse_mode="Markdown")
            else:
                await bot.send_message(chat_id, msg, parse_mode="Markdown")
            return

    # Анимация
    for frame in SPIN_FRAMES:
        frame_text = _render_spinning(frame)
        try:
            if message_id:
                await bot.edit_message_text(
                    frame_text, chat_id=chat_id, message_id=message_id, parse_mode="Markdown"
                )
            else:
                sent = await bot.send_message(chat_id, frame_text, parse_mode="Markdown")
                message_id = sent.message_id
        except Exception:
            pass
        await asyncio.sleep(0.4)

    # Стрик-буст
    streak = _get_streak(user_id)
    boost = streak >= STREAK_BOOST_AFTER

    # Крутим барабаны
    reels = [_spin_reel(boost) for _ in range(3)]
    multiplier, win_type, scatter_count = _calculate_result(reels)

    # Фриспины при scatter
    new_freespins = 0
    if win_type == "scatter":
        new_freespins = SCATTER_FREESPINS
        payout = 0
        outcome = "win"  # scatter — это выигрыш (фриспины)
    else:
        house_fee = int(bet * HOUSE_FEE_PERCENT / 100)
        if multiplier > 0:
            raw_payout = int(bet * multiplier)
            payout = max(0, raw_payout - house_fee)
            outcome = "win"
            await credit(user_id, payout, "game_win")
        else:
            payout = 0
            house_fee = 0
            outcome = "loss"

    # Сохраняем в БД
    try:
        house_fee_val = int(bet * HOUSE_FEE_PERCENT / 100) if multiplier > 0 and win_type != "scatter" else 0
        get_supabase_admin().table("casino_rounds").insert({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "game_type": "slots",
            "amount": bet if not is_freespin else 0,
            "payout": payout,
            "house_fee": house_fee_val,
            "outcome": outcome,
            "result": {
                "reels": reels,
                "multiplier": multiplier,
                "win_type": win_type,
                "scatter_count": scatter_count,
                "streak_boost": boost,
                "is_freespin": is_freespin,
            },
        }).execute()
    except Exception:
        pass

    balance = await get_balance(user_id)

    # Финальный рендер
    total_freespins = freespins_left + new_freespins
    text, keyboard = _render_slots(
        reels=reels,
        win_type=win_type,
        multiplier=multiplier,
        payout=payout,
        bet=bet,
        balance=balance,
        freespins=total_freespins,
        is_freespin=is_freespin,
    )

    try:
        await bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    except Exception:
        await bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=keyboard)

    # Если остались фриспины — запускаем следующий через 1.5 сек
    remaining = total_freespins - (1 if is_freespin else 0)
    if win_type == "scatter" and new_freespins > 0:
        # Первый фриспин запустится по callback от пользователя
        pass
    elif is_freespin and remaining > 0:
        await asyncio.sleep(1.5)
        await play_slots(
            user_id=user_id,
            bet=bet,
            language=language,
            bot=bot,
            chat_id=chat_id,
            message_id=message_id,
            freespins_left=remaining,
            is_freespin=True,
        )
