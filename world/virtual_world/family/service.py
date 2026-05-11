"""
virtual_world/family/service.py — Семейные отношения между пользователями.

Логика:
- Любой игрок может усыновить/удочерить другого (реальный игрок, даёт согласие)
- Максимум 5 детей на родителя
- Игрок может быть одновременно чьим-то ребёнком и иметь своих детей
- Братья/сёстры вычисляются через общих родителей
- Таблица: family_relations (initiator_id=parent, target_id=child, status)
"""

from __future__ import annotations
import uuid
import logging

from infra.db.supabase import get_supabase_admin
from infra.notifications.sender import send_message_async

logger = logging.getLogger(__name__)

MAX_CHILDREN = 5


def _sb():
    return get_supabase_admin()


async def _get_user_by_telegram_id(telegram_id: int) -> dict | None:
    try:
        res = _sb().table("users").select("id, first_name, username").eq("telegram_id", telegram_id).execute()
        return res.data[0] if res and res.data else None
    except Exception as e:
        logger.warning(f"[Family] _get_user_by_telegram_id error: {e}")
        return None


async def _get_telegram_id(user_uuid: str) -> int | None:
    try:
        res = _sb().table("users").select("telegram_id").eq("id", user_uuid).execute()
        return res.data[0]["telegram_id"] if res and res.data else None
    except Exception as e:
        logger.warning(f"[Family] _get_telegram_id error: {e}")
        return None


async def _get_user_display(user_uuid: str) -> str:
    try:
        res = _sb().table("users").select("first_name, username").eq("id", user_uuid).execute()
        if res and res.data:
            u = res.data[0]
            name = u.get("first_name") or u.get("username") or "?"
            username = u.get("username")
            return f"{name} (@{username})" if username else name
    except Exception as e:
        logger.warning(f"[Family] _get_user_display error: {e}")
    return "?"


async def _count_children(parent_uuid: str) -> int:
    try:
        res = (
            _sb().table("family_relations")
            .select("id")
            .eq("initiator_id", parent_uuid)
            .eq("initiator_role", "parent")
            .eq("status", "active")
            .execute()
        )
        return len(res.data) if res and res.data else 0
    except Exception:
        return 0


async def _get_active_relation(user_a: str, user_b: str) -> dict | None:
    try:
        res = (
            _sb().table("family_relations")
            .select("*")
            .or_(
                f"and(initiator_id.eq.{user_a},target_id.eq.{user_b}),"
                f"and(initiator_id.eq.{user_b},target_id.eq.{user_a})"
            )
            .eq("status", "active")
            .execute()
        )
        return res.data[0] if res and res.data else None
    except Exception as e:
        logger.warning(f"[Family] _get_active_relation error: {e}")
        return None


async def _get_pending_to_target(target_id: str) -> list[dict]:
    try:
        res = (
            _sb().table("family_relations")
            .select("*")
            .eq("target_id", target_id)
            .eq("status", "pending")
            .execute()
        )
        return res.data if res and res.data else []
    except Exception as e:
        logger.warning(f"[Family] _get_pending_to_target error: {e}")
        return []


# ---------------------------------------------------------------------------
# Усыновить/удочерить (reply на сообщение игрока)
# ---------------------------------------------------------------------------

async def adopt(initiator_tg_id: int, target_tg_id: int) -> str:
    if initiator_tg_id == target_tg_id:
        return "🤔 Нельзя усыновить самого себя."

    initiator = await _get_user_by_telegram_id(initiator_tg_id)
    target = await _get_user_by_telegram_id(target_tg_id)

    if not initiator:
        return "❌ Твой профиль не найден."
    if not target:
        return "❌ Пользователь не найден в системе."

    initiator_id = initiator["id"]
    target_id = target["id"]

    if await _get_active_relation(initiator_id, target_id):
        return "👨‍👩‍👧 Вы уже состоите в семейных отношениях."

    # Проверяем уже отправленный pending
    try:
        res = (
            _sb().table("family_relations")
            .select("id")
            .eq("initiator_id", initiator_id)
            .eq("target_id", target_id)
            .eq("status", "pending")
            .execute()
        )
        if res and res.data:
            return "⏳ Запрос уже отправлен, ожидай ответа."
    except Exception:
        pass

    if await _count_children(initiator_id) >= MAX_CHILDREN:
        return f"👨‍👩‍👧 У тебя уже максимум детей ({MAX_CHILDREN})."

    try:
        _sb().table("family_relations").insert({
            "id": str(uuid.uuid4()),
            "initiator_id": initiator_id,
            "target_id": target_id,
            "initiator_role": "parent",
            "target_role": "child",
            "status": "pending",
        }).execute()
    except Exception as e:
        logger.error(f"[Family] adopt insert error: {e}")
        return "❌ Ошибка при отправке запроса. Попробуй ещё раз."

    initiator_name = initiator.get("first_name") or f"@{initiator.get('username', '?')}"
    target_name = target.get("first_name") or f"@{target.get('username', '?')}"

    await send_message_async(
        target_tg_id,
        f"👨‍👩‍👧 *{initiator_name}* хочет тебя усыновить/удочерить!\n\n"
        f"Напиши *принять усыновление* чтобы согласиться, "
        f"или *отказаться от усыновления* чтобы отклонить.",
    )

    return f"✅ Запрос отправлен *{target_name}*. Ожидай ответа."


