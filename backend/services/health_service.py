from datetime import date, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import SleepLog, User, WaterLog, WorkoutLog
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


async def get_sleep_total_minutes_all_time(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.coalesce(func.sum(SleepLog.duration_min), 0)).where(SleepLog.user_id == user_id)
    )
    return int(result.scalar_one())


async def get_sleep_totals_for_period(
    session: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
) -> tuple[int, float]:
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    result = await session.execute(
        select(
            func.coalesce(func.sum(SleepLog.duration_min), 0),
            func.coalesce(func.avg(SleepLog.quality), 0),
        ).where(
            and_(
                SleepLog.user_id == user_id,
                SleepLog.woke_up_at >= start_dt,
                SleepLog.woke_up_at <= end_dt,
            )
        )
    )
    total_minutes, avg_quality = result.one()
    return int(total_minutes or 0), float(avg_quality or 0)


async def get_sleep_details_for_period(
    session: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
) -> dict[str, int | float]:
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    totals_result = await session.execute(
        select(
            func.coalesce(func.sum(SleepLog.duration_min), 0),
            func.coalesce(func.avg(SleepLog.quality), 0),
            func.count(func.distinct(func.date(SleepLog.woke_up_at))),
            func.coalesce(func.max(SleepLog.duration_min), 0),
        ).where(
            and_(
                SleepLog.user_id == user_id,
                SleepLog.woke_up_at >= start_dt,
                SleepLog.woke_up_at <= end_dt,
            )
        )
    )
    total_minutes, avg_quality, active_days, longest_log_minutes = totals_result.one()

    best_day_result = await session.execute(
        select(func.coalesce(func.sum(SleepLog.duration_min), 0).label("day_total"))
        .where(
            and_(
                SleepLog.user_id == user_id,
                SleepLog.woke_up_at >= start_dt,
                SleepLog.woke_up_at <= end_dt,
            )
        )
        .group_by(func.date(SleepLog.woke_up_at))
        .order_by(func.sum(SleepLog.duration_min).desc())
        .limit(1)
    )
    best_day_minutes = best_day_result.scalar_one_or_none()

    return {
        "total_minutes": int(total_minutes or 0),
        "avg_quality": float(avg_quality or 0),
        "active_days": int(active_days or 0),
        "longest_log_minutes": int(longest_log_minutes or 0),
        "best_day_minutes": int(best_day_minutes or 0),
    }


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


async def remove_last_sleep_log(
    session: AsyncSession,
    user: User,
    target_day: date,
) -> tuple[int | None, int, int | None]:
    start_dt = datetime.combine(target_day, datetime.min.time())
    end_dt = datetime.combine(target_day, datetime.max.time())

    result = await session.execute(
        select(SleepLog)
        .where(
            and_(
                SleepLog.user_id == user.id,
                SleepLog.woke_up_at >= start_dt,
                SleepLog.woke_up_at <= end_dt,
            )
        )
        .order_by(SleepLog.woke_up_at.desc(), SleepLog.id.desc())
        .limit(1)
    )
    sleep_log = result.scalar_one_or_none()
    if not sleep_log:
        return None, 0, None

    duration_min = sleep_log.duration_min
    quality = sleep_log.quality
    await session.delete(sleep_log)
    level_change = -remove_exp(user, EXP_TABLE["sleep_logged"])
    await session.commit()
    await session.refresh(user)
    return duration_min, level_change, quality


async def add_workout_log(
    session: AsyncSession,
    user: User,
    workout_type: str,
    duration_min: int,
    logged_at: datetime | None = None,
) -> tuple[WorkoutLog, int]:
    workout_log = WorkoutLog(
        user_id=user.id,
        workout_type=workout_type,
        duration_min=duration_min,
        logged_at=logged_at or datetime.utcnow(),
    )
    session.add(workout_log)
    level_ups = add_exp(user, EXP_TABLE["workout_logged"])
    await session.commit()
    await session.refresh(workout_log)
    await session.refresh(user)
    return workout_log, level_ups


