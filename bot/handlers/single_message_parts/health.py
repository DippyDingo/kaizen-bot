from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta

from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from backend.database import async_session
from backend.services.health_service import add_sleep_log, add_water_log, remove_last_sleep_log, remove_last_water_log
from backend.services.user_service import get_or_create_user
from bot.states import DashboardStates

from .common import VIEW_HEALTH, _build_meter, _clamp_percent, _date_nav_row, _parse_iso_date, _render, router


HEALTH_MODE_SUMMARY_DAY = "summary_day"
HEALTH_MODE_SUMMARY_WEEK = "summary_week"
HEALTH_MODE_SLEEP_DURATION = "sleep_duration"
HEALTH_MODE_SLEEP_QUALITY = "sleep_quality"
HEALTH_MODE_SLEEP_EXACT = "sleep_exact"

SLEEP_DURATION_OPTIONS = (300, 360, 420, 480, 540, 600)
SLEEP_QUALITY_LABELS = {
    1: "1",
    2: "2",
    3: "3",
    4: "4",
    5: "5",
}

DAILY_WATER_TARGET_ML = 2500
DAILY_SLEEP_TARGET_MIN = 480


def _format_minutes(total_minutes: int) -> str:
    hours = total_minutes // 60
    minutes = total_minutes % 60
    if minutes == 0:
        return f"{hours} ч"
    return f"{hours} ч {minutes} м"


def _sleep_duration_label(minutes: int) -> str:
    hours = minutes // 60
    minutes_part = minutes % 60
    if minutes_part == 0:
        return f"{hours}ч"
    return f"{hours}ч {minutes_part}м"


def _progress_bar(current: int, target: int, filled: str, empty: str) -> tuple[str, int]:
    percent = _clamp_percent((current / target) * 100 if target > 0 else 0)
    return _build_meter(percent, 5, filled, empty), percent


