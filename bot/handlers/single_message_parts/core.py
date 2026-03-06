from __future__ import annotations

from datetime import date

from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

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
    VIEW_STATS,
    VIEW_TASKS,
    _build_companion_hint,
    _build_mana_bar,
    _build_meter,
    _clamp_percent,
    _format_long_date,
    _month_start,
    _render,
    _reset_context,
    _set_webapp_menu_button,
    router,
)


def _home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💧 +150мл", callback_data="water:150"),
                InlineKeyboardButton(text="💧 +250мл", callback_data="water:250"),
                InlineKeyboardButton(text="💧 +500мл", callback_data="water:500"),
            ],
            [
                InlineKeyboardButton(text="➕ Добавить Дейлик", callback_data="task:add"),
                InlineKeyboardButton(text="📝 Дневник", callback_data="view:diary"),
            ],
            [
                InlineKeyboardButton(text="🗂 Задачи", callback_data="view:tasks"),
                InlineKeyboardButton(text="📅 Календарь", callback_data="view:calendar"),
            ],
            [
                InlineKeyboardButton(text="📈 Статистика", callback_data="view:stats"),
                InlineKeyboardButton(text="💧 Здоровье", callback_data="view:health"),
            ],
        ]
    )


def _build_stats_keyboard(selected_date: date) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="◀️ День", callback_data="date:shift:-1"),
                InlineKeyboardButton(text=selected_date.strftime("%d.%m.%Y"), callback_data="cal:noop"),
                InlineKeyboardButton(text="День ▶️", callback_data="date:shift:1"),
            ],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="view:home")],
        ]
    )


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
        f"👤 {user.first_name} | Ур. {user.level} | ⭐ {user.exp}/{user.exp_to_next_level} EXP",
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


def _build_stats_text(user, tasks: list, water_ml: int, sleep_minutes: int, selected_date: date, notice: str | None) -> str:
    done_count = sum(1 for t in tasks if t.is_done)
    stamina_percent = _clamp_percent((sleep_minutes / 480) * 100)
    lines = [
        "<b>📈 СТАТИСТИКА</b>",
        f"Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>",
        f"👤 {user.first_name}",
        f"⭐ Уровень: <b>{user.level}</b>",
        f"⚡ EXP: <b>{user.exp}/{user.exp_to_next_level}</b>",
        f"✅ Задачи: <b>{done_count}/{len(tasks)}</b>",
        f"💧 Вода: <b>{water_ml} мл</b>",
        f"⚡️ Стамина: <b>{stamina_percent}%</b>",
    ]
    if notice:
        lines.extend(["", f"ℹ️ {notice}"])
    return "\n".join(lines)


@router.message(Command("start"))
@router.message(Command("dashboard"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    today = date.today()
    await state.update_data(
        selected_date=today.isoformat(),
        calendar_month=_month_start(today).isoformat(),
        view_mode=VIEW_HOME,
    )
    await _set_webapp_menu_button(message)
    await _render(from_user=message.from_user, state=state, message=message)


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext) -> None:
    await _set_webapp_menu_button(message)
    await _render(
        from_user=message.from_user,
        state=state,
        message=message,
        notice="Из главного меню вход в раздел, внутри только кнопки раздела и назад.",
    )


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
