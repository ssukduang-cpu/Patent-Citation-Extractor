from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import Request
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
COOKIE_NAME = "session_user"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_user(session: Session, email: str, password: str) -> User:
    user = User(email=email.lower().strip(), password_hash=hash_password(password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate_user(session: Session, email: str, password: str) -> User | None:
    user = session.scalar(select(User).where(User.email == email.lower().strip()))
    if not user or not verify_password(password, user.password_hash):
        return None
    user.last_active_at = datetime.now(timezone.utc)
    session.commit()
    return user


def set_session_cookie(response, user_id: int) -> None:
    secret = os.getenv("SESSION_SECRET_KEY", "dev-secret-change-me")
    response.set_cookie(COOKIE_NAME, f"{user_id}:{secret[:8]}", httponly=True, samesite="lax")


def clear_session_cookie(response) -> None:
    response.delete_cookie(COOKIE_NAME)


def get_current_user(request: Request, session: Session) -> User | None:
    val = request.cookies.get(COOKIE_NAME)
    if not val or ":" not in val:
        return None
    uid, _ = val.split(":", 1)
    if not uid.isdigit():
        return None
    user = session.get(User, int(uid))
    if user:
        user.last_active_at = datetime.now(timezone.utc)
        session.commit()
    return user
