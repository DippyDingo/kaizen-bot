from __future__ import annotations

from datetime import date


DEFAULT_SLEEP_TARGET_MIN = 480


def _display_name(user) -> str:
    preferred_name = getattr(user, "preferred_name", None)
    if preferred_name:
        return str(preferred_name)
    first_name = getattr(user, "first_name", None)
    if first_name:
        return str(first_name)
    username = getattr(user, "username", None)
    if username:
        return str(username)
    return "User"


def _clamp_percent(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _safe_int(value: object) -> int:
    return int(value or 0)


def _safe_float(value: object) -> float:
    return float(value or 0.0)


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def serialize_dashboard_payload(
    user,
    *,
    selected_date: date,
    tasks: list,
    water_ml: int,
    sleep_minutes: int,
    diary_count: int,
) -> dict[str, object]:
    total_tasks = len(tasks)
    done_tasks = sum(1 for task in tasks if getattr(task, "is_done", False))
    open_tasks = total_tasks - done_tasks
    task_percent = _clamp_percent((done_tasks / total_tasks) * 100 if total_tasks else 0)
    water_percent = _clamp_percent((water_ml / user.daily_water_target_ml) * 100 if user.daily_water_target_ml else 0)
    sleep_percent = _clamp_percent((sleep_minutes / DEFAULT_SLEEP_TARGET_MIN) * 100)

    priority_order = {"high": 0, "medium": 1, "low": 2}
    focus_tasks = sorted(
        [task for task in tasks if not getattr(task, "is_done", False)],
        key=lambda task: (
            priority_order.get(getattr(task, "priority", "low"), 3),
            getattr(task, "id", 0),
        ),
    )

    return {
        "date": selected_date.isoformat(),
        "user": {
            "display_name": _display_name(user),
            "level": int(user.level),
            "exp": int(user.exp),
            "exp_to_next_level": int(user.exp_to_next_level),
            "current_streak": int(user.current_streak),
            "longest_streak": int(user.longest_streak),
        },
        "summary": {
            "tasks": {
                "total": total_tasks,
                "done": done_tasks,
                "open": open_tasks,
            },
            "water": {
                "total_ml": int(water_ml),
                "target_ml": int(user.daily_water_target_ml),
            },
            "sleep": {
                "total_minutes": int(sleep_minutes),
                "target_minutes": DEFAULT_SLEEP_TARGET_MIN,
            },
            "diary": {
                "entries": int(diary_count),
            },
        },
        "progress": {
            "tasks_percent": task_percent,
            "water_percent": water_percent,
            "sleep_percent": sleep_percent,
        },
        "focus_tasks": [
            {
                "id": int(task.id),
                "title": str(task.title),
                "priority": str(task.priority),
                "is_done": bool(task.is_done),
                "task_date": task.task_date.isoformat(),
            }
            for task in focus_tasks[:3]
        ],
    }


def serialize_health_payload(
    user,
    *,
    selected_date: date,
    week_from: date,
    day_water_total: int,
    day_sleep_total: int,
    day_workout_total: int,
    day_wellbeing: dict[str, object],
    day_medication_schedule: list[dict[str, object]],
    day_sleep_details: dict[str, object],
    week_water_details: dict[str, object],
    week_sleep_details: dict[str, object],
    week_workout_details: dict[str, object],
    week_wellbeing_details: dict[str, object],
    week_medication_details: dict[str, object],
) -> dict[str, object]:
    day_water_percent = _clamp_percent((day_water_total / user.daily_water_target_ml) * 100 if user.daily_water_target_ml else 0)
    day_sleep_percent = _clamp_percent((day_sleep_total / DEFAULT_SLEEP_TARGET_MIN) * 100)
    week_water_target = max(1, int(user.daily_water_target_ml) * 7)
    week_sleep_target = DEFAULT_SLEEP_TARGET_MIN * 7
    week_workout_target = max(1, int(user.daily_workout_target_min) * 7)

    return {
        "date": selected_date.isoformat(),
        "week_from": week_from.isoformat(),
        "targets": {
            "daily_water_ml": int(user.daily_water_target_ml),
            "daily_sleep_min": DEFAULT_SLEEP_TARGET_MIN,
            "daily_workout_min": int(user.daily_workout_target_min),
        },
        "day": {
            "water": {
                "total_ml": int(day_water_total),
                "target_ml": int(user.daily_water_target_ml),
                "percent": day_water_percent,
            },
            "sleep": {
                "total_minutes": int(day_sleep_total),
                "target_minutes": DEFAULT_SLEEP_TARGET_MIN,
                "percent": day_sleep_percent,
                "avg_quality": _safe_float(day_sleep_details.get("avg_quality")),
            },
            "workout": {
                "total_minutes": int(day_workout_total),
                "target_minutes": int(user.daily_workout_target_min),
                "percent": _clamp_percent((day_workout_total / user.daily_workout_target_min) * 100 if user.daily_workout_target_min else 0),
            },
            "wellbeing": {
                "has_entry": bool(day_wellbeing.get("has_entry")),
                "energy_level": _safe_int(day_wellbeing.get("energy_level")),
                "stress_level": _safe_int(day_wellbeing.get("stress_level")),
            },
            "medications": {
                "total": len(day_medication_schedule),
                "taken": sum(1 for item in day_medication_schedule if item.get("status") == "taken"),
                "pending": sum(1 for item in day_medication_schedule if item.get("status") == "pending"),
                "skipped": sum(1 for item in day_medication_schedule if item.get("status") == "skipped"),
                "schedule": [
                    {
                        "course_id": int(item["course_id"]),
                        "title": str(item["title"]),
                        "dose": str(item["dose"]),
                        "intake_time": str(item["intake_time"]),
                        "days_left": int(item["days_left"]),
                        "status": str(item["status"]),
                    }
                    for item in day_medication_schedule
                ],
            },
        },
        "week": {
            "water": {
                "total_ml": _safe_int(week_water_details.get("total_ml")),
                "active_days": _safe_int(week_water_details.get("active_days")),
                "best_day_ml": _safe_int(week_water_details.get("best_day_ml")),
                "average_daily_ml": int(round(_safe_int(week_water_details.get("total_ml")) / 7)),
                "target_total_ml": week_water_target,
                "percent": _clamp_percent((_safe_int(week_water_details.get("total_ml")) / week_water_target) * 100),
            },
            "sleep": {
                "total_minutes": _safe_int(week_sleep_details.get("total_minutes")),
                "active_days": _safe_int(week_sleep_details.get("active_days")),
                "best_day_minutes": _safe_int(week_sleep_details.get("best_day_minutes")),
                "average_daily_minutes": int(round(_safe_int(week_sleep_details.get("total_minutes")) / 7)),
                "avg_quality": _safe_float(week_sleep_details.get("avg_quality")),
                "target_total_minutes": week_sleep_target,
                "percent": _clamp_percent((_safe_int(week_sleep_details.get("total_minutes")) / week_sleep_target) * 100),
            },
            "workout": {
                "total_minutes": _safe_int(week_workout_details.get("total_minutes")),
                "sessions_count": _safe_int(week_workout_details.get("sessions_count")),
                "active_days": _safe_int(week_workout_details.get("active_days")),
                "best_day_minutes": _safe_int(week_workout_details.get("best_day_minutes")),
                "average_daily_minutes": int(round(_safe_int(week_workout_details.get("total_minutes")) / 7)),
                "target_total_minutes": week_workout_target,
                "percent": _clamp_percent((_safe_int(week_workout_details.get("total_minutes")) / week_workout_target) * 100),
                "by_type": {
                    "strength": {
                        "sessions": _safe_int(week_workout_details.get("strength_count")),
                        "minutes": _safe_int(week_workout_details.get("strength_minutes")),
                    },
                    "cardio": {
                        "sessions": _safe_int(week_workout_details.get("cardio_count")),
                        "minutes": _safe_int(week_workout_details.get("cardio_minutes")),
                    },
                    "mobility": {
                        "sessions": _safe_int(week_workout_details.get("mobility_count")),
                        "minutes": _safe_int(week_workout_details.get("mobility_minutes")),
                    },
                },
            },
            "wellbeing": {
                "entries_count": _safe_int(week_wellbeing_details.get("entries_count")),
                "active_days": _safe_int(week_wellbeing_details.get("active_days")),
                "avg_energy": _safe_float(week_wellbeing_details.get("avg_energy")),
                "avg_stress": _safe_float(week_wellbeing_details.get("avg_stress")),
                "best_energy_day": _iso(week_wellbeing_details.get("best_energy_day")),
                "highest_stress_day": _iso(week_wellbeing_details.get("highest_stress_day")),
            },
            "medications": {
                "total_logs": _safe_int(week_medication_details.get("total_logs")),
                "active_days": _safe_int(week_medication_details.get("active_days")),
                "unique_titles": _safe_int(week_medication_details.get("unique_titles")),
                "best_day_logs": _safe_int(week_medication_details.get("best_day_logs")),
                "top_title": str(week_medication_details.get("top_title") or ""),
                "taken_count": _safe_int(week_medication_details.get("taken_count")),
                "pending_count": _safe_int(week_medication_details.get("pending_count")),
                "skipped_count": _safe_int(week_medication_details.get("skipped_count")),
            },
        },
    }


def serialize_stats_payload(
    user,
    *,
    selected_date: date,
    period: str,
    stats: dict[str, object],
) -> dict[str, object]:
    period_days = _safe_int(stats.get("period_days"))
    tasks_total = _safe_int(stats.get("tasks_total"))
    tasks_done = _safe_int(stats.get("tasks_done"))
    water_total_ml = _safe_int(stats.get("water_total_ml"))
    sleep_total_minutes = _safe_int(stats.get("sleep_total_minutes"))
    diary_total = _safe_int(stats.get("diary_total"))
    avg_sleep_quality = _safe_float(stats.get("avg_sleep_quality"))

    task_details = dict(stats.get("task_details") or {})
    water_details = dict(stats.get("water_details") or {})
    sleep_details = dict(stats.get("sleep_details") or {})
    workout_details = dict(stats.get("workout_details") or {})
    wellbeing_details = dict(stats.get("wellbeing_details") or {})
    medication_details = dict(stats.get("medication_details") or {})
    diary_details = dict(stats.get("diary_details") or {})

    avg_water_ml = int(round(water_total_ml / period_days)) if period_days else 0
    avg_sleep_minutes = int(round(sleep_total_minutes / period_days)) if period_days else 0
    avg_workout_minutes = int(round(_safe_int(workout_details.get("total_minutes")) / period_days)) if period_days else 0

    return {
        "date": selected_date.isoformat(),
        "period": period,
        "period_days": period_days,
        "user": {
            "display_name": _display_name(user),
            "level": int(user.level),
            "exp": int(user.exp),
            "exp_to_next_level": int(user.exp_to_next_level),
            "current_streak": int(user.current_streak),
            "longest_streak": int(user.longest_streak),
            "created_at": user.created_at.date().isoformat(),
        },
        "tasks": {
            "total": tasks_total,
            "done": tasks_done,
            "percent": _clamp_percent((tasks_done / tasks_total) * 100 if tasks_total else 0),
            "high_count": _safe_int(task_details.get("high_count")),
            "medium_count": _safe_int(task_details.get("medium_count")),
            "low_count": _safe_int(task_details.get("low_count")),
            "active_days": _safe_int(task_details.get("active_days")),
        },
        "water": {
            "total_ml": water_total_ml,
            "average_daily_ml": avg_water_ml,
            "target_daily_ml": int(user.daily_water_target_ml),
            "percent_of_target": _clamp_percent((avg_water_ml / user.daily_water_target_ml) * 100 if user.daily_water_target_ml else 0),
            "active_days": _safe_int(water_details.get("active_days")),
            "best_day_ml": _safe_int(water_details.get("best_day_ml")),
        },
        "sleep": {
            "total_minutes": sleep_total_minutes,
            "average_daily_minutes": avg_sleep_minutes,
            "target_daily_minutes": DEFAULT_SLEEP_TARGET_MIN,
            "percent_of_target": _clamp_percent((avg_sleep_minutes / DEFAULT_SLEEP_TARGET_MIN) * 100 if DEFAULT_SLEEP_TARGET_MIN else 0),
            "avg_quality": avg_sleep_quality,
            "quality_percent": _clamp_percent((avg_sleep_quality / 5) * 100 if avg_sleep_quality else 0),
            "active_days": _safe_int(sleep_details.get("active_days")),
            "best_day_minutes": _safe_int(sleep_details.get("best_day_minutes")),
            "longest_log_minutes": _safe_int(sleep_details.get("longest_log_minutes")),
        },
        "workout": {
            "total_minutes": _safe_int(workout_details.get("total_minutes")),
            "average_daily_minutes": avg_workout_minutes,
            "target_daily_minutes": int(user.daily_workout_target_min),
            "percent_of_target": _clamp_percent((avg_workout_minutes / user.daily_workout_target_min) * 100 if user.daily_workout_target_min else 0),
            "sessions_count": _safe_int(workout_details.get("sessions_count")),
            "active_days": _safe_int(workout_details.get("active_days")),
            "best_day_minutes": _safe_int(workout_details.get("best_day_minutes")),
            "by_type": {
                "strength": {
                    "sessions": _safe_int(workout_details.get("strength_count")),
                    "minutes": _safe_int(workout_details.get("strength_minutes")),
                },
                "cardio": {
                    "sessions": _safe_int(workout_details.get("cardio_count")),
                    "minutes": _safe_int(workout_details.get("cardio_minutes")),
                },
                "mobility": {
                    "sessions": _safe_int(workout_details.get("mobility_count")),
                    "minutes": _safe_int(workout_details.get("mobility_minutes")),
                },
            },
        },
        "medications": {
            "total_logs": _safe_int(medication_details.get("total_logs")),
            "taken_count": _safe_int(medication_details.get("taken_count")),
            "pending_count": _safe_int(medication_details.get("pending_count")),
            "skipped_count": _safe_int(medication_details.get("skipped_count")),
            "unique_titles": _safe_int(medication_details.get("unique_titles")),
            "active_days": _safe_int(medication_details.get("active_days")),
            "best_day_logs": _safe_int(medication_details.get("best_day_logs")),
            "top_title": str(medication_details.get("top_title") or ""),
        },
        "wellbeing": {
            "entries_count": _safe_int(wellbeing_details.get("entries_count")),
            "active_days": _safe_int(wellbeing_details.get("active_days")),
            "avg_energy": _safe_float(wellbeing_details.get("avg_energy")),
            "avg_stress": _safe_float(wellbeing_details.get("avg_stress")),
            "best_energy_day": _iso(wellbeing_details.get("best_energy_day")),
            "highest_stress_day": _iso(wellbeing_details.get("highest_stress_day")),
        },
        "diary": {
            "total_entries": diary_total,
            "active_days": _safe_int(diary_details.get("active_days")),
            "best_day_entries": _safe_int(diary_details.get("best_day_entries")),
            "active_percent": _clamp_percent((_safe_int(diary_details.get("active_days")) / period_days) * 100 if period_days else 0),
        },
    }
