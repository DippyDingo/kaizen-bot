from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(50), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    preferred_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow", nullable=False)
    daily_water_target_ml: Mapped[int] = mapped_column(Integer, default=2500, nullable=False)
    daily_workout_target_min: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    dashboard_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    dashboard_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    exp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exp_to_next_level: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    crystals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_active_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<User {self.preferred_name or self.first_name} (tg_id={self.telegram_id}, level={self.level})>"
