"""
api/routes/brain_editor.py — Brain Editor API для EAdmin.
CRUD для кастомных правил классификатора.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from api.auth import require_admin
from brain.editor import get_all_rules, update_rule, delete_rule, get_editor_stats, load_rules_into_classifier

router = APIRouter(prefix="/brain", tags=["brain"])


@router.get("/stats")
async def brain_stats(_=Depends(require_admin)):
    return await get_editor_stats()


@router.get("/rules")
async def list_rules(_=Depends(require_admin)):
    return await get_all_rules()


class RuleUpdate(BaseModel):
    keywords: list[str]


@router.put("/rules/{intent}")
async def update_brain_rule(intent: str, body: RuleUpdate, _=Depends(require_admin)):
    rule = await update_rule(intent, body.keywords)
    await load_rules_into_classifier()
    return rule


@router.delete("/rules/{intent}")
async def delete_brain_rule(intent: str, _=Depends(require_admin)):
    await delete_rule(intent)
    return {"ok": True}


@router.post("/rules/reload")
async def reload_rules(_=Depends(require_admin)):
    count = await load_rules_into_classifier()
    return {"ok": True, "loaded": count}
