from __future__ import annotations

import html
import re
from datetime import date, datetime, time, timedelta

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..common import _build_bar_caption, _build_goal_bar, _clamp_percent, _date_nav_row

HEALTH_MODE_SUMMARY_DAY = "summary_day"
HEALTH_MODE_SUMMARY_WEEK = "summary_week"
HEALTH_MODE_MEDICATIONS = "medications"
HEALTH_MODE_MEDICATION_CALENDAR = "medication_calendar"
HEALTH_MODE_SLEEP_DURATION = "sleep_duration"
HEALTH_MODE_SLEEP_QUALITY = "sleep_quality"
HEALTH_MODE_SLEEP_EXACT = "sleep_exact"
HEALTH_MODE_MEDICATION_TITLE = "medication_title"
HEALTH_MODE_MEDICATION_DOSE = "medication_dose"
HEALTH_MODE_MEDICATION_TIME = "medication_time"
HEALTH_MODE_MEDICATION_DAYS = "medication_days"
HEALTH_MODE_WORKOUT_TYPE = "workout_type"
HEALTH_MODE_WORKOUT_DURATION = "workout_duration"

SLEEP_DURATION_OPTIONS = (300, 360, 420, 480, 540, 600)
SLEEP_QUALITY_LABELS = {1: "1", 2: "2", 3: "3", 4: "4", 5: "5"}
WORKOUT_TYPE_LABELS = {
    "strength": "💪 Силовая",
    "cardio": "🏃 Кардио",
    "mobility": "🧘 Мобилити",
}
WORKOUT_TYPE_SHORT = {
    "strength": "силовая",
    "cardio": "кардио",
    "mobility": "мобилити",
}
WORKOUT_DURATION_OPTIONS = (15, 30, 45, 60)

DAILY_WATER_TARGET_ML = 2500
DAILY_SLEEP_TARGET_MIN = 480
DAILY_WORKOUT_TARGET_MIN = 30


def _format_minutes(total_minutes: int) -> str:
    hours = total_minutes // 60
    minutes = total_minutes % 60
    if hours and minutes:
        return f"{hours} ч {minutes} м"
    if hours:
        return f"{hours} ч"
    return f"{minutes} м"


def _sleep_duration_label(minutes: int) -> str:
    hours = minutes // 60
    minutes_part = minutes % 60
    if minutes_part == 0:
        return f"{hours}ч"
    return f"{hours}ч {minutes_part}м"


def _parse_workout_duration_input(raw_text: str) -> int | None:
    text = raw_text.strip().lower()
    if text.isdigit():
        value = int(text)
        return value if value > 0 else None

    match = re.fullmatch(r"(\d{1,2}):([0-5]\d)", text)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        total = hours * 60 + minutes
        return total if total > 0 else None

    return None


def _short_medication(value: str, limit: int = 24) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _parse_medication_time_input(raw_text: str) -> time | None:
    text = raw_text.strip()
    match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", text)
    if not match:
        return None
    return time(hour=int(match.group(1)), minute=int(match.group(2)))


def _parse_medication_days_input(raw_text: str) -> int | None:
    text = raw_text.strip()
    if not text.isdigit():
        return None
    value = int(text)
    return value if value > 0 else None


def _medication_status_icon(status: str) -> str:
    return {
        "taken": "🟢",
        "skipped": "🔴",
        "pending": "🟡",
    }.get(status, "🟡")


