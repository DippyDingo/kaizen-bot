from datetime import date, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import User, WaterLog
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


async def get_water_total_all_time(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.coalesce(func.sum(WaterLog.amount_ml), 0)).where(WaterLog.user_id == user_id)
    )
    return int(result.scalar_one())


async def get_water_total_for_period(
    session: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
) -> int:
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

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


async def get_water_details_for_period(
    session: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
) -> dict[str, int]:
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    totals_result = await session.execute(
        select(
            func.coalesce(func.sum(WaterLog.amount_ml), 0),
            func.count(func.distinct(func.date(WaterLog.logged_at))),
        ).where(
            and_(
                WaterLog.user_id == user_id,
                WaterLog.logged_at >= start_dt,
                WaterLog.logged_at <= end_dt,
            )
        )
    )
    total_ml, active_days = totals_result.one()

    best_day_result = await session.execute(
        select(func.coalesce(func.sum(WaterLog.amount_ml), 0).label("day_total"))
        .where(
            and_(
                WaterLog.user_id == user_id,
                WaterLog.logged_at >= start_dt,
                WaterLog.logged_at <= end_dt,
            )
        )
        .group_by(func.date(WaterLog.logged_at))
        .order_by(func.sum(WaterLog.amount_ml).desc())
        .limit(1)
    )
    best_day_ml = best_day_result.scalar_one_or_none()

    return {
        "total_ml": int(total_ml or 0),
        "active_days": int(active_days or 0),
        "best_day_ml": int(best_day_ml or 0),
    }
