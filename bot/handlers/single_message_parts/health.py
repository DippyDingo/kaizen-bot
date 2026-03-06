from __future__ import annotations

from datetime import date, datetime

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from backend.database import async_session
from backend.services.health_service import add_water_log, remove_last_water_log
from backend.services.user_service import get_or_create_user

from .common import _back_row, _date_nav_row, _parse_iso_date, _render, router


def _build_health_keyboard(selected_date: date) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _date_nav_row(selected_date),
            [
                InlineKeyboardButton(text="💧150", callback_data="water:150"),
                InlineKeyboardButton(text="💧250", callback_data="water:250"),
                InlineKeyboardButton(text="💧500", callback_data="water:500"),
            ],
            [InlineKeyboardButton(text="↩️ Вода", callback_data="water:undo")],
            _back_row(),
        ]
    )


def _build_health_text(water_ml: int, selected_date: date, notice: str | None) -> str:
    lines = [
        "<b>💧 ЗДОРОВЬЕ</b>",
        f"Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>",
        f"Вода за день: <b>{water_ml} мл</b>",
        "Добавляй воду кнопками.",
    ]
    if notice:
        lines.extend(["", f"ℹ️ {notice}"])
    return "\n".join(lines)


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