def _build_health_keyboard(selected_date: date, *, mode: str = HEALTH_MODE_SUMMARY_DAY, summary: dict | None = None) -> InlineKeyboardMarkup:
    summary = summary or {}
    rows: list[list[InlineKeyboardButton]] = [
        _date_nav_row(selected_date),
        [
            InlineKeyboardButton(
                text="• День" if mode == HEALTH_MODE_SUMMARY_DAY else "День",
                callback_data="health:mode:day",
            ),
            InlineKeyboardButton(
                text="• Неделя" if mode == HEALTH_MODE_SUMMARY_WEEK else "Неделя",
                callback_data="health:mode:week",
            ),
        ],
    ]

    if mode == HEALTH_MODE_SLEEP_DURATION:
        rows.extend(
            [
                [InlineKeyboardButton(text="5ч", callback_data="sleep:dur:300"), InlineKeyboardButton(text="6ч", callback_data="sleep:dur:360"), InlineKeyboardButton(text="7ч", callback_data="sleep:dur:420")],
                [InlineKeyboardButton(text="8ч", callback_data="sleep:dur:480"), InlineKeyboardButton(text="9ч", callback_data="sleep:dur:540"), InlineKeyboardButton(text="10ч", callback_data="sleep:dur:600")],
                [InlineKeyboardButton(text="🕒 Точное время", callback_data="sleep:exact")],
                [InlineKeyboardButton(text="↩️", callback_data="sleep:cancel")],
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=rows)

    if mode == HEALTH_MODE_SLEEP_QUALITY:
        rows.extend(
            [
                [InlineKeyboardButton(text=SLEEP_QUALITY_LABELS[quality], callback_data=f"sleep:quality:{quality}") for quality in (1, 2, 3, 4, 5)],
                [InlineKeyboardButton(text="↩️", callback_data="sleep:back")],
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=rows)

    if mode == HEALTH_MODE_SLEEP_EXACT:
        rows.extend([[InlineKeyboardButton(text="↩️", callback_data="sleep:exact:cancel")]])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    if mode == HEALTH_MODE_MEDICATION_TITLE:
        rows.extend([[InlineKeyboardButton(text="↩️", callback_data="med:cancel")]])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    if mode == HEALTH_MODE_MEDICATION_DOSE:
        rows.extend([[InlineKeyboardButton(text="↩️", callback_data="med:back")]])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    if mode == HEALTH_MODE_MEDICATION_TIME:
        rows.extend(
            [
                [InlineKeyboardButton(text="08:00", callback_data="med:time:08:00"), InlineKeyboardButton(text="13:00", callback_data="med:time:13:00")],
                [InlineKeyboardButton(text="20:00", callback_data="med:time:20:00"), InlineKeyboardButton(text="22:00", callback_data="med:time:22:00")],
                [InlineKeyboardButton(text="⌨️ Своё время", callback_data="med:time:custom")],
                [InlineKeyboardButton(text="↩️", callback_data="med:time:back")],
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=rows)

    if mode == HEALTH_MODE_MEDICATION_DAYS:
        rows.extend(
            [
                [InlineKeyboardButton(text="3 дня", callback_data="med:days:3"), InlineKeyboardButton(text="5 дней", callback_data="med:days:5")],
                [InlineKeyboardButton(text="7 дней", callback_data="med:days:7"), InlineKeyboardButton(text="14 дней", callback_data="med:days:14")],
                [InlineKeyboardButton(text="30 дней", callback_data="med:days:30"), InlineKeyboardButton(text="⌨️ Своё число", callback_data="med:days:custom")],
                [InlineKeyboardButton(text="↩️", callback_data="med:days:back")],
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=rows)

    if mode == HEALTH_MODE_MEDICATIONS:
        rows.extend(
            [
                [InlineKeyboardButton(text="➕ Курс", callback_data="med:plan:start"), InlineKeyboardButton(text="📅 Календарь", callback_data="med:calendar")],
            ]
        )
        medication_schedule = list(summary.get("medication_schedule", []))
        for item in medication_schedule:
            course_id = int(item["course_id"])
            title = _short_medication(f"{item['intake_time']} {item['title']}", limit=26)
            status = str(item["status"])
            rows.append(
                [
                    InlineKeyboardButton(text=title, callback_data=f"med:item:{course_id}"),
                    InlineKeyboardButton(text="🗑", callback_data=f"med:delete:{course_id}"),
                ]
            )
            if status == "taken":
                rows.append(
                    [
                        InlineKeyboardButton(text="↩️", callback_data=f"med:toggle:{course_id}:taken"),
                        InlineKeyboardButton(text="✖️ Пропуск", callback_data=f"med:toggle:{course_id}:skipped"),
                    ]
                )
            elif status == "skipped":
                rows.append(
                    [
                        InlineKeyboardButton(text="✅ Выпил", callback_data=f"med:toggle:{course_id}:taken"),
                        InlineKeyboardButton(text="↩️", callback_data=f"med:toggle:{course_id}:skipped"),
                    ]
                )
            else:
                rows.append(
                    [
                        InlineKeyboardButton(text="✅ Выпил", callback_data=f"med:toggle:{course_id}:taken"),
                        InlineKeyboardButton(text="✖️ Пропуск", callback_data=f"med:toggle:{course_id}:skipped"),
                    ]
                )
        rows.append([InlineKeyboardButton(text="↩️", callback_data="med:close")])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    if mode == HEALTH_MODE_WORKOUT_TYPE:
        rows.extend(
            [
                [InlineKeyboardButton(text=WORKOUT_TYPE_LABELS["strength"], callback_data="workout:type:strength"), InlineKeyboardButton(text=WORKOUT_TYPE_LABELS["cardio"], callback_data="workout:type:cardio")],
                [InlineKeyboardButton(text=WORKOUT_TYPE_LABELS["mobility"], callback_data="workout:type:mobility")],
                [InlineKeyboardButton(text="↩️", callback_data="workout:cancel")],
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=rows)

    if mode == HEALTH_MODE_WORKOUT_DURATION:
        rows.extend(
            [
                [InlineKeyboardButton(text="15м", callback_data="workout:dur:15"), InlineKeyboardButton(text="30м", callback_data="workout:dur:30")],
                [InlineKeyboardButton(text="45м", callback_data="workout:dur:45"), InlineKeyboardButton(text="60м", callback_data="workout:dur:60")],
                [InlineKeyboardButton(text="⌨️ Своё время", callback_data="workout:custom")],
                [InlineKeyboardButton(text="↩️", callback_data="workout:back")],
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=rows)

    rows.extend(
        [
            [InlineKeyboardButton(text="😴 Добавить сон", callback_data="sleep:start"), InlineKeyboardButton(text="↩️", callback_data="sleep:undo")],
            [InlineKeyboardButton(text="🏃 Добавить тренировку", callback_data="workout:start"), InlineKeyboardButton(text="↩️", callback_data="workout:undo")],
            [InlineKeyboardButton(text="💧 Вода", callback_data="health:water"), InlineKeyboardButton(text="💊 Лекарства", callback_data="health:mode:meds")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_health_text(
    water_ml: int,
    sleep_minutes: int,
    selected_date: date,
    notice: str | None,
    *,
    mode: str = HEALTH_MODE_SUMMARY_DAY,
    pending_sleep_minutes: int | None = None,
    summary: dict | None = None,
) -> str:
    summary = summary or {}
    water_target_ml = int(summary.get("daily_water_target_ml", DAILY_WATER_TARGET_ML))
    workout_target_min = int(summary.get("daily_workout_target_min", DAILY_WORKOUT_TARGET_MIN))
    stamina_percent = _clamp_percent((sleep_minutes / DAILY_SLEEP_TARGET_MIN) * 100)

    day_workout_total = int(summary.get("day_workout_total", 0))
    day_medication_total = int(summary.get("day_medication_total", 0))
    day_medication_taken = int(summary.get("day_medication_taken", 0))
    day_medication_skipped = int(summary.get("day_medication_skipped", 0))
    day_medication_unique = int(summary.get("day_medication_unique", 0))
    day_recent_medications = list(summary.get("day_recent_medications", []))
    medication_schedule = list(summary.get("medication_schedule", []))
    day_quality = float(summary.get("day_avg_quality", 0))
    day_water_bar, day_water_percent = _build_goal_bar(water_ml, water_target_ml, "water")
    day_sleep_bar, day_sleep_percent = _build_goal_bar(sleep_minutes, DAILY_SLEEP_TARGET_MIN, "sleep")
    day_workout_bar, day_workout_percent = _build_goal_bar(day_workout_total, workout_target_min, "workout")

    week_from = summary.get("week_from", selected_date)
    week_water_total = int(summary.get("week_water_total", 0))
    week_sleep_total = int(summary.get("week_sleep_total", 0))
    week_workout_total = int(summary.get("week_workout_total", 0))
    week_medication_total = int(summary.get("week_medication_total", 0))
    week_water_bar, week_water_percent = _build_goal_bar(week_water_total, water_target_ml * 7, "water")
    week_sleep_bar, week_sleep_percent = _build_goal_bar(week_sleep_total, DAILY_SLEEP_TARGET_MIN * 7, "sleep")
    week_workout_bar, week_workout_percent = _build_goal_bar(week_workout_total, workout_target_min * 7, "workout")

    if mode == HEALTH_MODE_MEDICATIONS:
        lines = [
            "<b>💊 ЛЕКАРСТВА</b>",
            f"Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>",
            "",
            f"• Запланировано: <b>{day_medication_total}</b>",
            f"• Выпито: <b>{day_medication_taken}</b>",
            f"• Пропусков: <b>{day_medication_skipped}</b>",
            f"• Уникальных: <b>{day_medication_unique}</b>",
            "",
        ]
        if medication_schedule:
            lines.append("<b>На этот день</b>")
            for item in medication_schedule:
                lines.append(
                    "• "
                    f"{_medication_status_icon(str(item['status']))} "
                    f"<b>{html.escape(str(item['intake_time']))}</b> "
                    f"{html.escape(str(item['title']))} - {html.escape(str(item['dose']))}"
                )
                lines.append(
                    f"  Курс: {item['start_date'].strftime('%d.%m')} - {item['end_date'].strftime('%d.%m')} | осталось {item['days_left']} дн."
                )
        else:
            lines.extend(
                [
                    "<b>На этот день</b>",
                    "• Нет активных курсов.",
                    "• Выбери дату стрелками или открой календарь.",
                ]
            )
    elif mode == HEALTH_MODE_SUMMARY_WEEK:
        lines = [
            "<b>❤️ ЗДОРОВЬЕ • НЕДЕЛЯ</b>",
            f"Период: <b>{week_from.strftime('%d.%m')} - {selected_date.strftime('%d.%m.%Y')}</b>",
            "",
            "<b>💧 Вода</b>",
            f"• Сумма: <b>{week_water_total} мл</b>",
            f"• {_build_bar_caption('Вода', week_water_bar, f'{week_water_percent}%')}",
            f"• Среднее: <b>{summary.get('week_water_avg', 0)} мл/д</b>",
            f"• Активных дней: <b>{summary.get('week_water_active_days', 0)}/7</b>",
            f"• Лучший день: <b>{summary.get('week_best_water_day', 0)} мл</b>",
            "",
            "<b>😴 Сон</b>",
            f"• Сумма: <b>{_format_minutes(week_sleep_total)}</b>",
            f"• {_build_bar_caption('Сон', week_sleep_bar, f'{week_sleep_percent}%')}",
            f"• Среднее: <b>{_format_minutes(int(summary.get('week_sleep_avg', 0)))}/д</b>",
            f"• Качество: <b>{float(summary.get('week_avg_quality', 0)):.1f}/5</b>" if summary.get("week_avg_quality", 0) else "• Качество: <b>нет данных</b>",
            f"• Активных дней: <b>{summary.get('week_sleep_active_days', 0)}/7</b>",
            f"• Лучший день: <b>{_format_minutes(int(summary.get('week_best_sleep_day', 0)))}</b>",
            "",
            "<b>🏃 Тренировки</b>",
            f"• Сумма: <b>{_format_minutes(week_workout_total)}</b>",
            f"• {_build_bar_caption('Тренировки', week_workout_bar, f'{week_workout_percent}%')}",
            f"• Среднее: <b>{_format_minutes(int(summary.get('week_workout_avg', 0)))}/д</b>",
            f"• Сессий: <b>{summary.get('week_workout_sessions', 0)}</b>",
            f"• Активных дней: <b>{summary.get('week_workout_active_days', 0)}/7</b>",
            f"• Лучший день: <b>{_format_minutes(int(summary.get('week_best_workout_day', 0)))}</b>",
            f"• По типам: <b>💪 {summary.get('week_strength_count', 0)}</b> | <b>🏃 {summary.get('week_cardio_count', 0)}</b> | <b>🧘 {summary.get('week_mobility_count', 0)}</b>",
            f"• Минуты по типам: <b>💪 {summary.get('week_strength_minutes', 0)}</b> | <b>🏃 {summary.get('week_cardio_minutes', 0)}</b> | <b>🧘 {summary.get('week_mobility_minutes', 0)}</b>",
            "",
            "<b>💊 Лекарства</b>",
            f"• Приёмов: <b>{week_medication_total}</b>",
            f"• Активных дней: <b>{summary.get('week_medication_active_days', 0)}/7</b>",
            f"• Уникальных: <b>{summary.get('week_medication_unique', 0)}</b>",
            f"• Лучший день: <b>{summary.get('week_best_medication_day', 0)}</b> приём(ов)",
            f"• Чаще всего: <b>{html.escape(str(summary.get('week_top_medication_title')))}</b>" if summary.get("week_top_medication_title") else "• Чаще всего: <b>нет данных</b>",
        ]
    else:
        lines = [
            "<b>❤️ ЗДОРОВЬЕ • ДЕНЬ</b>",
            f"Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>",
            "",
            "<b>Сегодня</b>",
            f"• 💧 Вода: <b>{water_ml} мл</b>",
            f"• {_build_bar_caption('Вода', day_water_bar, f'{day_water_percent}%')}",
            f"• 😴 Сон: <b>{_format_minutes(sleep_minutes)}</b>",
            f"• {_build_bar_caption('Сон', day_sleep_bar, f'{day_sleep_percent}%')}",
            f"• ⚡ Стамина: <b>{stamina_percent}%</b>",
            f"• 🏃 Тренировки: <b>{_format_minutes(day_workout_total)}</b>",
            f"• {_build_bar_caption('Тренировки', day_workout_bar, f'{day_workout_percent}%')}",
            f"• 💊 Лекарства: <b>{day_medication_total}</b>",
            f"• Уникальных: <b>{day_medication_unique}</b>",
            f"• ⭐ Качество сна: <b>{day_quality:.1f}/5</b>" if day_quality else "• ⭐ Качество сна: <b>нет данных</b>",
            "",
            "<b>Быстрые действия</b>",
            "• вода ведется в отдельной вкладке `Вода`",
            "• сон и тренировки добавляются кнопками ниже",
            "• лекарства ведутся в отдельном окне",
        ]

    if mode == HEALTH_MODE_SLEEP_DURATION:
        lines.extend(["", "<b>Добавление сна</b>", "Выбери длительность сна.", "Или перейди в точный режим."])
    elif mode == HEALTH_MODE_SLEEP_QUALITY:
        duration_label = _sleep_duration_label(pending_sleep_minutes or 0)
        lines.extend(["", "<b>Качество сна</b>", f"Длительность: <b>{duration_label}</b>", "Оцени качество по шкале 1-5."])
    elif mode == HEALTH_MODE_SLEEP_EXACT:
        lines.extend(["", "<b>Точное время сна</b>", "Отправь время сна в формате:", "<b>23:40 07:15</b>", "или", "<b>23:40-07:15</b>", "Первое время — засыпание, второе — подъём.", "Если время засыпания позже времени подъёма, бот считает, что ты уснул накануне."])
    elif mode == HEALTH_MODE_WORKOUT_TYPE:
        lines.extend(["", "<b>Добавление тренировки</b>", "Выбери тип тренировки."])
    elif mode == HEALTH_MODE_WORKOUT_DURATION:
        workout_type = str(summary.get("pending_workout_type") or "")
        workout_label = WORKOUT_TYPE_LABELS.get(workout_type, "Тренировка")
        lines.extend(["", "<b>Добавление тренировки</b>", f"Тип: <b>{workout_label}</b>", "Выбери длительность или нажми `Своё время`."])
    elif mode == HEALTH_MODE_MEDICATION_TITLE:
        lines.extend(["", "<b>Добавление лекарства</b>", "Напиши название лекарства."])
    elif mode == HEALTH_MODE_MEDICATION_DOSE:
        medication_title = str(summary.get("pending_medication_title") or "Лекарство")
        lines.extend(["", "<b>Добавление лекарства</b>", f"Название: <b>{html.escape(medication_title)}</b>", "Напиши дозу. Пример: <b>1 таблетка</b> или <b>200 мг</b>."])
    elif mode == HEALTH_MODE_MEDICATION_TIME:
        lines.extend(["", "<b>Время приёма</b>", f"Лекарство: <b>{html.escape(str(summary.get('pending_medication_title') or 'Лекарство'))}</b>", "Выбери время кнопкой или отправь своё в формате <b>08:30</b>."])
    elif mode == HEALTH_MODE_MEDICATION_DAYS:
        pending_time = str(summary.get("pending_medication_time") or "--:--")
        lines.extend(["", "<b>Длительность курса</b>", f"Старт: <b>{selected_date.strftime('%d.%m.%Y')}</b>", f"Время: <b>{html.escape(pending_time)}</b>", "Выбери, сколько дней пить лекарство."])

    if day_recent_medications and mode == HEALTH_MODE_SUMMARY_DAY:
        lines.extend(["", "<b>Последние лекарства</b>", *[f"• {html.escape(str(item))}" for item in day_recent_medications]])

    if notice:
        lines.extend(["", f"ℹ️ {notice}"])
    return "\n".join(lines)


def _build_sleep_datetimes(target_day: date, duration_minutes: int) -> tuple[datetime, datetime]:
    woke_up_at = datetime.combine(target_day, time(hour=8, minute=0))
    fell_asleep_at = woke_up_at - timedelta(minutes=duration_minutes)
    return fell_asleep_at, woke_up_at


def _build_exact_sleep_datetimes(target_day: date, fell_time: time, wake_time: time) -> tuple[datetime, datetime]:
    woke_up_at = datetime.combine(target_day, wake_time)
    fell_day = target_day - timedelta(days=1) if fell_time >= wake_time else target_day
    fell_asleep_at = datetime.combine(fell_day, fell_time)
    return fell_asleep_at, woke_up_at


def _parse_exact_sleep_input(raw_text: str, target_day: date) -> tuple[datetime, datetime] | None:
    matches = re.findall(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", raw_text)
    if len(matches) != 2:
        return None

    fell_hour, fell_minute = map(int, matches[0])
    wake_hour, wake_minute = map(int, matches[1])
    fell_time = time(hour=fell_hour, minute=fell_minute)
    wake_time = time(hour=wake_hour, minute=wake_minute)
    fell_asleep_at, woke_up_at = _build_exact_sleep_datetimes(target_day, fell_time, wake_time)
    if woke_up_at <= fell_asleep_at:
        return None
    return fell_asleep_at, woke_up_at