async def remove_last_workout_log(
    session: AsyncSession,
    user: User,
    target_day: date,
) -> tuple[int | None, int, str | None]:
    start_dt = datetime.combine(target_day, datetime.min.time())
    end_dt = datetime.combine(target_day, datetime.max.time())

    result = await session.execute(
        select(WorkoutLog)
        .where(
            and_(
                WorkoutLog.user_id == user.id,
                WorkoutLog.logged_at >= start_dt,
                WorkoutLog.logged_at <= end_dt,
            )
        )
        .order_by(WorkoutLog.logged_at.desc(), WorkoutLog.id.desc())
        .limit(1)
    )
    workout_log = result.scalar_one_or_none()
    if not workout_log:
        return None, 0, None

    duration_min = workout_log.duration_min
    workout_type = workout_log.workout_type
    await session.delete(workout_log)
    level_change = -remove_exp(user, EXP_TABLE["workout_logged"])
    await session.commit()
    await session.refresh(user)
    return duration_min, level_change, workout_type


async def get_day_workout_total_minutes(session: AsyncSession, user_id: int, target_day: date) -> int:
    start_dt = datetime.combine(target_day, datetime.min.time())
    end_dt = datetime.combine(target_day, datetime.max.time())

    result = await session.execute(
        select(func.coalesce(func.sum(WorkoutLog.duration_min), 0)).where(
            and_(
                WorkoutLog.user_id == user_id,
                WorkoutLog.logged_at >= start_dt,
                WorkoutLog.logged_at <= end_dt,
            )
        )
    )
    return int(result.scalar_one())


async def get_workout_details_for_period(
    session: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
) -> dict[str, int]:
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    totals_result = await session.execute(
        select(
            func.coalesce(func.sum(WorkoutLog.duration_min), 0),
            func.count(WorkoutLog.id),
            func.count(func.distinct(func.date(WorkoutLog.logged_at))),
        ).where(
            and_(
                WorkoutLog.user_id == user_id,
                WorkoutLog.logged_at >= start_dt,
                WorkoutLog.logged_at <= end_dt,
            )
        )
    )
    total_minutes, sessions_count, active_days = totals_result.one()

    best_day_result = await session.execute(
        select(func.coalesce(func.sum(WorkoutLog.duration_min), 0).label("day_total"))
        .where(
            and_(
                WorkoutLog.user_id == user_id,
                WorkoutLog.logged_at >= start_dt,
                WorkoutLog.logged_at <= end_dt,
            )
        )
        .group_by(func.date(WorkoutLog.logged_at))
        .order_by(func.sum(WorkoutLog.duration_min).desc())
        .limit(1)
    )
    best_day_minutes = best_day_result.scalar_one_or_none()

    type_rows = await session.execute(
        select(
            WorkoutLog.workout_type,
            func.count(WorkoutLog.id),
            func.coalesce(func.sum(WorkoutLog.duration_min), 0),
        ).where(
            and_(
                WorkoutLog.user_id == user_id,
                WorkoutLog.logged_at >= start_dt,
                WorkoutLog.logged_at <= end_dt,
            )
        ).group_by(WorkoutLog.workout_type)
    )

    type_counts = {"strength": 0, "cardio": 0, "mobility": 0}
    type_minutes = {"strength": 0, "cardio": 0, "mobility": 0}
    for workout_type, count_value, total_value in type_rows:
        if workout_type in type_counts:
            type_counts[workout_type] = int(count_value or 0)
            type_minutes[workout_type] = int(total_value or 0)

    return {
        "total_minutes": int(total_minutes or 0),
        "sessions_count": int(sessions_count or 0),
        "active_days": int(active_days or 0),
        "best_day_minutes": int(best_day_minutes or 0),
        "strength_count": type_counts["strength"],
        "cardio_count": type_counts["cardio"],
        "mobility_count": type_counts["mobility"],
        "strength_minutes": type_minutes["strength"],
        "cardio_minutes": type_minutes["cardio"],
        "mobility_minutes": type_minutes["mobility"],
    }
