from __future__ import annotations

import html
from datetime import date, timedelta

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from backend.database import async_session
from backend.services.diary_service import list_day_diary_entries
from backend.services.health_service import get_medication_calendar_marks, list_medication_schedule_for_day
from backend.services.user_service import get_or_create_user, set_user_dashboard_message_ref
from bot.states import DashboardStates

from .chat_ui import _ensure_chat_keyboard
from .constants import (
    CONFIGURED_REPLY_KEYBOARD_CHATS,
    DASHBOARD_MESSAGES,
    MAX_TRACKED_OUTPUT_MESSAGES,
    VIEW_CALENDAR,
    VIEW_DIARY,
    VIEW_HEALTH,
    VIEW_HOME,
    VIEW_PROFILE,
    VIEW_SETTINGS,
    VIEW_STATS,
    VIEW_TASKS,
    VIEW_WATER,
)
from .data import _load_health_summary, _load_user_and_metrics, _load_user_period_stats
from .helpers import _month_start, _parse_iso_date


def _is_message_not_modified(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in str(exc).lower()


async def _persist_dashboard_ref(state: FSMContext, from_user, chat_id: int, message_id: int) -> None:
    await state.update_data(dashboard_chat_id=chat_id, dashboard_message_id=message_id)
    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=from_user.id,
            first_name=from_user.first_name,
            username=from_user.username,
            last_name=from_user.last_name,
        )
        await set_user_dashboard_message_ref(
            session,
            user,
            chat_id=chat_id,
            message_id=message_id,
        )


async def _clear_dashboard_ref(state: FSMContext, from_user) -> None:
    await state.update_data(dashboard_chat_id=None, dashboard_message_id=None)
    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=from_user.id,
            first_name=from_user.first_name,
            username=from_user.username,
            last_name=from_user.last_name,
        )
        await set_user_dashboard_message_ref(
            session,
            user,
            chat_id=None,
            message_id=None,
        )


async def _resolve_dashboard_target(message: Message, state: FSMContext) -> tuple[int, int] | None:
    data = await state.get_data()
    chat_id = data.get("dashboard_chat_id")
    message_id = data.get("dashboard_message_id")
    if isinstance(chat_id, int) and isinstance(message_id, int):
        return chat_id, message_id

    key = (message.chat.id, message.from_user.id)
    target = DASHBOARD_MESSAGES.get(key)
    if target:
        return target

    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            last_name=message.from_user.last_name,
        )
        if user.dashboard_chat_id and user.dashboard_message_id:
            return int(user.dashboard_chat_id), int(user.dashboard_message_id)

    return None


async def _relocate_dashboard_message(message: Message, state: FSMContext) -> None:
    target = await _resolve_dashboard_target(message, state)
    key = (message.chat.id, message.from_user.id)

    if target:
        chat_id, message_id = target
        try:
            await message.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except TelegramBadRequest:
            pass

    DASHBOARD_MESSAGES.pop(key, None)
    await _clear_dashboard_ref(state, message.from_user)


async def _edit_dashboard_callback(callback: CallbackQuery, text: str, keyboard: InlineKeyboardMarkup) -> None:
    key = (callback.message.chat.id, callback.from_user.id)
    DASHBOARD_MESSAGES[key] = (callback.message.chat.id, callback.message.message_id)
    if callback.message.chat.id not in CONFIGURED_REPLY_KEYBOARD_CHATS:
        await _ensure_chat_keyboard(callback.message)
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard)
    except TelegramBadRequest as exc:
        if not _is_message_not_modified(exc):
            raise


async def _upsert_dashboard_message(message: Message, state: FSMContext, text: str, keyboard: InlineKeyboardMarkup) -> None:
    key = (message.chat.id, message.from_user.id)
    target = await _resolve_dashboard_target(message, state)

    if target:
        chat_id, message_id = target
        try:
            await message.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=keyboard,
            )
            DASHBOARD_MESSAGES[key] = (chat_id, message_id)
            await state.update_data(dashboard_chat_id=chat_id, dashboard_message_id=message_id)
            return
        except TelegramBadRequest as exc:
            if _is_message_not_modified(exc):
                DASHBOARD_MESSAGES[key] = (chat_id, message_id)
                await state.update_data(dashboard_chat_id=chat_id, dashboard_message_id=message_id)
                return

    sent = await message.answer(text=text, reply_markup=keyboard)
    DASHBOARD_MESSAGES[key] = (sent.chat.id, sent.message_id)
    await _persist_dashboard_ref(state, message.from_user, sent.chat.id, sent.message_id)


