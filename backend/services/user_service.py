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
        user.first_name = first_name
        user.username = username
        user.last_name = last_name
        user.timezone = timezone
        await session.commit()
        await session.refresh(user)
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


async def set_user_preferred_name(session: AsyncSession, user: User, preferred_name: str | None) -> User:
    user.preferred_name = (preferred_name or "").strip() or None
    await session.commit()
    await session.refresh(user)
    return user


async def set_user_daily_water_target(session: AsyncSession, user: User, daily_water_target_ml: int) -> User:
    user.daily_water_target_ml = max(250, daily_water_target_ml)
    await session.commit()
    await session.refresh(user)
    return user


async def set_user_daily_workout_target(session: AsyncSession, user: User, daily_workout_target_min: int) -> User:
    user.daily_workout_target_min = max(5, daily_workout_target_min)
    await session.commit()
    await session.refresh(user)
    return user


async def set_user_dashboard_message_ref(
    session: AsyncSession,
    user: User,
    *,
    chat_id: int | None,
    message_id: int | None,
) -> User:
    user.dashboard_chat_id = chat_id
    user.dashboard_message_id = message_id
    await session.commit()
    await session.refresh(user)
    return user


async def set_user_chat_keyboard_message_ref(
    session: AsyncSession,
    user: User,
    *,
    chat_id: int | None,
    message_id: int | None,
) -> User:
    user.chat_keyboard_chat_id = chat_id
    user.chat_keyboard_message_id = message_id
    await session.commit()
    await session.refresh(user)
    return user
