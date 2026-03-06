from __future__ import annotations

from datetime import date, timedelta

from backend.database import async_session
from backend.services.diary_service import (
    get_day_diary_entries_count,
    get_diary_details_for_period,
    get_diary_entries_count_for_period,
    get_total_diary_entries_count,
)
from backend.services.health_service import (
    get_day_sleep_total_minutes,
    get_day_workout_total_minutes,
    get_medication_details_for_period,
    get_sleep_details_for_period,
    get_sleep_total_minutes_all_time,
    get_sleep_totals_for_period,
    get_today_water_total,
    get_water_details_for_period,
    get_water_total_all_time,
    get_water_total_for_period,
    get_wellbeing_details_for_period,
    get_wellbeing_for_day,
    get_workout_details_for_period,
    list_medication_schedule_for_day,
)
from backend.services.task_service import (
    get_task_details_for_period,
    get_task_totals,
    get_task_totals_for_period,
    list_tasks_for_date,
)
from backend.services.user_service import get_user_by_telegram_id

from .serializers import (
    serialize_dashboard_payload,
    serialize_health_payload,
    serialize_stats_payload,
)


def _stats_period_bounds(selected_date: date, period: str) -> tuple[date | None, date | None]:
    if period == "day":
        return selected_date, selected_date
    if period == "7d":
        return selected_date - timedelta(days=6), selected_date
    if period == "30d":
        return selected_date - timedelta(days=29), selected_date
    return None, None


async def build_dashboard_payload(telegram_id: int, target_date: date) -> dict[str, object] | None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            return None

        tasks = await list_tasks_for_date(session, user.id, target_date)
        water_ml = await get_today_water_total(session, user.id, target_date)
        sleep_minutes = await get_day_sleep_total_minutes(session, user.id, target_date)
        diary_count = await get_day_diary_entries_count(session, user.id, target_date)

    return serialize_dashboard_payload(
        user,
        selected_date=target_date,
        tasks=tasks,
        water_ml=water_ml,
        sleep_minutes=sleep_minutes,
        diary_count=diary_count,
    )


async def build_health_payload(telegram_id: int, selected_date: date) -> dict[str, object] | None:
    week_from = selected_date - timedelta(days=6)

    async with async_session() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            return None

        day_water_total = await get_today_water_total(session, user.id, selected_date)
        day_sleep_total = await get_day_sleep_total_minutes(session, user.id, selected_date)
        day_workout_total = await get_day_workout_total_minutes(session, user.id, selected_date)
        day_wellbeing = await get_wellbeing_for_day(session, user.id, selected_date)
        day_medication_schedule = await list_medication_schedule_for_day(session, user.id, selected_date)
        day_sleep_details = await get_sleep_details_for_period(session, user.id, selected_date, selected_date)
        week_water_details = await get_water_details_for_period(session, user.id, week_from, selected_date)
        week_sleep_details = await get_sleep_details_for_period(session, user.id, week_from, selected_date)
        week_workout_details = await get_workout_details_for_period(session, user.id, week_from, selected_date)
        week_wellbeing_details = await get_wellbeing_details_for_period(session, user.id, week_from, selected_date)
        week_medication_details = await get_medication_details_for_period(session, user.id, week_from, selected_date)

    return serialize_health_payload(
        user,
        selected_date=selected_date,
        week_from=week_from,
        day_water_total=day_water_total,
        day_sleep_total=day_sleep_total,
        day_workout_total=day_workout_total,
        day_wellbeing=day_wellbeing,
        day_medication_schedule=day_medication_schedule,
        day_sleep_details=day_sleep_details,
        week_water_details=week_water_details,
        week_sleep_details=week_sleep_details,
        week_workout_details=week_workout_details,
        week_wellbeing_details=week_wellbeing_details,
        week_medication_details=week_medication_details,
    )


async def build_stats_payload(telegram_id: int, selected_date: date, period: str) -> dict[str, object] | None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            return None

        if period == "all":
            tasks_total, tasks_done = await get_task_totals(session, user.id)
            water_total_ml = await get_water_total_all_time(session, user.id)
            sleep_total_minutes = await get_sleep_total_minutes_all_time(session, user.id)
            diary_total = await get_total_diary_entries_count(session, user.id)
            period_days = max((selected_date - user.created_at.date()).days + 1, 1)
            avg_sleep_quality = 0.0
            detail_from = user.created_at.date()
            detail_to = selected_date
        else:
            date_from, date_to = _stats_period_bounds(selected_date, period)
            assert date_from is not None and date_to is not None
            tasks_total, tasks_done = await get_task_totals_for_period(session, user.id, date_from, date_to)
            water_total_ml = await get_water_total_for_period(session, user.id, date_from, date_to)
            sleep_total_minutes, avg_sleep_quality = await get_sleep_totals_for_period(session, user.id, date_from, date_to)
            diary_total = await get_diary_entries_count_for_period(session, user.id, date_from, date_to)
            period_days = max((date_to - date_from).days + 1, 1)
            detail_from = date_from
            detail_to = date_to

        stats = {
            "period_days": period_days,
            "tasks_total": tasks_total,
            "tasks_done": tasks_done,
            "water_total_ml": water_total_ml,
            "sleep_total_minutes": sleep_total_minutes,
            "avg_sleep_quality": avg_sleep_quality,
            "diary_total": diary_total,
            "task_details": await get_task_details_for_period(session, user.id, detail_from, detail_to),
            "water_details": await get_water_details_for_period(session, user.id, detail_from, detail_to),
            "sleep_details": await get_sleep_details_for_period(session, user.id, detail_from, detail_to),
            "workout_details": await get_workout_details_for_period(session, user.id, detail_from, detail_to),
            "wellbeing_details": await get_wellbeing_details_for_period(session, user.id, detail_from, detail_to),
            "medication_details": await get_medication_details_for_period(session, user.id, detail_from, detail_to),
            "diary_details": await get_diary_details_for_period(session, user.id, detail_from, detail_to),
        }

    return serialize_stats_payload(
        user,
        selected_date=selected_date,
        period=period,
        stats=stats,
    )