async def _remember_output_message(state: FSMContext, bot_message: Message) -> None:
    data = await state.get_data()
    tracked: list[int] = list(data.get("output_message_ids", []))
    tracked.append(bot_message.message_id)
    if len(tracked) > MAX_TRACKED_OUTPUT_MESSAGES:
        tracked = tracked[-MAX_TRACKED_OUTPUT_MESSAGES:]
    await state.update_data(output_message_ids=tracked)


async def _clear_output_messages(message: Message, state: FSMContext) -> tuple[int, int]:
    data = await state.get_data()
    tracked: list[int] = list(data.get("output_message_ids", []))
    if not tracked:
        return 0, 0

    removed = 0
    skipped = 0
    for msg_id in tracked:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
            removed += 1
        except TelegramBadRequest:
            skipped += 1

    await state.update_data(output_message_ids=[])
    return removed, skipped


async def _reset_context(state: FSMContext, *, view_mode: str | None = None) -> tuple[date, date, str]:
    data = await state.get_data()
    selected_date = _parse_iso_date(data.get("selected_date"), date.today())
    calendar_month = _parse_iso_date(data.get("calendar_month"), _month_start(selected_date))
    output_message_ids = list(data.get("output_message_ids", []))
    dashboard_chat_id = data.get("dashboard_chat_id")
    dashboard_message_id = data.get("dashboard_message_id")
    old_view = data.get("view_mode", VIEW_HOME)
    await state.clear()
    resolved_view = view_mode or old_view
    await state.update_data(
        selected_date=selected_date.isoformat(),
        calendar_month=calendar_month.isoformat(),
        view_mode=resolved_view,
        output_message_ids=output_message_ids,
        dashboard_chat_id=dashboard_chat_id,
        dashboard_message_id=dashboard_message_id,
    )
    return selected_date, calendar_month, resolved_view


