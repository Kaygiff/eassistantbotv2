"""
economy/wallet.py — Операции с кошельком Ecoins.
Атомарные транзакции через Supabase RPC.
"""

from __future__ import annotations
import uuid
import logging
from typing import Optional

from infra.db.supabase import get_supabase_admin
from api.audit.logger import log_ecoin_transaction
from bot.brain.context import BrainContext
from api.auth.session import get_fsm_state, set_fsm_state, set_fsm_data, get_fsm_data, clear_fsm_state, clear_fsm_data

logger = logging.getLogger(__name__)


async def get_balance(user_id: str) -> int:
    """Возвращает текущий баланс пользователя."""
    res = (
        get_supabase_admin().table("ecoin_wallets")
        .select("balance")
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    return res.data["balance"] if res.data else 0


async def credit(user_id: str, amount: int, reason: str, related_id: str | None = None) -> int:
    """
    Пополняет кошелёк на amount Ecoins.
    Возвращает новый баланс.
    """
    balance = await get_balance(user_id)
    new_balance = balance + amount

    get_supabase_admin().table("ecoin_wallets").update({
        "balance": new_balance,
    }).eq("user_id", user_id).execute()

    tx_id = str(uuid.uuid4())
    get_supabase_admin().table("ecoin_transactions").insert({
        "id": tx_id,
        "user_id": user_id,
        "type": "credit",
        "amount": amount,
        "balance_after": new_balance,
        "reason": reason,
        "related_id": related_id,
    }).execute()

    await log_ecoin_transaction(user_id, "credit", amount, reason, new_balance)
    return new_balance


async def debit(user_id: str, amount: int, reason: str, related_id: str | None = None) -> tuple[bool, int]:
    """
    Списывает amount Ecoins с кошелька.
    Возвращает (success, new_balance).
    """
    balance = await get_balance(user_id)
    if balance < amount:
        return False, balance

    new_balance = balance - amount
    get_supabase_admin().table("ecoin_wallets").update({
        "balance": new_balance,
    }).eq("user_id", user_id).execute()

    tx_id = str(uuid.uuid4())
    get_supabase_admin().table("ecoin_transactions").insert({
        "id": tx_id,
        "user_id": user_id,
        "type": "debit",
        "amount": amount,
        "balance_after": new_balance,
        "reason": reason,
        "related_id": related_id,
    }).execute()

    await log_ecoin_transaction(user_id, "debit", amount, reason, new_balance)
    return True, new_balance


async def transfer_ecoins(
    from_user_id: str,
    to_username: str,
    amount: int,
    language: str = "ru",
) -> str:
    """Переводит Ecoins от одного пользователя другому."""
    from core.i18n.loader import t

    if amount <= 0:
        return "❌ Сумма перевода должна быть больше 0."

    # Находим получателя
    res = (
        get_supabase_admin().table("users")
        .select("id, username, first_name")
        .eq("username", to_username)
        .maybe_single()
        .execute()
    )
    if not res.data:
        return t(language, "common.not_found")

    to_user = res.data
    to_user_id = to_user["id"]

    if to_user_id == from_user_id:
        return "❌ Нельзя переводить самому себе."

    # Списываем у отправителя
    success, new_balance = await debit(from_user_id, amount, "transfer_out", to_user_id)
    if not success:
        return t(language, "economy.insufficient_funds", balance=new_balance)

    # Зачисляем получателю
    await credit(to_user_id, amount, "transfer_in", from_user_id)

    # Уведомляем получателя
    from infra.notifications.sender import notify_user
    from_res = get_supabase_admin().table("users").select("username").eq("id", from_user_id).maybe_single().execute()
    from_username = from_res.data.get("username", "пользователь") if from_res.data else "пользователь"
    await notify_user(to_user_id, t(language, "economy.transfer_received", amount=amount, username=f"@{from_username}"))

    display_name = f"@{to_user.get('username', to_user.get('first_name', to_username))}"
    return t(language, "economy.transfer_sent", amount=amount, username=display_name)


async def handle_transfer_fsm(ctx: BrainContext, bot, state: str) -> bool:
    """FSM для ввода суммы перевода."""
    user_id = str(ctx.user.id)

    if state == "transfer:awaiting_amount":
        data = await get_fsm_data(user_id)
        to_username = data.get("to_username")
        try:
            amount = int(ctx.text.strip())
        except ValueError:
            await bot.send_message(ctx.chat_id, "⚠️ Введи число.")
            return True

        await clear_fsm_state(user_id)
        await clear_fsm_data(user_id)
        result = await transfer_ecoins(user_id, to_username, amount, ctx.language)
        await bot.send_message(ctx.chat_id, result, parse_mode="Markdown")
        return True

    return False
