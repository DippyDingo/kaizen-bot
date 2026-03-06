from __future__ import annotations

import html
from datetime import date

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from backend.database import async_session
from backend.services.user_service import get_or_create_user
from bot.states import DashboardStates

from ..common import (
    HOME_COMPANION_ROLE,
    HOME_DUEL_OPPONENT,
    HOME_DUEL_OPPONENT_WATER_ML,
    HOME_LOCATION_NAME,
    HOME_TRACK_TITLE,
    VIEW_DIARY,
    VIEW_HEALTH,
    VIEW_HOME,
    VIEW_PROFILE,
    VIEW_SETTINGS,
    VIEW_TASKS,
    VIEW_WATER,
    _build_bar_caption,
    _build_companion_hint,
    _build_goal_bar,
    _build_mana_bar,
    _build_metric_bar,
    _clamp_percent,
    _date_nav_row,
    _display_name,
    _format_long_date,
    _month_start,
    _relocate_dashboard_message,
    _render,
    _reset_context,
    _setup_chat_ui,
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


def _home_focus_lines(tasks: list) -> list[str]:
    if not tasks:
        return ["• На сегодня задач нет"]

    priority_order = {"high": 0, "medium": 1, "low": 2}
    priority_badges = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    pending_tasks = [task for task in tasks if not task.is_done]
    if not pending_tasks:
        return ["• Все задачи на сегодня закрыты"]

    ordered = sorted(
        pending_tasks,
        key=lambda task: (priority_order.get(getattr(task, "priority", "low"), 3), getattr(task, "created_at", None) or 0),
    )
    lines: list[str] = []
    for task in ordered[:3]:
        badge = priority_badges.get(task.priority, "⚪")
        title = html.escape(task.title.strip())
        if len(title) > 46:
            title = f"{title[:45]}…"
        lines.append(f"• {badge} {title}")
    remaining = len(ordered) - len(lines)
    if remaining > 0:
        lines.append(f"• И ещё {remaining}")
    return lines


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
    return InlineKeyboardMarkup(inline_keyboard=[_date_nav_row(selected_date), *period_rows])


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
    open_count = total_tasks - done_count

    hp_percent = _clamp_percent((done_count / total_tasks) * 100 if total_tasks else 0)
    hp_bar = _build_metric_bar("tasks", hp_percent)

    mana_bar, mana_steps = _build_mana_bar(water_ml, user.daily_water_target_ml)
    water_percent = _clamp_percent((water_ml / user.daily_water_target_ml) * 100 if user.daily_water_target_ml else 0)

    stamina_percent = _clamp_percent((sleep_minutes / 480) * 100)
    stamina_bar = _build_metric_bar("sleep", stamina_percent)
    sleep_label = _sleep_duration_text(sleep_minutes)

    companion_hint = _build_companion_hint(stamina_percent, water_ml, done_count, total_tasks)
    focus_lines = _home_focus_lines(tasks)
    date_prefix = "Сегодня" if selected_date == date.today() else "Дата"
    lines = [
        "<b>🏠 ГЛАВНАЯ</b>",
        f"📅 {date_prefix}: {_format_long_date(selected_date)}",
        f"👤 <b>{html.escape(_display_name(user))}</b> · Ур. <b>{user.level}</b> · ⭐ <b>{user.exp}/{user.exp_to_next_level}</b>",
        f"🔥 Серия: <b>{user.current_streak}</b> · 📍 {HOME_LOCATION_NAME}",
        "",
        "<b>Сегодня</b>",
        f"• Задачи: <b>{done_count}/{total_tasks}</b>" if total_tasks else "• Задачи: <b>0</b>",
        f"• Открыто: <b>{open_count}</b>",
        f"• Вода: <b>{water_ml}/{user.daily_water_target_ml} мл</b>",
        f"• Сон: <b>{sleep_label}</b>",
        f"• Дневник: <b>{diary_count}</b>",
        "",
        _build_bar_caption("Ритм", hp_bar, f"{hp_percent}%", icon="❤️"),
        _build_bar_caption("Вода", mana_bar, f"{water_percent}%", icon="💧"),
        _build_bar_caption("Сон", stamina_bar, f"{stamina_percent}%", icon="⚡️"),
        "",
        "<b>Фокус дня</b>",
        *focus_lines,
        "",
        "<b>Контекст</b>",
        f"• ⚔️ Дуэль воды: ты <b>{water_ml} мл</b> vs {HOME_DUEL_OPPONENT} <b>{HOME_DUEL_OPPONENT_WATER_ML} мл</b>",
        f"• 🎵 Трек: {html.escape(HOME_TRACK_TITLE)}",
        "",
        f"<b>💬 {HOME_COMPANION_ROLE}</b>",
        f'"{companion_hint}"',
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
    medication_details = stats["medication_details"]
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
        f"• Приоритеты: <b>🔴 {task_details['high_count']}</b> | <b>🟡 {task_details['medium_count']}</b> | <b>🟢 {task_details['low_count']}</b>",
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
        f"• По типам: <b>💪 {workout_details['strength_count']}</b> | <b>🏃 {workout_details['cardio_count']}</b> | <b>🧘 {workout_details['mobility_count']}</b>",
        f"• Минуты по типам: <b>💪 {workout_details['strength_minutes']}</b> | <b>🏃 {workout_details['cardio_minutes']}</b> | <b>🧘 {workout_details['mobility_minutes']}</b>",
        f"• Активных дней: <b>{workout_details['active_days']}</b>",
        f"• Лучший день: <b>{_sleep_duration_text(int(workout_details['best_day_minutes']))}</b>",
        "",
        "<b>Лекарства</b>",
        f"• Приемов: <b>{medication_details['total_logs']}</b>",
        f"• Выпито: <b>{medication_details['taken_count']}</b> | пропусков <b>{medication_details['skipped_count']}</b>",
        f"• Уникальных: <b>{medication_details['unique_titles']}</b>",
        f"• Активных дней: <b>{medication_details['active_days']}</b>",
        f"• Лучший день: <b>{medication_details['best_day_logs']}</b> прием(ов)",
        f"• Чаще всего: <b>{html.escape(str(medication_details['top_title']))}</b>" if medication_details["top_title"] else "• Чаще всего: <b>нет данных</b>",
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


async def _render_command_view(
    message: Message,
    state: FSMContext,
    view_mode: str,
    notice: str | None = None,
    *,
    delete_source_message: bool = False,
    force_keyboard: bool = True,
    relocate_dashboard: bool = False,
) -> None:
    await _reset_context(state, view_mode=view_mode)
    await _setup_chat_ui(message, force_keyboard=force_keyboard)
    if relocate_dashboard:
        await _relocate_dashboard_message(message, state)
    if delete_source_message:
        try:
            await message.delete()
        except TelegramBadRequest:
            pass
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
    await _relocate_dashboard_message(message, state)
    await _render(
        from_user=message.from_user,
        state=state,
        message=message,
        notice="Напиши имя или ник, который бот будет использовать дальше.",
    )
    return True


def _resolve_cancel_view(raw_state: str | None) -> str:
    if raw_state == DashboardStates.waiting_water_amount_text.state:
        return VIEW_WATER
    if raw_state == DashboardStates.waiting_display_name.state:
        return VIEW_PROFILE
    if raw_state == DashboardStates.waiting_sleep_exact_time.state:
        return VIEW_HEALTH
    if raw_state in {
        DashboardStates.waiting_medication_title.state,
        DashboardStates.waiting_medication_dose.state,
        DashboardStates.waiting_medication_time_text.state,
        DashboardStates.waiting_medication_days_text.state,
    }:
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
