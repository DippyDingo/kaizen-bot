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


async def get_total_diary_entries_count(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.count(DiaryEntry.id)).where(DiaryEntry.user_id == user_id)
    )
    return int(result.scalar_one())


async def get_diary_entries_count_for_period(
    session: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
) -> int:
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

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


async def get_diary_calendar_marks(
    session: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
) -> dict[date, str]:
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    result = await session.execute(
        select(func.date(DiaryEntry.created_at))
        .where(
            and_(
                DiaryEntry.user_id == user_id,
                DiaryEntry.created_at >= start_dt,
                DiaryEntry.created_at <= end_dt,
            )
        )
        .group_by(func.date(DiaryEntry.created_at))
    )

    marks: dict[date, str] = {}
    for (entry_date,) in result.all():
        parsed_date = entry_date
        if isinstance(entry_date, str):
            parsed_date = date.fromisoformat(entry_date)
        if isinstance(parsed_date, date):
            marks[parsed_date] = "has_entries"
    return marks


async def get_diary_details_for_period(
    session: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
) -> dict[str, int]:
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    total_result = await session.execute(
        select(
            func.count(DiaryEntry.id),
            func.count(func.distinct(func.date(DiaryEntry.created_at))),
        ).where(
            and_(
                DiaryEntry.user_id == user_id,
                DiaryEntry.created_at >= start_dt,
                DiaryEntry.created_at <= end_dt,
            )
        )
    )
    total_entries, active_days = total_result.one()

    best_day_result = await session.execute(
        select(func.count(DiaryEntry.id).label("entries_count"))
        .where(
            and_(
                DiaryEntry.user_id == user_id,
                DiaryEntry.created_at >= start_dt,
                DiaryEntry.created_at <= end_dt,
            )
        )
        .group_by(func.date(DiaryEntry.created_at))
        .order_by(func.count(DiaryEntry.id).desc())
        .limit(1)
    )
    best_day_entries = best_day_result.scalar_one_or_none()

    return {
        "total_entries": int(total_entries or 0),
        "active_days": int(active_days or 0),
        "best_day_entries": int(best_day_entries or 0),
    }


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