# ---------------------------------------------------------------------------
# Принять усыновление
# ---------------------------------------------------------------------------

async def accept_adoption(target_tg_id: int) -> str:
    target = await _get_user_by_telegram_id(target_tg_id)
    if not target:
        return "❌ Профиль не найден."

    target_id = target["id"]
    pending_list = await _get_pending_to_target(target_id)

    if not pending_list:
        return "📭 Нет входящих запросов на усыновление."

    pending = pending_list[0]  # берём первый если несколько

    if await _count_children(pending["initiator_id"]) >= MAX_CHILDREN:
        return f"❌ У этого пользователя уже максимум детей ({MAX_CHILDREN})."

    try:
        _sb().table("family_relations").update({"status": "active"}).eq("id", pending["id"]).execute()
    except Exception as e:
        logger.error(f"[Family] accept_adoption update error: {e}")
        return "❌ Ошибка при подтверждении. Попробуй ещё раз."

    initiator_tg = await _get_telegram_id(pending["initiator_id"])
    target_name = target.get("first_name") or f"@{target.get('username', '?')}"
    if initiator_tg:
        await send_message_async(
            initiator_tg,
            f"🎉 *{target_name}* принял(а) твоё предложение! Теперь вы семья 👨‍👩‍👧"
        )

    return "🎉 Ты принял(а) предложение! Теперь вы семья 👨‍👩‍👧"


# ---------------------------------------------------------------------------
# Отказаться от усыновления (входящий запрос)
# ---------------------------------------------------------------------------

async def decline_adoption(target_tg_id: int) -> str:
    target = await _get_user_by_telegram_id(target_tg_id)
    if not target:
        return "❌ Профиль не найден."

    pending_list = await _get_pending_to_target(target["id"])
    if not pending_list:
        return "📭 Нет входящих запросов."

    pending = pending_list[0]

    try:
        _sb().table("family_relations").delete().eq("id", pending["id"]).execute()
    except Exception as e:
        logger.error(f"[Family] decline_adoption delete error: {e}")
        return "❌ Ошибка. Попробуй ещё раз."

    initiator_tg = await _get_telegram_id(pending["initiator_id"])
    target_name = target.get("first_name") or f"@{target.get('username', '?')}"
    if initiator_tg:
        await send_message_async(initiator_tg, f"💔 *{target_name}* отказал(а) в усыновлении.")

    return "✅ Запрос отклонён."


# ---------------------------------------------------------------------------
# Отказаться от ребёнка (reply на ребёнка)
# ---------------------------------------------------------------------------

async def remove_child(parent_tg_id: int, child_tg_id: int) -> str:
    parent = await _get_user_by_telegram_id(parent_tg_id)
    child = await _get_user_by_telegram_id(child_tg_id)

    if not parent or not child:
        return "❌ Пользователь не найден."

    try:
        res = (
            _sb().table("family_relations")
            .select("id")
            .eq("initiator_id", parent["id"])
            .eq("target_id", child["id"])
            .eq("initiator_role", "parent")
            .eq("status", "active")
            .execute()
        )
        relation = res.data[0] if res and res.data else None
    except Exception as e:
        logger.error(f"[Family] remove_child error: {e}")
        return "❌ Ошибка. Попробуй ещё раз."

    if not relation:
        return "🔍 Этот пользователь не является твоим ребёнком."

    try:
        _sb().table("family_relations").delete().eq("id", relation["id"]).execute()
    except Exception as e:
        logger.error(f"[Family] remove_child delete error: {e}")
        return "❌ Ошибка. Попробуй ещё раз."

    child_name = child.get("first_name") or f"@{child.get('username', '?')}"
    await send_message_async(child_tg_id, "💔 Один из твоих родителей отказался от тебя.")

    return f"💔 Ты отказался(ась) от *{child_name}*."


# ---------------------------------------------------------------------------
# Отказаться от родителя (сам игрок)
# ---------------------------------------------------------------------------

