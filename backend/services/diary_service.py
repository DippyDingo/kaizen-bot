from datetime import date, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import DiaryEntry, User
from backend.services.rpg_service import EXP_TABLE, add_exp

async def add_diary_entry(
    session: AsyncSession,
    user: User,
    entry_type: str,
    text: str | None = None,
    file_id: str | None = None,
    file_unique_id: str | None = None,
    mime_type: str | None = None,
    duration_sec: int | None = None,
    width: int | None = None,
    height: int | None = None,
    created_at: datetime | None = None,
) -> int:
    entry = DiaryEntry(
        user_id=user.id,
        entry_type=entry_type,
        text=(text or "").strip() or None,
        file_id=file_id,
        file_unique_id=file_unique_id,
        mime_type=mime_type,
        duration_sec=duration_sec,
        width=width,
        height=height,
        created_at=created_at or datetime.utcnow(),
    )
    session.add(entry)
    level_ups = add_exp(user, EXP_TABLE["diary_logged"])
    await session.commit()
    await session.refresh(user)
    return level_ups


async def get_day_diary_entries_count(session: AsyncSession, user_id: int, target_day: date) -> int:
    start_dt = datetime.combine(target_day, datetime.min.time())
    end_dt = datetime.combine(target_day, datetime.max.time())

    result = await session.execute(
        select(func.count(DiaryEntry.id)).where(
            and_(
                DiaryEntry.user_id == user_id,
                DiaryEntry.created_at >= start_dt,
                DiaryEntry.created_at <= end_dt,
            )
        )
    )
    return int(result.scalar_one())


async def list_day_diary_entries(
    session: AsyncSession,
    user_id: int,
    target_day: date,
    limit: int | None = 20,
) -> list[DiaryEntry]:
    start_dt = datetime.combine(target_day, datetime.min.time())
    end_dt = datetime.combine(target_day, datetime.max.time())

    query = (
        select(DiaryEntry)
        .where(
            and_(
                DiaryEntry.user_id == user_id,
                DiaryEntry.created_at >= start_dt,
                DiaryEntry.created_at <= end_dt,
            )
        )
        .order_by(DiaryEntry.created_at.desc())
    )
    if limit is not None:
        query = query.limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


async def get_user_diary_entry(session: AsyncSession, user_id: int, entry_id: int) -> DiaryEntry | None:
    result = await session.execute(
        select(DiaryEntry).where(
            and_(
                DiaryEntry.id == entry_id,
                DiaryEntry.user_id == user_id,
            )
        )
    )
    return result.scalar_one_or_none()
