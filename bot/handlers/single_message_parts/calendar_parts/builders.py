from __future__ import annotations

import calendar
from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..common import MONTH_NAMES, WEEKDAY_LABELS, _next_month, _prev_month


def _build_calendar_keyboard(
    month_date: date,
    selected_date: date,
    context: str,
    *,
    marks: dict[date, str] | None = None,
) -> InlineKeyboardMarkup:
    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdayscalendar(month_date.year, month_date.month)
    marks = marks or {}

    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=f"{MONTH_NAMES[month_date.month]} {month_date.year}",
                callback_data="cal:noop",
            )
        ],
        [InlineKeyboardButton(text=w, callback_data="cal:noop") for w in WEEKDAY_LABELS],
    ]

    today = date.today()
    for week in weeks:
        row: list[InlineKeyboardButton] = []
        for day_num in week:
            if day_num == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="cal:noop"))
                continue

            day_date = date(month_date.year, month_date.month, day_num)
            text = str(day_num)
            if day_date == selected_date:
                text = f"🔘{day_num}"
            elif context == "tasks" and marks.get(day_date) == "done":
                text = f"✅{day_num}"
            elif context == "tasks" and marks.get(day_date) == "mixed":
                text = f"🟡{day_num}"
            elif context == "tasks" and marks.get(day_date) == "open":
                text = f"🔴{day_num}"
            elif context == "med" and marks.get(day_date) == "done":
                text = f"✅{day_num}"
            elif context == "med" and marks.get(day_date) == "skipped":
                text = f"✖️{day_num}"
            elif context == "med" and marks.get(day_date) == "planned":
                text = f"💊{day_num}"
            elif context == "diary" and marks.get(day_date) == "has_entries":
                text = f"📝{day_num}"
            elif day_date == today:
                text = f"◦{day_num}"

            row.append(
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"cal:pick:{context}:{day_date.isoformat()}",
                )
            )
        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton(
                text="◀️",
                callback_data=f"cal:nav:{context}:{_prev_month(month_date).isoformat()}",
            ),
            InlineKeyboardButton(
                text="▶️",
                callback_data=f"cal:nav:{context}:{_next_month(month_date).isoformat()}",
            ),
        ]
    )

    if context == "create":
        rows.append(
            [
                InlineKeyboardButton(text="📍 Сегодня", callback_data="cal:today:create"),
                InlineKeyboardButton(text="↩️ Назад", callback_data="task:cancel"),
            ]
        )
    elif context == "tasks":
        rows.append([InlineKeyboardButton(text="📍 Сегодня", callback_data="cal:today:tasks")])
        rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="task:calendar:close")])
    elif context == "browse":
        rows.append([InlineKeyboardButton(text="📍 Сегодня", callback_data="cal:today:browse")])
    elif context == "diary":
        rows.append([InlineKeyboardButton(text="📍 Сегодня", callback_data="cal:today:diary")])
        rows.append([InlineKeyboardButton(text="↩️ Дневник", callback_data="diary:close_calendar")])
    elif context == "med":
        rows.append([InlineKeyboardButton(text="📍 Сегодня", callback_data="cal:today:med")])
        rows.append([InlineKeyboardButton(text="💊 Лекарства", callback_data="cal:to_med")])
        rows.append([InlineKeyboardButton(text="↩️ Окно лекарств", callback_data="med:close_calendar")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_calendar_text(selected_date: date, notice: str | None) -> str:
    lines = [
        "<b>📅 КАЛЕНДАРЬ</b>",
        f"Выбранная дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>",
        "Выбери день и открой задачи.",
    ]
    if notice:
        lines.extend(["", f"ℹ️ {notice}"])
    return "\n".join(lines)


def _build_diary_calendar_text(selected_date: date, notice: str | None, day_count: int = 0) -> str:
    if day_count <= 0:
        summary_line = "На этот день записей нет"
    else:
        last_two = day_count % 100
        last_one = day_count % 10
        if 11 <= last_two <= 14:
            word = "записей"
        elif last_one == 1:
            word = "запись"
        elif 2 <= last_one <= 4:
            word = "записи"
        else:
            word = "записей"
        summary_line = f"{day_count} {word} за день"

    lines = [
        "<b>📅 Календарь дневника</b>",
        f"<b>{selected_date.strftime('%d.%m.%Y')}</b>",
        "📝 есть записи",
        summary_line,
    ]
    if notice:
        lines.extend(["", f"ℹ️ {notice}"])
    return "\n".join(lines)


def _build_task_calendar_text(
    selected_date: date,
    day_summary: dict[str, int],
    notice: str | None,
) -> str:
    total = int(day_summary.get("total", 0))
    done = int(day_summary.get("done", 0))
    open_count = max(total - done, 0)

    if total <= 0:
        summary_line = "На этот день задач нет"
    else:
        task_word = "задач" if total != 1 else "задача"
        summary_line = f"{total} {task_word} • {done} выполнено • {open_count} осталось"

    lines = [
        "<b>📅 Календарь задач</b>",
        f"<b>{selected_date.strftime('%d.%m.%Y')}</b>",
        "✅ всё • 🟡 часть • 🔴 открыто",
        summary_line,
    ]
    if notice:
        lines.extend(["", f"ℹ️ {notice}"])
    return "\n".join(lines)
