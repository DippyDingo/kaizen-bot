from __future__ import annotations

import html
from datetime import date

from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from backend.database import async_session
from backend.services.user_service import get_or_create_user, set_user_preferred_name
from bot.states import DashboardStates

from .common import (
    HOME_COMPANION_ROLE,
    HOME_DUEL_OPPONENT,
    HOME_DUEL_OPPONENT_WATER_ML,
    HOME_LOCATION_NAME,
    HOME_TRACK_TITLE,
    VIEW_CALENDAR,
    VIEW_HEALTH,
    VIEW_HOME,
    VIEW_PROFILE,
    VIEW_SETTINGS,
    VIEW_STATS,
    VIEW_TASKS,
    _build_companion_hint,
    _display_name,
    _build_mana_bar,
    _build_meter,
    _clamp_percent,
    _format_long_date,
    _month_start,
    _render,
    _reset_context,
    _setup_chat_ui,
    router,
)


def _home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💧150", callback_data="water:150"),
                InlineKeyboardButton(text="💧250", callback_data="water:250"),
                InlineKeyboardButton(text="💧500", callback_data="water:500"),
            ],
            [InlineKeyboardButton(text="↩️ Вода", callback_data="water:undo")],
            [
                InlineKeyboardButton(text="➕ Задача", callback_data="task:add"),
                InlineKeyboardButton(text="➕ Запись", callback_data="diary:add"),
            ],
        ]
    )


def _build_stats_keyboard(_selected_date: date) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[])


def _build_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Профиль", callback_data="view:profile")],
        ]
    )


def _build_settings_text(user, notice: str | None) -> str:
    lines = [
        "<b>⚙️ НАСТРОЙКИ</b>",
        f"Текущее имя: <b>{html.escape(_display_name(user))}</b>",
        "Здесь будут настройки профиля и будущие системные параметры.",
    ]
    if notice:
        lines.extend(["", f"ℹ️ {notice}"])
    return "\n".join(lines)


