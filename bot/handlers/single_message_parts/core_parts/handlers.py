from __future__ import annotations

import html
from datetime import date

from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from backend.database import async_session
from backend.services.user_service import (
    get_or_create_user,
    set_user_daily_water_target,
    set_user_daily_workout_target,
    set_user_preferred_name,
)
from bot.states import DashboardStates

from ..common import VIEW_CALENDAR, VIEW_DIARY, VIEW_HEALTH, VIEW_HOME, VIEW_PROFILE, VIEW_SETTINGS, VIEW_STATS, VIEW_TASKS, VIEW_WATER, _month_start, _render, _reset_context, _setup_chat_ui, router
from .builders import STATS_PERIOD_LABELS, _maybe_start_name_onboarding, _render_command_view, _resolve_cancel_view


@router.message(Command("start"))
@router.message(Command("dashboard"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    if await _maybe_start_name_onboarding(message, state):
        return
    await state.clear()
    today = date.today()
    await state.update_data(
        selected_date=today.isoformat(),
        calendar_month=_month_start(today).isoformat(),
        view_mode=VIEW_HOME,
    )
    await _setup_chat_ui(message, force_keyboard=True)
    await _render(from_user=message.from_user, state=state, message=message)


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext) -> None:
    await _setup_chat_ui(message, force_keyboard=True)
    await _render(
        from_user=message.from_user,
        state=state,
        message=message,
        notice="Нижняя кнопка чата открывает Web App. Разделы вынесены в быстрые кнопки у поля ввода.",
    )


@router.message(StateFilter(DashboardStates.waiting_display_name))
async def msg_display_name(message: Message, state: FSMContext) -> None:
    preferred_name = (message.text or "").strip()
    if not preferred_name:
        await _render(
            from_user=message.from_user,
            state=state,
            message=message,
            notice="Отправь текстом имя или ник, который использовать в боте.",
        )
        return

    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            last_name=message.from_user.last_name,
        )
        await set_user_preferred_name(session, user, preferred_name)

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    data = await state.get_data()
    target_view = data.get("name_origin_view", VIEW_PROFILE)
    await _reset_context(state, view_mode=target_view)
    await _setup_chat_ui(message, force_keyboard=True)
    await _render(
        from_user=message.from_user,
        state=state,
        message=message,
        notice=f"Буду обращаться: {html.escape(preferred_name)}",
    )


@router.message(StateFilter(DashboardStates.waiting_daily_water_target))
async def msg_daily_water_target(message: Message, state: FSMContext) -> None:
    raw_text = (message.text or "").strip()
    if not raw_text.isdigit():
        await _render(
            from_user=message.from_user,
            state=state,
            message=message,
            notice="Нужны только цифры. Пример: 2200",
        )
        return

    target_ml = int(raw_text)
    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            last_name=message.from_user.last_name,
        )
        await set_user_daily_water_target(session, user, target_ml)

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await _reset_context(state, view_mode=VIEW_SETTINGS)
    await _render(
        from_user=message.from_user,
        state=state,
        message=message,
        notice=f"Лимит воды обновлен: {max(250, target_ml)} мл",
    )


@router.message(StateFilter(DashboardStates.waiting_daily_workout_target))
async def msg_daily_workout_target(message: Message, state: FSMContext) -> None:
    raw_text = (message.text or "").strip()
    if not raw_text.isdigit():
        await _render(
            from_user=message.from_user,
            state=state,
            message=message,
            notice="Нужны только цифры. Пример: 40",
        )
        return

    target_min = int(raw_text)
    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            last_name=message.from_user.last_name,
        )
        await set_user_daily_workout_target(session, user, target_min)

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await _reset_context(state, view_mode=VIEW_SETTINGS)
    await _render(
        from_user=message.from_user,
        state=state,
        message=message,
        notice=f"Лимит тренировок обновлен: {max(5, target_min)} мин",
    )


@router.callback_query(F.data == "view:profile")
async def cb_view_profile(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    origin_view = data.get("view_mode", VIEW_HOME)
    await _reset_context(state, view_mode=VIEW_PROFILE)
    await state.update_data(profile_origin_view=origin_view)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "view:settings")
async def cb_view_settings(callback: CallbackQuery, state: FSMContext) -> None:
    await _reset_context(state, view_mode=VIEW_SETTINGS)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "settings:water_target")
async def cb_settings_water_target(callback: CallbackQuery, state: FSMContext) -> None:
    await _reset_context(state, view_mode=VIEW_SETTINGS)
    await state.set_state(DashboardStates.waiting_daily_water_target)
    await _render(from_user=callback.from_user, state=state, callback=callback, notice="Жду новый лимит воды.")
    await callback.answer("Жду число")


@router.callback_query(F.data == "settings:workout_target")
async def cb_settings_workout_target(callback: CallbackQuery, state: FSMContext) -> None:
    await _reset_context(state, view_mode=VIEW_SETTINGS)
    await state.set_state(DashboardStates.waiting_daily_workout_target)
    await _render(from_user=callback.from_user, state=state, callback=callback, notice="Жду новый лимит тренировок.")
    await callback.answer("Жду число")