async def leave_family(child_tg_id: int) -> str:
    child = await _get_user_by_telegram_id(child_tg_id)
    if not child:
        return "❌ Профиль не найден."

    child_id = child["id"]

    try:
        res = (
            _sb().table("family_relations")
            .select("*")
            .eq("target_id", child_id)
            .eq("target_role", "child")
            .eq("status", "active")
            .execute()
        )
        relations = res.data if res and res.data else []
    except Exception as e:
        logger.error(f"[Family] leave_family error: {e}")
        return "❌ Ошибка. Попробуй ещё раз."

    if not relations:
        return "🔍 У тебя нет родителей в системе."

    try:
        for rel in relations:
            _sb().table("family_relations").delete().eq("id", rel["id"]).execute()
            parent_tg = await _get_telegram_id(rel["initiator_id"])
            if parent_tg:
                child_name = child.get("first_name") or f"@{child.get('username', '?')}"
                await send_message_async(parent_tg, f"💔 *{child_name}* покинул(а) твою семью.")
    except Exception as e:
        logger.error(f"[Family] leave_family delete error: {e}")
        return "❌ Ошибка при выходе из семьи."

    return "✅ Ты вышел(а) из семьи."


# ---------------------------------------------------------------------------
# Моя семья — список
# ---------------------------------------------------------------------------

async def get_family_list(user_tg_id: int) -> str:
    user = await _get_user_by_telegram_id(user_tg_id)
    if not user:
        return "❌ Профиль не найден."

    user_id = user["id"]
    lines = ["👨‍👩‍👧 *Моя семья:*\n"]
    found_any = False

    try:
        # Родители
        res = (
            _sb().table("family_relations")
            .select("initiator_id")
            .eq("target_id", user_id)
            .eq("target_role", "child")
            .eq("status", "active")
            .execute()
        )
        parents = res.data if res and res.data else []
        for p in parents:
            display = await _get_user_display(p["initiator_id"])
            lines.append(f"👤 Родитель: *{display}*")
            found_any = True

        # Дети
        res = (
            _sb().table("family_relations")
            .select("target_id")
            .eq("initiator_id", user_id)
            .eq("initiator_role", "parent")
            .eq("status", "active")
            .execute()
        )
        children = res.data if res and res.data else []
        for c in children:
            display = await _get_user_display(c["target_id"])
            lines.append(f"👶 Ребёнок: *{display}*")
            found_any = True

        # Братья/сёстры (дети тех же родителей)
        sibling_ids: set[str] = set()
        for p in parents:
            res = (
                _sb().table("family_relations")
                .select("target_id")
                .eq("initiator_id", p["initiator_id"])
                .eq("initiator_role", "parent")
                .eq("status", "active")
                .execute()
            )
            if res and res.data:
                for row in res.data:
                    if row["target_id"] != user_id:
                        sibling_ids.add(row["target_id"])

        for sib_id in sibling_ids:
            display = await _get_user_display(sib_id)
            lines.append(f"👥 Брат/сестра: *{display}*")
            found_any = True

    except Exception as e:
        logger.error(f"[Family] get_family_list error: {e}")
        return "❌ Ошибка при получении данных. Попробуй ещё раз."

    if not found_any:
        return "👨‍👩‍👧 У тебя пока нет семьи."

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Для профиля — динамический блок (пустой список = не показывать)
# ---------------------------------------------------------------------------

async def get_family_profile_lines(user_id: str) -> list[str]:
    lines = []
    try:
        # Родители
        res = (
            _sb().table("family_relations")
            .select("initiator_id")
            .eq("target_id", user_id)
            .eq("target_role", "child")
            .eq("status", "active")
            .execute()
        )
        for p in (res.data or []):
            display = await _get_user_display(p["initiator_id"])
            lines.append(f"👤 Родитель: {display}")

        # Дети
        res = (
            _sb().table("family_relations")
            .select("target_id")
            .eq("initiator_id", user_id)
            .eq("initiator_role", "parent")
            .eq("status", "active")
            .execute()
        )
        children_data = res.data or []
        for c in children_data:
            display = await _get_user_display(c["target_id"])
            lines.append(f"👶 Ребёнок: {display}")

        # Братья/сёстры
        sibling_ids: set[str] = set()
        parents_res = (
            _sb().table("family_relations")
            .select("initiator_id")
            .eq("target_id", user_id)
            .eq("target_role", "child")
            .eq("status", "active")
            .execute()
        )
        for p in (parents_res.data or []):
            res = (
                _sb().table("family_relations")
                .select("target_id")
                .eq("initiator_id", p["initiator_id"])
                .eq("initiator_role", "parent")
                .eq("status", "active")
                .execute()
            )
            for row in (res.data or []):
                if row["target_id"] != user_id:
                    sibling_ids.add(row["target_id"])

        for sib_id in sibling_ids:
            display = await _get_user_display(sib_id)
            lines.append(f"👥 Брат/сестра: {display}")

    except Exception as e:
        logger.warning(f"[Family] get_family_profile_lines error: {e}")

    return lines