async def _render(
    *,
    from_user,
    state: FSMContext,
    callback: CallbackQuery | None = None,
    message: Message | None = None,
    notice: str | None = None,
) -> None:
    from ..calendar import _build_calendar_keyboard, _build_calendar_text, _build_diary_calendar_text
    from ..core import (
        _build_home_text,
        _build_profile_keyboard,
        _build_profile_text,
        _build_settings_keyboard,
        _build_settings_text,
        _build_stats_keyboard,
        _build_stats_text,
        _home_keyboard,
    )
    from ..diary import _build_diary_keyboard, _build_diary_text
    from ..health import (
        HEALTH_MODE_MEDICATION_CALENDAR,
        _build_health_keyboard,
        _build_health_text,
    )
    from ..tasks import _build_priority_keyboard, _build_tasks_keyboard, _build_tasks_text
    from ..water import _build_water_keyboard, _build_water_text

    data = await state.get_data()
    selected_date = _parse_iso_date(data.get("selected_date"), date.today())
    calendar_month = _parse_iso_date(data.get("calendar_month"), _month_start(selected_date))
    view_mode = data.get("view_mode", VIEW_HOME)
    diary_calendar_mode = bool(data.get("diary_calendar_mode", False))
    current_state = await state.get_state()

    user, tasks, water_ml, sleep_minutes, diary_count = await _load_user_and_metrics(from_user, selected_date)
    diary_entries: list = []
    if view_mode == VIEW_DIARY or current_state == DashboardStates.waiting_diary_text.state:
        async with async_session() as session:
            diary_entries = await list_day_diary_entries(session, user.id, selected_date, limit=20)

    if current_state == DashboardStates.waiting_task_title.state:
        text = _build_tasks_text(tasks, selected_date, "wait_title", data.get("pending_task_title"), data.get("pending_task_priority"), notice)
        keyboard = _build_tasks_keyboard(tasks, selected_date)
    elif current_state == DashboardStates.waiting_water_amount_text.state:
        text = _build_water_text(user, water_ml, selected_date, notice, mode="wait_amount")
        keyboard = _build_water_keyboard(selected_date, mode="wait_amount")
    elif current_state == DashboardStates.waiting_display_name.state:
        text = _build_profile_text(user, mode="wait_name", notice=notice)
        keyboard = _build_profile_keyboard(editing=True)
    elif current_state in {
        DashboardStates.waiting_medication_title.state,
        DashboardStates.waiting_medication_dose.state,
        DashboardStates.waiting_medication_time_text.state,
        DashboardStates.waiting_medication_days_text.state,
    }:
        health_mode = data.get("health_mode", "summary_day")
        pending_sleep_minutes_raw = data.get("pending_sleep_minutes")
        pending_sleep_minutes = int(pending_sleep_minutes_raw) if pending_sleep_minutes_raw else None
        health_summary = await _load_health_summary(user.id, selected_date)
        health_summary["pending_workout_type"] = data.get("pending_workout_type")
        health_summary["pending_medication_title"] = data.get("pending_medication_title")
        health_summary["pending_medication_time"] = data.get("pending_medication_time")
        health_summary["daily_water_target_ml"] = user.daily_water_target_ml
        health_summary["daily_workout_target_min"] = user.daily_workout_target_min
        text = _build_health_text(
            water_ml,
            sleep_minutes,
            selected_date,
            notice,
            mode=health_mode,
            pending_sleep_minutes=pending_sleep_minutes,
            summary=health_summary,
        )
        keyboard = _build_health_keyboard(selected_date, mode=health_mode, summary=health_summary)
    elif current_state == DashboardStates.waiting_daily_water_target.state:
        text = _build_settings_text(user, notice=notice, mode="wait_water")
        keyboard = _build_settings_keyboard()
    elif current_state == DashboardStates.waiting_daily_workout_target.state:
        text = _build_settings_text(user, notice=notice, mode="wait_workout")
        keyboard = _build_settings_keyboard()
    elif current_state == DashboardStates.waiting_task_priority.state:
        text = _build_tasks_text(tasks, selected_date, "wait_priority", data.get("pending_task_title"), data.get("pending_task_priority"), notice)
        keyboard = _build_priority_keyboard()
    elif current_state == DashboardStates.waiting_task_date.state:
        text = _build_tasks_text(tasks, selected_date, "wait_task_date", data.get("pending_task_title"), data.get("pending_task_priority"), notice)
        keyboard = _build_calendar_keyboard(calendar_month, selected_date, context="create")
    elif current_state == DashboardStates.waiting_diary_text.state:
        text = _build_diary_text(diary_entries, selected_date, "wait_text", notice, total_count=diary_count)
        keyboard = _build_diary_keyboard(selected_date, diary_entries)
    elif view_mode == VIEW_TASKS:
        text = _build_tasks_text(tasks, selected_date, "main", data.get("pending_task_title"), data.get("pending_task_priority"), notice)
        keyboard = _build_tasks_keyboard(tasks, selected_date)
    elif view_mode == VIEW_CALENDAR:
        text = _build_calendar_text(selected_date, notice)
        keyboard = _build_calendar_keyboard(calendar_month, selected_date, context="browse")
    elif view_mode == VIEW_STATS:
        stats_period = data.get("stats_period", "all")
        user, period_stats = await _load_user_period_stats(from_user, selected_date, stats_period)
        text = _build_stats_text(user, period_stats, selected_date, notice)
        keyboard = _build_stats_keyboard(selected_date, stats_period)
    elif view_mode == VIEW_PROFILE:
        text = _build_profile_text(user, mode="main", notice=notice)
        keyboard = _build_profile_keyboard(editing=False)
    elif view_mode == VIEW_SETTINGS:
        text = _build_settings_text(user, notice=notice)
        keyboard = _build_settings_keyboard()
    elif view_mode == VIEW_HEALTH:
        health_mode = data.get("health_mode", "summary_day")
        pending_sleep_minutes_raw = data.get("pending_sleep_minutes")
        pending_sleep_minutes = int(pending_sleep_minutes_raw) if pending_sleep_minutes_raw else None
        health_summary = await _load_health_summary(user.id, selected_date)
        health_summary["pending_workout_type"] = data.get("pending_workout_type")
        health_summary["pending_medication_title"] = data.get("pending_medication_title")
        health_summary["pending_medication_time"] = data.get("pending_medication_time")
        health_summary["daily_water_target_ml"] = user.daily_water_target_ml
        health_summary["daily_workout_target_min"] = user.daily_workout_target_min
        if health_mode == HEALTH_MODE_MEDICATION_CALENDAR:
            month_start = _month_start(calendar_month)
            next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            month_end = next_month - timedelta(days=1)
            async with async_session() as session:
                med_marks = await get_medication_calendar_marks(session, user.id, month_start, month_end)
            text = "\n".join(
                [
                    "<b>💊 КАЛЕНДАРЬ ЛЕКАРСТВ</b>",
                    f"Выбранная дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>",
                    "Метки: 💊 есть прием, ✅ все выпито, ✖️ есть пропуск.",
                    *(["", f"ℹ️ {notice}"] if notice else []),
                ]
            )
            keyboard = _build_calendar_keyboard(calendar_month, selected_date, context="med", marks=med_marks)
        else:
            async with async_session() as session:
                health_summary["medication_schedule"] = await list_medication_schedule_for_day(session, user.id, selected_date)
            text = _build_health_text(
                water_ml,
                sleep_minutes,
                selected_date,
                notice,
                mode=health_mode,
                pending_sleep_minutes=pending_sleep_minutes,
                summary=health_summary,
            )
            keyboard = _build_health_keyboard(selected_date, mode=health_mode, summary=health_summary)
    elif view_mode == VIEW_WATER:
        text = _build_water_text(user, water_ml, selected_date, notice)
        keyboard = _build_water_keyboard(selected_date)
    elif view_mode == VIEW_DIARY and diary_calendar_mode:
        text = _build_diary_calendar_text(selected_date, notice)
        keyboard = _build_calendar_keyboard(calendar_month, selected_date, context="diary")
    elif view_mode == VIEW_DIARY:
        text = _build_diary_text(diary_entries, selected_date, "main", notice, total_count=diary_count)
        keyboard = _build_diary_keyboard(selected_date, diary_entries)
    else:
        text = _build_home_text(user, tasks, water_ml, sleep_minutes, diary_count, selected_date, notice)
        keyboard = _home_keyboard()

    if callback:
        await _persist_dashboard_ref(state, callback.from_user, callback.message.chat.id, callback.message.message_id)
        await _edit_dashboard_callback(callback, text, keyboard)
    elif message:
        await _upsert_dashboard_message(message, state, text, keyboard)


