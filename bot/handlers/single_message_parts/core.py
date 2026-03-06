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
from backend.services.user_service import (
    get_or_create_user,
    set_user_daily_water_target,
    set_user_daily_workout_target,
    set_user_preferred_name,
)
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
    _build_bar_caption,
    _build_goal_bar,
    _build_companion_hint,
    _build_metric_bar,
    _build_mana_bar,
    _clamp_percent,
    _date_nav_row,
    _display_name,
    _format_long_date,
    _month_start,
    _render,
    _reset_context,
    _setup_chat_ui,
    router,
)


STATS_PERIOD_LABELS = {
    "day": "День",
    "7d": "7 дней",
    "30d": "30 дней",
    "all": "Всё время",
}

STATS_SLEEP_TARGET_MIN_PER_DAY = 480


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


def _build_stats_keyboard(selected_date: date, stats_period: str) -> InlineKeyboardMarkup:
    period_rows = [
        [
            InlineKeyboardButton(
                text=f"• {STATS_PERIOD_LABELS['day']}" if stats_period == "day" else STATS_PERIOD_LABELS["day"],
                callback_data="stats:period:day",
            ),
            InlineKeyboardButton(
                text=f"• {STATS_PERIOD_LABELS['7d']}" if stats_period == "7d" else STATS_PERIOD_LABELS["7d"],
                callback_data="stats:period:7d",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"• {STATS_PERIOD_LABELS['30d']}" if stats_period == "30d" else STATS_PERIOD_LABELS["30d"],
                callback_data="stats:period:30d",
            ),
            InlineKeyboardButton(
                text=f"• {STATS_PERIOD_LABELS['all']}" if stats_period == "all" else STATS_PERIOD_LABELS["all"],
                callback_data="stats:period:all",
            ),
        ],
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _date_nav_row(selected_date),
            *period_rows,
        ]
    )


def _build_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Профиль", callback_data="view:profile")],
            [InlineKeyboardButton(text="💧 Лимит воды", callback_data="settings:water_target")],
            [InlineKeyboardButton(text="🏃 Лимит тренировок", callback_data="settings:workout_target")],
        ]
    )


