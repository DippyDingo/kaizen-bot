from datetime import date, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import SleepLog, User, WaterLog
from backend.services.rpg_service import EXP_TABLE, add_exp, remove_exp


async def add_water_log(
    session: AsyncSession,
    user: User,
    amount_ml: int,
    logged_at: datetime | None = None,
) -> int:
    log = WaterLog(user_id=user.id, amount_ml=amount_ml, logged_at=logged_at or datetime.utcnow())
    session.add(log)
    level_ups = add_exp(user, EXP_TABLE["water_logged"])
    await session.commit()
    await session.refresh(user)
    return level_ups


async def remove_last_water_log(
    session: AsyncSession,
    user: User,
    target_day: date,
) -> tuple[int | None, int]:
    start_dt = datetime.combine(target_day, datetime.min.time())
    end_dt = datetime.combine(target_day, datetime.max.time())

    result = await session.execute(
        select(WaterLog)
        .where(
            and_(
                WaterLog.user_id == user.id,
                WaterLog.logged_at >= start_dt,
                WaterLog.logged_at <= end_dt,
            )
        )
        .order_by(WaterLog.logged_at.desc(), WaterLog.id.desc())
        .limit(1)
    )
    water_log = result.scalar_one_or_none()
    if not water_log:
        return None, 0

    amount_ml = water_log.amount_ml
    await session.delete(water_log)
    level_change = -remove_exp(user, EXP_TABLE["water_logged"])
    await session.commit()
    await session.refresh(user)
    return amount_ml, level_change


async def get_today_water_total(session: AsyncSession, user_id: int, today: date) -> int:
    start_dt = datetime.combine(today, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())

    result = await session.execute(
        select(func.coalesce(func.sum(WaterLog.amount_ml), 0)).where(
            and_(
                WaterLog.user_id == user_id,
                WaterLog.logged_at >= start_dt,
                WaterLog.logged_at <= end_dt,
            )
        )
    )
    return int(result.scalar_one())


async def get_day_sleep_total_minutes(session: AsyncSession, user_id: int, target_day: date) -> int:
    start_dt = datetime.combine(target_day, datetime.min.time())
    end_dt = datetime.combine(target_day, datetime.max.time())

    result = await session.execute(
        select(SleepLog).where(
            and_(
                SleepLog.user_id == user_id,
                SleepLog.woke_up_at >= start_dt,
                SleepLog.fell_asleep_at <= end_dt,
            )
        )
    )

    total_minutes = 0
    for log in result.scalars():
        overlap_start = max(log.fell_asleep_at, start_dt)
        overlap_end = min(log.woke_up_at, end_dt)
        if overlap_end > overlap_start:
            total_minutes += int((overlap_end - overlap_start).total_seconds() // 60)

    return total_minutes


async def add_sleep_log(
    session: AsyncSession,
    user: User,
    fell_asleep_at: datetime,
    woke_up_at: datetime,
    quality: int,
) -> tuple[SleepLog, int]:
    duration = woke_up_at - fell_asleep_at
    duration_min = max(int(duration.total_seconds() // 60), 0)

    sleep_log = SleepLog(
        user_id=user.id,
        fell_asleep_at=fell_asleep_at,
        woke_up_at=woke_up_at,
        duration_min=duration_min,
        quality=quality,
    )
    session.add(sleep_log)
    level_ups = add_exp(user, EXP_TABLE["sleep_logged"])
    await session.commit()
    await session.refresh(sleep_log)
    await session.refresh(user)
    return sleep_log, level_ups
