"""
api/auth.py — JWT авторизация для EAdmin REST API.
Используется как Depends() в роутерах.
"""

from __future__ import annotations
import os
from typing import Annotated

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

SECRET_KEY = os.getenv("EADMIN_SECRET_KEY", "change-me")
ALGORITHM = "HS256"

security = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_admin(payload: dict = Depends(verify_token)) -> dict:
    """Проверяет что токен принадлежит администратору."""
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return payload


def create_admin_token(admin_id: str) -> str:
    """Создаёт JWT токен для администратора (для скриптов)."""
    return jwt.encode({"sub": admin_id, "role": "admin"}, SECRET_KEY, algorithm=ALGORITHM)