def _build_profile_keyboard(*, editing: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if editing:
        rows.append([InlineKeyboardButton(text="↩️ Отмена", callback_data="profile:cancel")])
    else:
        rows.append([InlineKeyboardButton(text="✏️ Сменить имя", callback_data="profile:edit")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_profile_text(user, mode: str, notice: str | None) -> str:
    lines = [
        "<b>👤 ПРОФИЛЬ</b>",
        f"Имя в боте: <b>{html.escape(_display_name(user))}</b>",
        f"Telegram: <b>{html.escape(user.first_name)}</b>",
    ]
    if user.username:
        lines.append(f"Username: <b>@{html.escape(user.username)}</b>")
    lines.append(f"С нами с: <b>{user.created_at.strftime('%d.%m.%Y')}</b>")

    if mode == "wait_name":
        lines.extend(["", "Напиши имя или ник, который бот должен использовать дальше."])

    if notice:
        lines.extend(["", f"ℹ️ {notice}"])
    return "\n".join(lines)


def _build_home_text(
    user,
    tasks: list,
    water_ml: int,
    sleep_minutes: int,
    diary_count: int,
    selected_date: date,
    notice: str | None,
) -> str:
    total_tasks = len(tasks)
    done_count = sum(1 for t in tasks if t.is_done)

    hp_percent = _clamp_percent((done_count / total_tasks) * 100 if total_tasks else 0)
    hp_bar = _build_meter(hp_percent, 5, "🟩", "🟥")

    mana_bar, mana_steps = _build_mana_bar(water_ml)

    stamina_percent = _clamp_percent((sleep_minutes / 480) * 100)
    stamina_bar = _build_meter(stamina_percent, 5, "🟨", "⬜️")

    companion_hint = _build_companion_hint(stamina_percent, water_ml, done_count, total_tasks)
    date_prefix = "Сегодня" if selected_date == date.today() else "Дата"

    lines = [
        f"📅 {date_prefix}: {_format_long_date(selected_date)}",
        f"👤 {_display_name(user)} | Ур. {user.level} | ⭐ {user.exp}/{user.exp_to_next_level} EXP",
        f"📍 Локация: {HOME_LOCATION_NAME} | 🔥 Streak: {user.current_streak} дней",
        "",
        f"❤️ HP (Привычки): {hp_bar} [{hp_percent}%]",
        f"💧 Мана (Вода): {mana_bar} [{mana_steps}/5]",
        f"⚡️ Стамина (Сон/Спорт): {stamina_bar} [{stamina_percent}%]",
        "",
        f"⚔️ Дуэль (Вода): Ты [{water_ml}мл] 🆚 {HOME_DUEL_OPPONENT} [{HOME_DUEL_OPPONENT_WATER_ML}мл]",
        f"🎵 Трек: {HOME_TRACK_TITLE}",
        f"📝 Дневник: {diary_count} запис(ей) за день",
        "",
        f"💬 Компаньон ({HOME_COMPANION_ROLE}):",
        f'"{companion_hint}"',
        "",
        "— [ Быстрые действия ] —",
    ]
    if notice:
        lines.extend(["", f"ℹ️ {notice}"])
    return "\n".join(lines)


def _build_stats_text(user, stats: dict[str, int], notice: str | None) -> str:
    tasks_total = stats["tasks_total"]
    tasks_done = stats["tasks_done"]
    sleep_total_minutes = stats["sleep_total_minutes"]
    sleep_hours = sleep_total_minutes // 60
    sleep_minutes_part = sleep_total_minutes % 60
    completion_percent = _clamp_percent((tasks_done / tasks_total) * 100 if tasks_total else 0)
    lines = [
        "<b>📈 СТАТИСТИКА ЗА ВСЕ ВРЕМЯ</b>",
        f"👤 {_display_name(user)}",
        f"🗓 С нами с: <b>{user.created_at.strftime('%d.%m.%Y')}</b>",
        f"⭐ Уровень: <b>{user.level}</b>",
        f"⚡ EXP: <b>{user.exp}/{user.exp_to_next_level}</b>",
        f"🔥 Серия: <b>{user.current_streak}</b> | рекорд <b>{user.longest_streak}</b>",
        f"✅ Задачи: <b>{tasks_done}/{tasks_total}</b> [{completion_percent}%]",
        f"💧 Вода: <b>{stats['water_total_ml']} мл</b>",
        f"😴 Сон: <b>{sleep_hours} ч {sleep_minutes_part} м</b>",
        f"📝 Дневник: <b>{stats['diary_total']}</b> записей",
    ]
    if notice:
        lines.extend(["", f"ℹ️ {notice}"])
    return "\n".join(lines)


async def _render_command_view(message: Message, state: FSMContext, view_mode: str, notice: str | None = None) -> None:
    await _reset_context(state, view_mode=view_mode)
    await _setup_chat_ui(message, force_keyboard=True)
    await _render(from_user=message.from_user, state=state, message=message, notice=notice)


async def _maybe_start_name_onboarding(message: Message, state: FSMContext) -> bool:
    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            last_name=message.from_user.last_name,
        )

    if user.preferred_name:
        return False

    await state.clear()
    today = date.today()
    await state.update_data(
        selected_date=today.isoformat(),
        calendar_month=_month_start(today).isoformat(),
        view_mode=VIEW_PROFILE,
        name_origin_view=VIEW_PROFILE,
    )
    await state.set_state(DashboardStates.waiting_display_name)
    await _setup_chat_ui(message, force_keyboard=True, keyboard_text="Как тебя называть?")
    await _render(
        from_user=message.from_user,
        state=state,
        message=message,
        notice="Напиши имя или ник, который бот будет использовать дальше.",
    )
    return True


def _resolve_cancel_view(raw_state: str | None) -> str:
    if raw_state == DashboardStates.waiting_display_name.state:
        return VIEW_PROFILE
    if raw_state in {
        DashboardStates.waiting_task_title.state,
        DashboardStates.waiting_task_priority.state,
        DashboardStates.waiting_task_date.state,
    }:
        return VIEW_TASKS
    if raw_state == DashboardStates.waiting_diary_text.state:
        return VIEW_DIARY
    return VIEW_HOME


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
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "view:health")
async def cb_view_health(callback: CallbackQuery, state: FSMContext) -> None:
    await _reset_context(state, view_mode=VIEW_HEALTH)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.message()
async def fallback(message: Message, state: FSMContext) -> None:
    if await state.get_state() not in {
        DashboardStates.waiting_display_name.state,
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
        notice="Управление кнопками. Текст нужен только для названия задачи.",
    )
