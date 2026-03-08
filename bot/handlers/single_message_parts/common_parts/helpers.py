from __future__ import annotations

import html
from datetime import date, datetime, timedelta

from aiogram.types import InlineKeyboardButton, Message

from .constants import BAR_EMPTY, BAR_FILLED, BAR_STEPS, MONTH_NAMES_GENITIVE, WEEKDAY_NAMES_LONG


def _short(text: str, limit: int = 22) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _display_name(user) -> str:
    preferred_name = getattr(user, "preferred_name", None)
    if preferred_name:
        return preferred_name
    first_name = getattr(user, "first_name", None)
    if first_name:
        return first_name
    username = getattr(user, "username", None)
    if username:
        return username
    return "Игрок"


def _parse_iso_date(value: str | None, default: date) -> date:
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default


def _month_start(day: date) -> date:
    return day.replace(day=1)


def _next_month(day: date) -> date:
    return (day.replace(day=28) + timedelta(days=4)).replace(day=1)


def _prev_month(day: date) -> date:
    return (day.replace(day=1) - timedelta(days=1)).replace(day=1)


def _format_long_date(day: date) -> str:
    return f"{day.day} {MONTH_NAMES_GENITIVE[day.month]}, {WEEKDAY_NAMES_LONG[day.weekday()]}"


def _clamp_percent(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _build_meter(percent: int, total: int, filled: str, empty: str) -> str:
    filled_count = max(0, min(total, int(round(percent / 100 * total))))
    return (filled * filled_count) + (empty * (total - filled_count))


def _build_metric_bar(metric: str, percent: int, total: int = BAR_STEPS) -> str:
    filled = BAR_FILLED[metric]
    return _build_meter(percent, total, filled, BAR_EMPTY)


def _build_goal_bar(current: int, target: int, metric: str, total: int = BAR_STEPS) -> tuple[str, int]:
    percent = _clamp_percent((current / target) * 100 if target > 0 else 0)
    return _build_metric_bar(metric, percent, total=total), percent


def _build_bar_caption(label: str, bar: str, value: str, *, icon: str | None = None) -> str:
    prefix = f"{icon} " if icon else ""
    return f"{prefix}{label}: {bar} <b>{value}</b>"


def _build_step_bar(filled_steps: int, metric: str, total: int = BAR_STEPS) -> str:
    safe_steps = max(0, min(total, filled_steps))
    filled = BAR_FILLED[metric]
    return (filled * safe_steps) + (BAR_EMPTY * (total - safe_steps))


def _build_mana_bar(water_ml: int, target_ml: int = 2500) -> tuple[str, int]:
    step_ml = max(1, int(round(target_ml / BAR_STEPS)))
    mana_steps = max(0, min(BAR_STEPS, int(round(water_ml / step_ml))))
    return _build_step_bar(mana_steps, "water", total=BAR_STEPS), mana_steps


def _date_nav_row(selected_date: date, *, center_callback_data: str = "cal:noop") -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(text="◀️", callback_data="date:shift:-1"),
        InlineKeyboardButton(text=selected_date.strftime("%d.%m"), callback_data=center_callback_data),
        InlineKeyboardButton(text="▶️", callback_data="date:shift:1"),
    ]


def _diary_type_label(entry_type: str) -> str:
    mapping = {
        "text": "📝 Текст",
        "voice": "🎤 Голосовое",
        "video_note": "⭕ Кружок",
        "photo": "🖼 Фото",
        "video": "🎬 Видео",
    }
    return mapping.get(entry_type, "📎 Медиа")


def _build_diary_entry_preview(entry) -> str:
    base = _diary_type_label(getattr(entry, "entry_type", "text"))
    text = (entry.text or "").replace("\n", " ").strip()
    if text:
        return f"{base}: {html.escape(_short(text, limit=56))}"
    return base


def _extract_diary_payload(message: Message) -> dict | None:
    if message.text:
        return {"entry_type": "text", "text": message.text}

    if message.voice:
        return {
            "entry_type": "voice",
            "text": message.caption,
            "file_id": message.voice.file_id,
            "file_unique_id": message.voice.file_unique_id,
            "mime_type": message.voice.mime_type,
            "duration_sec": message.voice.duration,
        }

    if message.video_note:
        return {
            "entry_type": "video_note",
            "text": message.caption,
            "file_id": message.video_note.file_id,
            "file_unique_id": message.video_note.file_unique_id,
            "duration_sec": message.video_note.duration,
            "width": message.video_note.length,
            "height": message.video_note.length,
        }

    if message.photo:
        best = message.photo[-1]
        return {
            "entry_type": "photo",
            "text": message.caption,
            "file_id": best.file_id,
            "file_unique_id": best.file_unique_id,
            "width": best.width,
            "height": best.height,
        }

    if message.video:
        return {
            "entry_type": "video",
            "text": message.caption,
            "file_id": message.video.file_id,
            "file_unique_id": message.video.file_unique_id,
            "mime_type": message.video.mime_type,
            "duration_sec": message.video.duration,
            "width": message.video.width,
            "height": message.video.height,
        }

    return None
