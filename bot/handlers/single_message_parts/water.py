from __future__ import annotations

import re
from datetime import date, datetime

from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from backend.database import async_session
from backend.services.health_service import add_water_log
from backend.services.user_service import get_or_create_user
from bot.states import DashboardStates

from .common import VIEW_HEALTH, VIEW_WATER, _build_bar_caption, _build_goal_bar, _date_nav_row, _render, _reset_context, router
from .health import _reset_health_mode


def _build_water_keyboard(selected_date: date, *, mode: str = "main") -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        _date_nav_row(selected_date),
        [
            InlineKeyboardButton(text="💧150", callback_data="water:150"),
            InlineKeyboardButton(text="💧250", callback_data="water:250"),
            InlineKeyboardButton(text="💧500", callback_data="water:500"),
        ],
    ]

    if mode == "wait_amount":
        rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="water:custom:cancel")])
    else:
        rows.append(
            [
                InlineKeyboardButton(text="↩️ Отмена", callback_data="water:undo"),
                InlineKeyboardButton(text="⌨️ Точно", callback_data="water:custom"),
            ]
        )
        rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="water:back")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_water_text(user, water_ml: int, selected_date: date, notice: str | None, *, mode: str = "main") -> str:
    target_ml = user.daily_water_target_ml
    bar, percent = _build_goal_bar(water_ml, target_ml, "water")
    remaining_ml = max(target_ml - water_ml, 0)

    lines = [
        "<b>💧 ВОДА</b>",
        f"Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>",
        "",
        f"• Выпито: <b>{water_ml} мл</b>",
        f"• Цель: <b>{target_ml} мл</b>",
        f"• Осталось: <b>{remaining_ml} мл</b>",
        f"• {_build_bar_caption('Прогресс', bar, f'{percent}%')}",
    ]

    if mode == "wait_amount":
        lines.extend(["", "Отправь точный объём воды в мл. Пример: <b>330</b>."])
    else:
        lines.extend(["", "Выбери быстрый объём кнопками ниже или укажи точное количество воды."])

    if notice:
        lines.extend(["", f"ℹ️ {notice}"])
    return "\n".join(lines)


def _parse_water_amount_input(raw_text: str) -> int | None:
    match = re.search(r"(\d{1,5})", raw_text.strip())
    if not match:
        return None
    amount_ml = int(match.group(1))
    return amount_ml if amount_ml > 0 else None


async def _go_back_from_water(callback: CallbackQuery, state: FSMContext, notice: str | None = None) -> None:
    data = await state.get_data()
    target_view = data.get("water_origin_view", VIEW_HEALTH)

    if target_view == VIEW_HEALTH:
        await _reset_health_mode(state)
    else:
        await _reset_context(state, view_mode=target_view)

    await _render(from_user=callback.from_user, state=state, callback=callback, notice=notice)


@router.callback_query(F.data == "water:back")
async def cb_water_back(callback: CallbackQuery, state: FSMContext) -> None:
    await _go_back_from_water(callback, state)
    await callback.answer()


@router.callback_query(F.data == "water:custom")
async def cb_water_custom(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    origin_view = data.get("water_origin_view", VIEW_HEALTH)
    await state.set_state(DashboardStates.waiting_water_amount_text)
    await state.update_data(view_mode=VIEW_WATER, water_origin_view=origin_view)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer("Жду мл")


@router.callback_query(F.data == "water:custom:cancel")
async def cb_water_custom_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    origin_view = data.get("water_origin_view", VIEW_HEALTH)
    await _reset_context(state, view_mode=VIEW_WATER)
    await state.update_data(water_origin_view=origin_view)
    await _render(from_user=callback.from_user, state=state, callback=callback, notice="Точный ввод отменен")
    await callback.answer()


@router.message(StateFilter(DashboardStates.waiting_water_amount_text), F.text)
async def msg_water_amount_text(message: Message, state: FSMContext) -> None:
    amount_ml = _parse_water_amount_input(message.text or "")
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    if amount_ml is None:
        await _render(
            from_user=message.from_user,
            state=state,
            message=message,
            notice="Нужен объём в мл. Пример: 330",
        )
        return

    data = await state.get_data()
    origin_view = data.get("water_origin_view", VIEW_HEALTH)
    selected_date = date.fromisoformat(data.get("selected_date", date.today().isoformat()))
    logged_at = datetime.combine(selected_date, datetime.now().time())

    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            last_name=message.from_user.last_name,
        )
        level_ups = await add_water_log(session, user, amount_ml, logged_at=logged_at)

    await state.set_state(None)
    await state.update_data(view_mode=VIEW_WATER, water_origin_view=origin_view)
    notice = f"Добавлено {amount_ml} мл воды (+2 EXP)"
    if level_ups > 0:
        notice += f" | Уровень +{level_ups}"

    await _render(from_user=message.from_user, state=state, message=message, notice=notice)


__all__ = [
    "_build_water_keyboard",
    "_build_water_text",
]
