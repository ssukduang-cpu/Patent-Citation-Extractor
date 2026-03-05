from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

DB_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    projects: Mapped[list[Project]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    latest_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    user: Mapped[User] = relationship(back_populates="projects")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def cleanup_inactive(days: int = 30) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    with SessionLocal() as s:
        users = s.scalars(select(User).where(User.last_active_at < cutoff)).all()
        for user in users:
            root = Path("data") / str(user.id)
            if root.exists():
                for child in sorted(root.rglob("*"), reverse=True):
                    if child.is_file():
                        child.unlink(missing_ok=True)
                    else:
                        child.rmdir()
                root.rmdir()
            s.delete(user)
        s.commit()


def get_session():
    with SessionLocal() as s:
        yield s