def _build_settings_text(user, notice: str | None, *, mode: str = "main") -> str:
    lines = [
        "<b>⚙️ НАСТРОЙКИ</b>",
        f"Текущее имя: <b>{html.escape(_display_name(user))}</b>",
        f"Лимит воды в день: <b>{user.daily_water_target_ml} мл</b>",
        f"Лимит тренировок в день: <b>{user.daily_workout_target_min} мин</b>",
    ]
    if mode == "wait_water":
        lines.extend(["", "Отправь новый лимит воды в мл. Пример: <b>2200</b>."])
    elif mode == "wait_workout":
        lines.extend(["", "Отправь новый лимит тренировок в минутах. Пример: <b>40</b>."])
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
    hp_bar = _build_metric_bar("tasks", hp_percent)

    mana_bar, mana_steps = _build_mana_bar(water_ml, user.daily_water_target_ml)

    stamina_percent = _clamp_percent((sleep_minutes / 480) * 100)
    stamina_bar = _build_metric_bar("sleep", stamina_percent)

    companion_hint = _build_companion_hint(stamina_percent, water_ml, done_count, total_tasks)
    date_prefix = "Сегодня" if selected_date == date.today() else "Дата"
    lines = [
        f"📅 {date_prefix}: {_format_long_date(selected_date)}",
        f"👤 {_display_name(user)} | Ур. {user.level} | ⭐ {user.exp}/{user.exp_to_next_level} EXP",
        f"📍 Локация: {HOME_LOCATION_NAME} | 🔥 Streak: {user.current_streak} дней",
        "",
        _build_bar_caption("Ритм", hp_bar, f"{hp_percent}%", icon="❤️"),
        _build_bar_caption("Вода", mana_bar, f"{mana_steps}/5", icon="💧"),
        _build_bar_caption("Сон", stamina_bar, f"{stamina_percent}%", icon="⚡️"),
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


def _build_stats_text(user, stats: dict[str, int | float | str], selected_date: date, notice: str | None) -> str:
    period = str(stats["period"])
    tasks_total = stats["tasks_total"]
    tasks_done = stats["tasks_done"]
    sleep_total_minutes = stats["sleep_total_minutes"]
    sleep_hours = sleep_total_minutes // 60
    sleep_minutes_part = sleep_total_minutes % 60
    completion_percent = _clamp_percent((tasks_done / tasks_total) * 100 if tasks_total else 0)
    period_days = int(stats["period_days"])
    water_total_ml = int(stats["water_total_ml"])
    diary_total = int(stats["diary_total"])
    avg_sleep_quality = float(stats["avg_sleep_quality"])
    avg_water_ml = int(round(water_total_ml / period_days)) if period_days else 0
    avg_sleep_minutes = int(round(sleep_total_minutes / period_days)) if period_days else 0
    avg_sleep_hours = avg_sleep_minutes // 60
    avg_sleep_minutes_part = avg_sleep_minutes % 60
    task_details = stats["task_details"]
    water_details = stats["water_details"]
    sleep_details = stats["sleep_details"]
    workout_details = stats["workout_details"]
    diary_details = stats["diary_details"]
    task_bar = _build_metric_bar("tasks", completion_percent)
    water_bar, water_percent = _build_goal_bar(avg_water_ml, user.daily_water_target_ml, "water")
    sleep_bar, sleep_percent = _build_goal_bar(avg_sleep_minutes, STATS_SLEEP_TARGET_MIN_PER_DAY, "sleep")
    avg_workout_minutes = int(round(int(workout_details["total_minutes"]) / period_days)) if period_days else 0
    workout_bar, workout_percent = _build_goal_bar(avg_workout_minutes, user.daily_workout_target_min, "workout")
    diary_active_percent = _clamp_percent((int(diary_details["active_days"]) / period_days) * 100 if period_days else 0)
    diary_bar = _build_metric_bar("diary", diary_active_percent)
    sleep_quality_percent = _clamp_percent((avg_sleep_quality / 5) * 100 if avg_sleep_quality else 0)
    sleep_quality_bar = _build_metric_bar("quality", sleep_quality_percent)

    if period == "all":
        title = "📈 СТАТИСТИКА ЗА ВСЕ ВРЕМЯ"
        period_line = f"Период: <b>с {user.created_at.strftime('%d.%m.%Y')}</b>"
    elif period == "day":
        title = "📈 СТАТИСТИКА ЗА ДЕНЬ"
        period_line = f"Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>"
    elif period == "7d":
        title = "📈 СТАТИСТИКА ЗА 7 ДНЕЙ"
        period_line = f"До даты: <b>{selected_date.strftime('%d.%m.%Y')}</b>"
    else:
        title = "📈 СТАТИСТИКА ЗА 30 ДНЕЙ"
        period_line = f"До даты: <b>{selected_date.strftime('%d.%m.%Y')}</b>"

    lines = [
        f"<b>{title}</b>",
        f"👤 {_display_name(user)}",
        period_line,
        "",
        "<b>Общее</b>",
        f"• ⭐ Уровень: <b>{user.level}</b>",
        f"• ⚡ EXP: <b>{user.exp}/{user.exp_to_next_level}</b>",
        f"• 🔥 Серия: <b>{user.current_streak}</b> | рекорд <b>{user.longest_streak}</b>",
        f"• 🗓 С нами с: <b>{user.created_at.strftime('%d.%m.%Y')}</b>",
        "",
        "<b>Задачи</b>",
        f"• Выполнено: <b>{tasks_done}/{tasks_total}</b> [{completion_percent}%]",
        f"• {_build_bar_caption('Выполнение', task_bar, f'{completion_percent}%')}",
        (
            f"• Приоритеты: <b>🔴 {task_details['high_count']}</b> | "
            f"<b>🟡 {task_details['medium_count']}</b> | <b>🟢 {task_details['low_count']}</b>"
        ),
        f"• Активных дней: <b>{task_details['active_days']}</b>",
        "",
        "<b>Вода</b>",
        f"• Всего: <b>{water_total_ml} мл</b>",
        f"• Среднее: <b>{avg_water_ml} мл/д</b>",
        f"• {_build_bar_caption('Цель воды', water_bar, f'{water_percent}%')}",
        f"• Активных дней: <b>{water_details['active_days']}</b>",
        f"• Лучший день: <b>{water_details['best_day_ml']} мл</b>",
        "",
        "<b>Сон</b>",
        f"• Всего: <b>{sleep_hours} ч {sleep_minutes_part} м</b>",
        f"• Среднее: <b>{avg_sleep_hours} ч {avg_sleep_minutes_part} м/д</b>",
        f"• {_build_bar_caption('Цель сна', sleep_bar, f'{sleep_percent}%')}",
        f"• Качество: <b>{avg_sleep_quality:.1f}/5</b>" if avg_sleep_quality else "• Качество: <b>нет данных</b>",
        f"• {_build_bar_caption('Качество', sleep_quality_bar, f'{sleep_quality_percent}%')}" if avg_sleep_quality else f"• {_build_bar_caption('Качество', _build_metric_bar('quality', 0), '0%')}",
        f"• Активных дней: <b>{sleep_details['active_days']}</b>",
        f"• Лучший день: <b>{_sleep_duration_text(int(sleep_details['best_day_minutes']))}</b>",
        f"• Самый длинный сон: <b>{_sleep_duration_text(int(sleep_details['longest_log_minutes']))}</b>",
        "",
        "<b>Тренировки</b>",
        f"• Всего: <b>{_sleep_duration_text(int(workout_details['total_minutes']))}</b>",
        f"• Среднее: <b>{_sleep_duration_text(avg_workout_minutes)}/д</b>",
        f"• {_build_bar_caption('Цель тренировок', workout_bar, f'{workout_percent}%')}",
        (
            f"• По типам: <b>💪 {workout_details['strength_count']}</b> | "
            f"<b>🏃 {workout_details['cardio_count']}</b> | <b>🧘 {workout_details['mobility_count']}</b>"
        ),
        (
            f"• Минуты по типам: <b>💪 {workout_details['strength_minutes']}</b> | "
            f"<b>🏃 {workout_details['cardio_minutes']}</b> | <b>🧘 {workout_details['mobility_minutes']}</b>"
        ),
        f"• Активных дней: <b>{workout_details['active_days']}</b>",
        f"• Лучший день: <b>{_sleep_duration_text(int(workout_details['best_day_minutes']))}</b>",
        "",
        "<b>Дневник</b>",
        f"• Записей: <b>{diary_total}</b>",
        f"• {_build_bar_caption('Активность', diary_bar, f'{diary_active_percent}%')}",
        f"• Активных дней: <b>{diary_details['active_days']}</b>",
        f"• Лучший день: <b>{diary_details['best_day_entries']}</b> записей",
    ]
    if notice:
        lines.extend(["", f"ℹ️ {notice}"])
    return "\n".join(lines)


def _sleep_duration_text(minutes: int) -> str:
    if minutes <= 0:
        return "0 ч"
    hours = minutes // 60
    minutes_part = minutes % 60
    if minutes_part == 0:
        return f"{hours} ч"
    return f"{hours} ч {minutes_part} м"


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
    if raw_state == DashboardStates.waiting_sleep_exact_time.state:
        return VIEW_HEALTH
    if raw_state == DashboardStates.waiting_workout_duration_text.state:
        return VIEW_HEALTH
    if raw_state in {
        DashboardStates.waiting_task_title.state,
        DashboardStates.waiting_task_priority.state,
        DashboardStates.waiting_task_date.state,
    }:
        return VIEW_TASKS
    if raw_state in {
        DashboardStates.waiting_daily_water_target.state,
        DashboardStates.waiting_daily_workout_target.state,
    }:
        return VIEW_SETTINGS
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
        DashboardStates.waiting_sleep_exact_time.state,
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
        notice="Управление кнопками. Текст нужен только для имени, названия задачи, записи дневника, точного времени сна, своей длительности тренировки и лимитов в настройках.",
    )
