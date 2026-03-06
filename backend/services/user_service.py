from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import User


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    first_name: str,
    username: str | None,
    last_name: str | None,
    timezone: str = "Europe/Moscow",
) -> tuple[User, bool]:
    user = await get_user_by_telegram_id(session, telegram_id)
    if user:
        return user, False

    user = User(
        telegram_id=telegram_id,
        first_name=first_name,
        username=username,
        last_name=last_name,
        timezone=timezone,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user, True