@router.callback_query(F.data == "profile:edit")
async def cb_profile_edit(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    origin_view = data.get("profile_origin_view", VIEW_PROFILE)
    selected_date, calendar_month, _ = await _reset_context(state, view_mode=VIEW_PROFILE)
    await state.set_state(DashboardStates.waiting_display_name)
    await state.update_data(
        selected_date=selected_date.isoformat(),
        calendar_month=calendar_month.isoformat(),
        view_mode=VIEW_PROFILE,
        profile_origin_view=origin_view,
        name_origin_view=origin_view,
    )
    await _render(
        from_user=callback.from_user,
        state=state,
        callback=callback,
        notice="Напиши новое имя или ник.",
    )
    await callback.answer("Жду имя")


@router.callback_query(F.data == "profile:cancel")
async def cb_profile_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await _reset_context(state, view_mode=VIEW_PROFILE)
    await _render(from_user=callback.from_user, state=state, callback=callback, notice="Изменение имени отменено")
    await callback.answer()


@router.message(Command("home"))
async def cmd_home(message: Message, state: FSMContext) -> None:
    await _render_command_view(message, state, VIEW_HOME)


@router.message(Command("tasks"))
async def cmd_tasks(message: Message, state: FSMContext) -> None:
    await _render_command_view(message, state, VIEW_TASKS)


@router.message(Command("calendar"))
async def cmd_calendar(message: Message, state: FSMContext) -> None:
    await _render_command_view(message, state, VIEW_CALENDAR)


@router.message(Command("stats"))
async def cmd_stats(message: Message, state: FSMContext) -> None:
    await _render_command_view(message, state, VIEW_STATS)


@router.message(Command("health"))
async def cmd_health(message: Message, state: FSMContext) -> None:
    await _render_command_view(message, state, VIEW_HEALTH)


@router.message(Command("water"))
async def cmd_water(message: Message, state: FSMContext) -> None:
    await _render_command_view(message, state, VIEW_WATER)


@router.message(Command("diary"))
async def cmd_diary(message: Message, state: FSMContext) -> None:
    await _render_command_view(message, state, VIEW_DIARY)


@router.message(Command("today"))
async def cmd_today(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    current_view = data.get("view_mode", VIEW_HOME)
    today = date.today()
    await _reset_context(state, view_mode=current_view)
    await state.update_data(
        selected_date=today.isoformat(),
        calendar_month=_month_start(today).isoformat(),
    )
    await _setup_chat_ui(message, force_keyboard=True)
    await _render(
        from_user=message.from_user,
        state=state,
        message=message,
        notice=f"Дата: {today.strftime('%d.%m.%Y')}",
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    target_view = _resolve_cancel_view(current_state)
    await _render_command_view(message, state, target_view, notice="Действие отменено")


@router.callback_query(F.data == "cal:noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data == "view:home")
async def cb_view_home(callback: CallbackQuery, state: FSMContext) -> None:
    await _reset_context(state, view_mode=VIEW_HOME)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "view:tasks")
async def cb_view_tasks(callback: CallbackQuery, state: FSMContext) -> None:
    await _reset_context(state, view_mode=VIEW_TASKS)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "view:calendar")
async def cb_view_calendar(callback: CallbackQuery, state: FSMContext) -> None:
    await _reset_context(state, view_mode=VIEW_CALENDAR)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "view:stats")
async def cb_view_stats(callback: CallbackQuery, state: FSMContext) -> None:
    await _reset_context(state, view_mode=VIEW_STATS)
    await state.update_data(stats_period="all")
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "view:health")
async def cb_view_health(callback: CallbackQuery, state: FSMContext) -> None:
    await _reset_context(state, view_mode=VIEW_HEALTH)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "view:water")
async def cb_view_water(callback: CallbackQuery, state: FSMContext) -> None:
    await _reset_context(state, view_mode=VIEW_WATER)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data.startswith("stats:period:"))
async def cb_stats_period(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        period = callback.data.split(":", 2)[2]
    except IndexError:
        await callback.answer("Ошибка")
        return

    if period not in STATS_PERIOD_LABELS:
        await callback.answer("Ошибка")
        return

    await state.update_data(view_mode=VIEW_STATS, stats_period=period)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer("Период обновлен")


@router.message()
async def fallback(message: Message, state: FSMContext) -> None:
    if await state.get_state() not in {
        DashboardStates.waiting_display_name.state,
        DashboardStates.waiting_water_amount_text.state,
        DashboardStates.waiting_sleep_exact_time.state,
        DashboardStates.waiting_medication_title.state,
        DashboardStates.waiting_medication_dose.state,
        DashboardStates.waiting_medication_time_text.state,
        DashboardStates.waiting_medication_days_text.state,
        DashboardStates.waiting_workout_duration_text.state,
        DashboardStates.waiting_daily_water_target.state,
        DashboardStates.waiting_daily_workout_target.state,
        DashboardStates.waiting_task_title.state,
        DashboardStates.waiting_diary_text.state,
    }:
        try:
            await message.delete()
        except TelegramBadRequest:
            pass

    await _render(
        from_user=message.from_user,
        state=state,
        message=message,
        notice="Управление кнопками. Текст нужен только для имени, названия задачи, записи дневника, точного времени сна, своей длительности тренировки, а в лекарствах — для названия, дозы, времени и числа дней курса.",
    )
