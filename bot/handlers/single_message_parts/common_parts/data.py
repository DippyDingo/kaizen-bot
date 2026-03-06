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
from backend.services.task_service import get_task_details_for_period, get_task_totals, get_task_totals_for_period, list_tasks_for_date
from backend.services.user_service import get_or_create_user


def _stats_period_bounds(selected_date: date, period: str) -> tuple[date | None, date | None]:
    if period == "day":
        return selected_date, selected_date
    if period == "7d":
        return selected_date - timedelta(days=6), selected_date
    if period == "30d":
        return selected_date - timedelta(days=29), selected_date
    return None, None


async def _load_health_summary(user_id: int, selected_date: date) -> dict[str, int | float | date]:
    week_from = selected_date - timedelta(days=6)
    async with async_session() as session:
        day_water_total = await get_today_water_total(session, user_id, selected_date)
        day_sleep_total = await get_day_sleep_total_minutes(session, user_id, selected_date)
        day_workout_total = await get_day_workout_total_minutes(session, user_id, selected_date)
        day_wellbeing = await get_wellbeing_for_day(session, user_id, selected_date)
        day_medication_schedule = await list_medication_schedule_for_day(session, user_id, selected_date)
        day_sleep_details = await get_sleep_details_for_period(session, user_id, selected_date, selected_date)
        week_water_details = await get_water_details_for_period(session, user_id, week_from, selected_date)
        week_sleep_details = await get_sleep_details_for_period(session, user_id, week_from, selected_date)
        week_workout_details = await get_workout_details_for_period(session, user_id, week_from, selected_date)
        week_wellbeing_details = await get_wellbeing_details_for_period(session, user_id, week_from, selected_date)
        week_medication_details = await get_medication_details_for_period(session, user_id, week_from, selected_date)

    return {
        "week_from": week_from,
        "day_water_total": day_water_total,
        "day_sleep_total": day_sleep_total,
        "day_workout_total": day_workout_total,
        "day_energy_level": int(day_wellbeing["energy_level"]),
        "day_stress_level": int(day_wellbeing["stress_level"]),
        "day_has_wellbeing": bool(day_wellbeing["has_entry"]),
        "day_medication_total": len(day_medication_schedule),
        "day_medication_taken": sum(1 for item in day_medication_schedule if item["status"] == "taken"),
        "day_medication_skipped": sum(1 for item in day_medication_schedule if item["status"] == "skipped"),
        "day_medication_unique": len({str(item["title"]) for item in day_medication_schedule}),
        "day_recent_medications": [f"{item['intake_time']} {item['title']} ({item['dose']})" for item in day_medication_schedule[:3]],
        "day_avg_quality": float(day_sleep_details["avg_quality"]),
        "week_water_total": int(week_water_details["total_ml"]),
        "week_water_active_days": int(week_water_details["active_days"]),
        "week_best_water_day": int(week_water_details["best_day_ml"]),
        "week_water_avg": int(round(int(week_water_details["total_ml"]) / 7)),
        "week_sleep_total": int(week_sleep_details["total_minutes"]),
        "week_sleep_active_days": int(week_sleep_details["active_days"]),
        "week_best_sleep_day": int(week_sleep_details["best_day_minutes"]),
        "week_sleep_avg": int(round(int(week_sleep_details["total_minutes"]) / 7)),
        "week_avg_quality": float(week_sleep_details["avg_quality"]),
        "week_workout_total": int(week_workout_details["total_minutes"]),
        "week_workout_sessions": int(week_workout_details["sessions_count"]),
        "week_workout_active_days": int(week_workout_details["active_days"]),
        "week_best_workout_day": int(week_workout_details["best_day_minutes"]),
        "week_workout_avg": int(round(int(week_workout_details["total_minutes"]) / 7)),
        "week_strength_count": int(week_workout_details["strength_count"]),
        "week_cardio_count": int(week_workout_details["cardio_count"]),
        "week_mobility_count": int(week_workout_details["mobility_count"]),
        "week_strength_minutes": int(week_workout_details["strength_minutes"]),
        "week_cardio_minutes": int(week_workout_details["cardio_minutes"]),
        "week_mobility_minutes": int(week_workout_details["mobility_minutes"]),
        "week_wellbeing_entries": int(week_wellbeing_details["entries_count"]),
        "week_wellbeing_active_days": int(week_wellbeing_details["active_days"]),
        "week_avg_energy": float(week_wellbeing_details["avg_energy"]),
        "week_avg_stress": float(week_wellbeing_details["avg_stress"]),
        "week_best_energy_day": week_wellbeing_details["best_energy_day"],
        "week_highest_stress_day": week_wellbeing_details["highest_stress_day"],
        "week_medication_total": int(week_medication_details["total_logs"]),
        "week_medication_active_days": int(week_medication_details["active_days"]),
        "week_medication_unique": int(week_medication_details["unique_titles"]),
        "week_best_medication_day": int(week_medication_details["best_day_logs"]),
        "week_top_medication_title": str(week_medication_details["top_title"]),
    }


def _build_companion_hint(stamina_percent: int, water_ml: int, done_count: int, total_tasks: int) -> str:
    if stamina_percent < 60:
        return "Твоя стамина проседает. По истории, если ты ложишься после 2:00, завтра завалишь дейлики. Пора отдыхать."
    if water_ml < 1200:
        return "По воде ты отстаешь от темпа дня. Добавь 250-500 мл сейчас."
    if total_tasks > 0 and done_count < total_tasks:
        return "Добей оставшиеся дейлики сегодня, чтобы не ронять streak."
    return "Темп хороший. Закрепи результат и не теряй ритм."


async def _load_user_and_metrics(from_user, target_date: date) -> tuple[object, list, int, int, int]:
    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=from_user.id,
            first_name=from_user.first_name,
            username=from_user.username,
            last_name=from_user.last_name,
        )
        tasks = await list_tasks_for_date(session, user.id, target_date)
        water_ml = await get_today_water_total(session, user.id, target_date)
        sleep_minutes = await get_day_sleep_total_minutes(session, user.id, target_date)
        diary_count = await get_day_diary_entries_count(session, user.id, target_date)
    return user, tasks, water_ml, sleep_minutes, diary_count


async def _load_user_period_stats(from_user, selected_date: date, period: str) -> tuple[object, dict[str, int | float | str]]:
    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=from_user.id,
            first_name=from_user.first_name,
            username=from_user.username,
            last_name=from_user.last_name,
        )

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

        task_details = await get_task_details_for_period(session, user.id, detail_from, detail_to)
        water_details = await get_water_details_for_period(session, user.id, detail_from, detail_to)
        sleep_details = await get_sleep_details_for_period(session, user.id, detail_from, detail_to)
        workout_details = await get_workout_details_for_period(session, user.id, detail_from, detail_to)
        wellbeing_details = await get_wellbeing_details_for_period(session, user.id, detail_from, detail_to)
        medication_details = await get_medication_details_for_period(session, user.id, detail_from, detail_to)
        diary_details = await get_diary_details_for_period(session, user.id, detail_from, detail_to)

    return user, {
        "period": period,
        "period_days": period_days,
        "tasks_total": tasks_total,
        "tasks_done": tasks_done,
        "water_total_ml": water_total_ml,
        "sleep_total_minutes": sleep_total_minutes,
        "avg_sleep_quality": avg_sleep_quality,
        "diary_total": diary_total,
        "task_details": task_details,
        "water_details": water_details,
        "sleep_details": sleep_details,
        "workout_details": workout_details,
        "wellbeing_details": wellbeing_details,
        "medication_details": medication_details,
        "diary_details": diary_details,
    }
