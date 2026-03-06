from __future__ import annotations

import html
from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..common import PRIORITY_TEXT, _date_nav_row

PRIORITY_BADGES: dict[str, str] = {
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
}


def _task_priority_badge(priority: str) -> str:
    return PRIORITY_BADGES.get(priority, "⚪")


def _build_tasks_keyboard(tasks: list, selected_date: date) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        _date_nav_row(selected_date),
    ]

    if not tasks:
        rows.append([InlineKeyboardButton(text="Пусто", callback_data="cal:noop")])
    else:
        for task in tasks[:12]:
            title = f"{_task_priority_badge(task.priority)} {task.title.strip()}"
            rows.append(
                [
                    InlineKeyboardButton(
                        text=title,
                        callback_data=f"task:toggle:{task.id}",
                        style="success" if task.is_done else "danger",
                    ),
                    InlineKeyboardButton(text="❌", callback_data=f"task:drop:{task.id}"),
                ]
            )

    rows.append([InlineKeyboardButton(text="➕ Задача", callback_data="task:add")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_priority_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔴 Важно", callback_data="task:prio:high")],
            [InlineKeyboardButton(text="🟡 Обычн.", callback_data="task:prio:medium")],
            [InlineKeyboardButton(text="🟢 Потом", callback_data="task:prio:low")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="task:cancel")],
        ]
    )


def _build_tasks_text(
    tasks: list,
    selected_date: date,
    mode: str,
    pending_title: str | None,
    pending_priority: str | None,
    notice: str | None,
) -> str:
    done_count = sum(1 for t in tasks if t.is_done)

    lines = [
        "<b>🗂 ЗАДАЧИ</b>",
        f"Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>",
        f"Выполнено: <b>{done_count}/{len(tasks)}</b>",
    ]

    if mode == "wait_title":
        lines.extend(["", "Отправь название задачи."])
    elif mode == "wait_priority":
        lines.extend(["", f"Новая: <b>{pending_title or ''}</b>", "Выбери приоритет."])
    elif mode == "wait_task_date":
        lines.extend(
            [
                "",
                f"Новая: <b>{pending_title or ''}</b>",
                f"Приоритет: <b>{PRIORITY_TEXT.get(pending_priority or '', '')}</b>",
                "Выбери дату.",
            ]
        )
    else:
        lines.extend(["", "Нажми на задачу, чтобы переключить выполнение. Кнопка <b>❌</b> удаляет задачу."])
        if tasks:
            lines.extend(["", "<b>Список задач:</b>"])
            for task in tasks[:12]:
                badge = _task_priority_badge(task.priority)
                title = html.escape(task.title)
                if task.is_done:
                    title = f"<s>{title}</s>"
                lines.append(f"{badge} {title}")

    if notice:
        lines.extend(["", f"ℹ️ {notice}"])

    return "\n".join(lines)
