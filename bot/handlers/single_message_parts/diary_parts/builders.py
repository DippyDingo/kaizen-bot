from __future__ import annotations

from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..common import _build_diary_entry_preview, _date_nav_row


def _build_diary_keyboard(selected_date: date, entries: list) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        _date_nav_row(selected_date, center_callback_data="diary:calendar"),
        [InlineKeyboardButton(text="➕ Запись", callback_data="diary:add")],
        [
            InlineKeyboardButton(text="📤 Всё", callback_data="diary:dumpday"),
            InlineKeyboardButton(text="🧹 Чат", callback_data="diary:clearout"),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_diary_text(
    entries: list,
    selected_date: date,
    mode: str,
    notice: str | None,
    total_count: int | None = None,
) -> str:
    resolved_count = total_count if total_count is not None else len(entries)
    lines = [
        "<b>📝 Дневник</b>",
        f"Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>",
        f"Записей за день: <b>{resolved_count}</b>",
    ]

    if mode == "wait_text":
        lines.extend(["", "Отправь текст, кружок, голосовое, фото или видео."])
    else:
        lines.extend(["", "<b>Обзор дня</b>"])

    if entries:
        lines.extend(["", "<b>Последние записи</b>"])
        for entry in entries[:10]:
            preview = _build_diary_entry_preview(entry)
            lines.append(f"• <b>{entry.created_at.strftime('%H:%M')}</b> — {preview}")
    else:
        lines.extend(["", "Записей за эту дату пока нет."])

    if notice:
        lines.extend(["", f"ℹ️ {notice}"])

    return "\n".join(lines)