async def _send_diary_entry_to_chat(message: Message, entry, state: FSMContext | None = None) -> bool:
    text = (entry.text or "").strip()
    safe_text = html.escape(text)

    try:
        if entry.entry_type == "text":
            sent = await message.answer(f"📝 <b>Запись #{entry.id}</b>\n{safe_text or '(пусто)'}")
            if state:
                await _remember_output_message(state, sent)
            return True

        caption = f"📝 Запись #{entry.id}"
        if safe_text:
            caption = f"{caption}\n{safe_text}"

        if entry.entry_type == "voice" and entry.file_id:
            sent = await message.answer_voice(voice=entry.file_id, caption=caption[:1024])
            if state:
                await _remember_output_message(state, sent)
            return True

        if entry.entry_type == "video_note" and entry.file_id:
            sent_note = await message.answer_video_note(video_note=entry.file_id)
            if state:
                await _remember_output_message(state, sent_note)
            if safe_text:
                sent_caption = await message.answer(f"📝 <b>Запись #{entry.id}</b>\n{safe_text}")
                if state:
                    await _remember_output_message(state, sent_caption)
            return True

        if entry.entry_type == "photo" and entry.file_id:
            sent = await message.answer_photo(photo=entry.file_id, caption=caption[:1024])
            if state:
                await _remember_output_message(state, sent)
            return True

        if entry.entry_type == "video" and entry.file_id:
            sent = await message.answer_video(video=entry.file_id, caption=caption[:1024])
            if state:
                await _remember_output_message(state, sent)
            return True

        sent = await message.answer(f"📝 <b>Запись #{entry.id}</b>\n{safe_text or 'Тип записи не поддерживается.'}")
        if state:
            await _remember_output_message(state, sent)
        return True
    except TelegramBadRequest:
        return False