def _build_health_keyboard(
    selected_date: date,
    *,
    mode: str = HEALTH_MODE_SUMMARY_DAY,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        _date_nav_row(selected_date),
        [
            InlineKeyboardButton(
                text="• День" if mode == HEALTH_MODE_SUMMARY_DAY else "День",
                callback_data="health:mode:day",
            ),
            InlineKeyboardButton(
                text="• Неделя" if mode == HEALTH_MODE_SUMMARY_WEEK else "Неделя",
                callback_data="health:mode:week",
            ),
        ],
    ]

    if mode == HEALTH_MODE_SLEEP_DURATION:
        rows.extend(
            [
                [
                    InlineKeyboardButton(text="5ч", callback_data="sleep:dur:300"),
                    InlineKeyboardButton(text="6ч", callback_data="sleep:dur:360"),
                    InlineKeyboardButton(text="7ч", callback_data="sleep:dur:420"),
                ],
                [
                    InlineKeyboardButton(text="8ч", callback_data="sleep:dur:480"),
                    InlineKeyboardButton(text="9ч", callback_data="sleep:dur:540"),
                    InlineKeyboardButton(text="10ч", callback_data="sleep:dur:600"),
                ],
                [InlineKeyboardButton(text="🕒 Точное время", callback_data="sleep:exact")],
                [InlineKeyboardButton(text="↩️ Назад", callback_data="sleep:cancel")],
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=rows)

    if mode == HEALTH_MODE_SLEEP_QUALITY:
        rows.extend(
            [
                [InlineKeyboardButton(text=SLEEP_QUALITY_LABELS[quality], callback_data=f"sleep:quality:{quality}") for quality in (1, 2, 3, 4, 5)],
                [InlineKeyboardButton(text="↩️ Назад", callback_data="sleep:back")],
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=rows)

    if mode == HEALTH_MODE_SLEEP_EXACT:
        rows.extend(
            [
                [InlineKeyboardButton(text="↩️ Назад", callback_data="sleep:exact:cancel")],
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=rows)

    rows.extend(
        [
            [
                InlineKeyboardButton(text="💧150", callback_data="water:150"),
                InlineKeyboardButton(text="💧250", callback_data="water:250"),
                InlineKeyboardButton(text="💧500", callback_data="water:500"),
            ],
            [InlineKeyboardButton(text="↩️ Вода", callback_data="water:undo")],
            [InlineKeyboardButton(text="😴 Добавить сон", callback_data="sleep:start")],
            [InlineKeyboardButton(text="↩️ Сон", callback_data="sleep:undo")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_health_text(
    water_ml: int,
    sleep_minutes: int,
    selected_date: date,
    notice: str | None,
    *,
    mode: str = HEALTH_MODE_SUMMARY_DAY,
    pending_sleep_minutes: int | None = None,
    summary: dict | None = None,
) -> str:
    stamina_percent = _clamp_percent((sleep_minutes / 480) * 100)
    summary = summary or {}
    day_water_bar, day_water_percent = _progress_bar(water_ml, DAILY_WATER_TARGET_ML, "🟦", "⬜️")
    day_sleep_bar, day_sleep_percent = _progress_bar(sleep_minutes, DAILY_SLEEP_TARGET_MIN, "🟨", "⬜️")
    week_water_total = int(summary.get("week_water_total", 0))
    week_sleep_total = int(summary.get("week_sleep_total", 0))
    week_water_bar, week_water_percent = _progress_bar(week_water_total, DAILY_WATER_TARGET_ML * 7, "🟦", "⬜️")
    week_sleep_bar, week_sleep_percent = _progress_bar(week_sleep_total, DAILY_SLEEP_TARGET_MIN * 7, "🟨", "⬜️")

    lines: list[str]
    if mode == HEALTH_MODE_SUMMARY_WEEK:
        lines = [
            "<b>❤️ ЗДОРОВЬЕ • НЕДЕЛЯ</b>",
            f"Период: <b>{summary.get('week_from', selected_date).strftime('%d.%m')} - {selected_date.strftime('%d.%m.%Y')}</b>",
            "",
            "<b>💧 Вода</b>",
            f"• Сумма: <b>{summary.get('week_water_total', 0)} мл</b>",
            f"• Прогресс: {week_water_bar} <b>{week_water_percent}%</b>",
            f"• Среднее: <b>{summary.get('week_water_avg', 0)} мл/д</b>",
            f"• Активных дней: <b>{summary.get('week_water_active_days', 0)}/7</b>",
            f"• Лучший день: <b>{summary.get('week_best_water_day', 0)} мл</b>",
            "",
            "<b>😴 Сон</b>",
            f"• Сумма: <b>{_format_minutes(int(summary.get('week_sleep_total', 0)))}</b>",
            f"• Прогресс: {week_sleep_bar} <b>{week_sleep_percent}%</b>",
            f"• Среднее: <b>{_format_minutes(int(summary.get('week_sleep_avg', 0)))}/д</b>",
            (
                f"• Качество: <b>{float(summary.get('week_avg_quality', 0)):.1f}/5</b>"
                if summary.get("week_avg_quality", 0)
                else "• Качество: <b>нет данных</b>"
            ),
            f"• Активных дней: <b>{summary.get('week_sleep_active_days', 0)}/7</b>",
            f"• Лучший день: <b>{_format_minutes(int(summary.get('week_best_sleep_day', 0)))}</b>",
        ]
    else:
        day_quality = float(summary.get("day_avg_quality", 0))
        lines = [
            "<b>❤️ ЗДОРОВЬЕ • ДЕНЬ</b>",
            f"Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>",
            "",
            "<b>Сегодня</b>",
            f"• 💧 Вода: <b>{water_ml} мл</b>",
            f"• Прогресс воды: {day_water_bar} <b>{day_water_percent}%</b>",
            f"• 😴 Сон: <b>{_format_minutes(sleep_minutes)}</b>",
            f"• Прогресс сна: {day_sleep_bar} <b>{day_sleep_percent}%</b>",
            f"• ⚡ Стамина: <b>{stamina_percent}%</b>",
            (
                f"• ⭐ Качество сна: <b>{day_quality:.1f}/5</b>"
                if day_quality
                else "• ⭐ Качество сна: <b>нет данных</b>"
            ),
            "",
            "<b>Быстрые действия</b>",
            "• вода и сон добавляются кнопками ниже",
        ]

    if mode == HEALTH_MODE_SLEEP_DURATION:
        lines.extend(["", "<b>Добавление сна</b>", "Выбери длительность сна.", "Или перейди в точный режим."])
    elif mode == HEALTH_MODE_SLEEP_QUALITY:
        duration_label = _sleep_duration_label(pending_sleep_minutes or 0)
        lines.extend(
            [
                "",
                "<b>Качество сна</b>",
                f"Длительность: <b>{duration_label}</b>",
                "Оцени качество по шкале 1-5.",
            ]
        )
    elif mode == HEALTH_MODE_SLEEP_EXACT:
        lines.extend(
            [
                "",
                "<b>Точное время сна</b>",
                "Отправь время сна в формате:",
                "<b>23:40 07:15</b>",
                "или",
                "<b>23:40-07:15</b>",
                "Первое время — засыпание, второе — подъем.",
                "Если время засыпания позже времени подъема, бот считает, что ты уснул накануне.",
            ]
        )
    if notice:
        lines.extend(["", f"ℹ️ {notice}"])
    return "\n".join(lines)


def _build_sleep_datetimes(target_day: date, duration_minutes: int) -> tuple[datetime, datetime]:
    woke_up_at = datetime.combine(target_day, time(hour=8, minute=0))
    fell_asleep_at = woke_up_at - timedelta(minutes=duration_minutes)
    return fell_asleep_at, woke_up_at


def _build_exact_sleep_datetimes(target_day: date, fell_time: time, wake_time: time) -> tuple[datetime, datetime]:
    woke_up_at = datetime.combine(target_day, wake_time)
    fell_day = target_day - timedelta(days=1) if fell_time >= wake_time else target_day
    fell_asleep_at = datetime.combine(fell_day, fell_time)
    return fell_asleep_at, woke_up_at


def _parse_exact_sleep_input(raw_text: str, target_day: date) -> tuple[datetime, datetime] | None:
    matches = re.findall(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", raw_text)
    if len(matches) != 2:
        return None

    fell_hour, fell_minute = map(int, matches[0])
    wake_hour, wake_minute = map(int, matches[1])

    fell_time = time(hour=fell_hour, minute=fell_minute)
    wake_time = time(hour=wake_hour, minute=wake_minute)
    fell_asleep_at, woke_up_at = _build_exact_sleep_datetimes(target_day, fell_time, wake_time)

    if woke_up_at <= fell_asleep_at:
        return None

    return fell_asleep_at, woke_up_at


async def _reset_health_mode(state: FSMContext) -> None:
    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=HEALTH_MODE_SUMMARY_DAY,
        pending_sleep_minutes=None,
        pending_sleep_exact_fell=None,
        pending_sleep_exact_wake=None,
    )


@router.callback_query(F.data.startswith("water:"))
async def cb_water(callback: CallbackQuery, state: FSMContext) -> None:
    action = callback.data.split(":", 1)[1]
    if action == "undo":
        await _undo_water(callback, state)
        return

    try:
        amount_ml = int(action)
    except (ValueError, IndexError):
        await callback.answer("Ошибка")
        return

    data = await state.get_data()
    selected_date = _parse_iso_date(data.get("selected_date"), date.today())
    logged_at = datetime.combine(selected_date, datetime.now().time())

    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            last_name=callback.from_user.last_name,
        )
        level_ups = await add_water_log(session, user, amount_ml, logged_at=logged_at)

    await _reset_health_mode(state)

    notice = f"Добавлено {amount_ml} мл воды (+2 EXP)"
    if level_ups > 0:
        notice += f" | Уровень +{level_ups}"

    await _render(from_user=callback.from_user, state=state, callback=callback, notice=notice)
    await callback.answer("Записано")


async def _undo_water(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected_date = _parse_iso_date(data.get("selected_date"), date.today())

    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            last_name=callback.from_user.last_name,
        )
        amount_ml, level_change = await remove_last_water_log(session, user, selected_date)

    await _reset_health_mode(state)

    if amount_ml is None:
        await _render(
            from_user=callback.from_user,
            state=state,
            callback=callback,
            notice="За выбранный день нечего отменять.",
        )
        await callback.answer("Пусто")
        return

    notice = f"Убрано {amount_ml} мл воды (-2 EXP)"
    if level_change < 0:
        notice += f" | Уровень {level_change}"

    await _render(from_user=callback.from_user, state=state, callback=callback, notice=notice)
    await callback.answer("Отменено")


@router.callback_query(F.data == "sleep:start")
async def cb_sleep_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=HEALTH_MODE_SLEEP_DURATION,
        pending_sleep_minutes=None,
        pending_sleep_exact_fell=None,
        pending_sleep_exact_wake=None,
    )
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer("Выбери длительность")


@router.callback_query(F.data == "sleep:cancel")
async def cb_sleep_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await _reset_health_mode(state)
    await _render(from_user=callback.from_user, state=state, callback=callback, notice="Запись сна отменена")
    await callback.answer()


@router.callback_query(F.data == "sleep:back")
async def cb_sleep_back(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("pending_sleep_exact_fell") and data.get("pending_sleep_exact_wake"):
        await state.set_state(DashboardStates.waiting_sleep_exact_time)
        await state.update_data(
            view_mode=VIEW_HEALTH,
            health_mode=HEALTH_MODE_SLEEP_EXACT,
            pending_sleep_minutes=None,
            pending_sleep_exact_fell=None,
            pending_sleep_exact_wake=None,
        )
    else:
        await state.set_state(None)
        await state.update_data(
            view_mode=VIEW_HEALTH,
            health_mode=HEALTH_MODE_SLEEP_DURATION,
            pending_sleep_exact_fell=None,
            pending_sleep_exact_wake=None,
        )
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "sleep:exact")
async def cb_sleep_exact(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DashboardStates.waiting_sleep_exact_time)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=HEALTH_MODE_SLEEP_EXACT,
        pending_sleep_minutes=None,
        pending_sleep_exact_fell=None,
        pending_sleep_exact_wake=None,
    )
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer("Жду время")


@router.callback_query(F.data == "sleep:exact:cancel")
async def cb_sleep_exact_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=HEALTH_MODE_SLEEP_DURATION,
        pending_sleep_minutes=None,
        pending_sleep_exact_fell=None,
        pending_sleep_exact_wake=None,
    )
    await _render(from_user=callback.from_user, state=state, callback=callback, notice="Точный ввод сна отменен")
    await callback.answer()


@router.callback_query(F.data.startswith("health:mode:"))
async def cb_health_mode(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        mode_raw = callback.data.split(":", 2)[2]
    except IndexError:
        await callback.answer("Ошибка")
        return

    if mode_raw == "day":
        mode = HEALTH_MODE_SUMMARY_DAY
    elif mode_raw == "week":
        mode = HEALTH_MODE_SUMMARY_WEEK
    else:
        await callback.answer("Ошибка")
        return

    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=mode,
        pending_sleep_minutes=None,
        pending_sleep_exact_fell=None,
        pending_sleep_exact_wake=None,
    )
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer("Экран обновлен")


@router.callback_query(F.data.startswith("sleep:dur:"))
async def cb_sleep_duration(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        duration_minutes = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка")
        return

    if duration_minutes not in SLEEP_DURATION_OPTIONS:
        await callback.answer("Ошибка")
        return

    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=HEALTH_MODE_SLEEP_QUALITY,
        pending_sleep_minutes=duration_minutes,
        pending_sleep_exact_fell=None,
        pending_sleep_exact_wake=None,
    )
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer("Оцени качество")


@router.callback_query(F.data.startswith("sleep:quality:"))
async def cb_sleep_quality(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        quality = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка")
        return

    if quality not in SLEEP_QUALITY_LABELS:
        await callback.answer("Ошибка")
        return

    data = await state.get_data()
    exact_fell_raw = data.get("pending_sleep_exact_fell")
    exact_wake_raw = data.get("pending_sleep_exact_wake")
    if exact_fell_raw and exact_wake_raw:
        fell_asleep_at = datetime.fromisoformat(exact_fell_raw)
        woke_up_at = datetime.fromisoformat(exact_wake_raw)
        duration_minutes = int((woke_up_at - fell_asleep_at).total_seconds() // 60)
    else:
        duration_minutes = int(data.get("pending_sleep_minutes") or 0)
        if duration_minutes not in SLEEP_DURATION_OPTIONS:
            await state.update_data(health_mode=HEALTH_MODE_SLEEP_DURATION, pending_sleep_minutes=None)
            await _render(
                from_user=callback.from_user,
                state=state,
                callback=callback,
                notice="Сначала выбери длительность сна.",
            )
            await callback.answer("Нет длительности")
            return

        selected_date = _parse_iso_date(data.get("selected_date"), date.today())
        fell_asleep_at, woke_up_at = _build_sleep_datetimes(selected_date, duration_minutes)

    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            last_name=callback.from_user.last_name,
        )
        _, level_ups = await add_sleep_log(
            session=session,
            user=user,
            fell_asleep_at=fell_asleep_at,
            woke_up_at=woke_up_at,
            quality=quality,
        )

    await _reset_health_mode(state)

    notice = f"Сон {_sleep_duration_label(duration_minutes)} сохранен, качество {quality}/5 (+20 EXP)"
    if level_ups > 0:
        notice += f" | Уровень +{level_ups}"

    await _render(from_user=callback.from_user, state=state, callback=callback, notice=notice)
    await callback.answer("Сон записан")


@router.message(StateFilter(DashboardStates.waiting_sleep_exact_time), F.text)
async def msg_sleep_exact_time(message: Message, state: FSMContext) -> None:
    raw_text = (message.text or "").strip()
    data = await state.get_data()
    selected_date = _parse_iso_date(data.get("selected_date"), date.today())
    parsed = _parse_exact_sleep_input(raw_text, selected_date)

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    if parsed is None:
        await state.update_data(
            view_mode=VIEW_HEALTH,
            health_mode=HEALTH_MODE_SLEEP_EXACT,
            pending_sleep_exact_fell=None,
            pending_sleep_exact_wake=None,
        )
        await _render(
            from_user=message.from_user,
            state=state,
            message=message,
            notice="Формат не распознан. Пример: 23:40 07:15",
        )
        return

    fell_asleep_at, woke_up_at = parsed
    duration_minutes = int((woke_up_at - fell_asleep_at).total_seconds() // 60)
    if duration_minutes <= 0:
        await state.update_data(
            view_mode=VIEW_HEALTH,
            health_mode=HEALTH_MODE_SLEEP_EXACT,
            pending_sleep_exact_fell=None,
            pending_sleep_exact_wake=None,
        )
        await _render(
            from_user=message.from_user,
            state=state,
            message=message,
            notice="Подъем должен быть позже засыпания.",
        )
        return

    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=HEALTH_MODE_SLEEP_QUALITY,
        pending_sleep_minutes=duration_minutes,
        pending_sleep_exact_fell=fell_asleep_at.isoformat(),
        pending_sleep_exact_wake=woke_up_at.isoformat(),
    )
    await _render(
        from_user=message.from_user,
        state=state,
        message=message,
        notice=f"Время сна: {fell_asleep_at.strftime('%H:%M')} -> {woke_up_at.strftime('%H:%M')}. Теперь оцени качество.",
    )


@router.callback_query(F.data == "sleep:undo")
async def cb_sleep_undo(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected_date = _parse_iso_date(data.get("selected_date"), date.today())

    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            last_name=callback.from_user.last_name,
        )
        duration_minutes, level_change, quality = await remove_last_sleep_log(session, user, selected_date)

    await _reset_health_mode(state)

    if duration_minutes is None:
        await _render(
            from_user=callback.from_user,
            state=state,
            callback=callback,
            notice="За выбранный день нечего откатывать по сну.",
        )
        await callback.answer("Пусто")
        return

    notice = f"Убран сон {_sleep_duration_label(duration_minutes)}"
    if quality is not None:
        notice += f", качество {quality}/5"
    notice += " (-20 EXP)"
    if level_change < 0:
        notice += f" | Уровень {level_change}"

    await _render(from_user=callback.from_user, state=state, callback=callback, notice=notice)
    await callback.answer("Сон отменен")
