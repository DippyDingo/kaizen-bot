from __future__ import annotations

from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import WellbeingLog


def _clamp_level(value: int) -> int:
    return min(5, max(1, int(value)))


def _build_wellbeing_details(logs: list[WellbeingLog]) -> dict[str, int | float | date | None]:
    if not logs:
        return {
            "entries_count": 0,
            "active_days": 0,
            "avg_energy": 0.0,
            "avg_stress": 0.0,
            "best_energy_day": None,
            "highest_stress_day": None,
        }

    entries_count = len(logs)
    active_days = len({log.logged_date for log in logs})
    avg_energy = sum(log.energy_level for log in logs) / entries_count
    avg_stress = sum(log.stress_level for log in logs) / entries_count
    best_energy_day = max(logs, key=lambda log: (log.energy_level, log.logged_date)).logged_date
    highest_stress_day = max(logs, key=lambda log: (log.stress_level, log.logged_date)).logged_date

    return {
        "entries_count": entries_count,
        "active_days": active_days,
        "avg_energy": round(avg_energy, 2),
        "avg_stress": round(avg_stress, 2),
        "best_energy_day": best_energy_day,
        "highest_stress_day": highest_stress_day,
    }


async def upsert_wellbeing_log(
    session: AsyncSession,
    user_id: int,
    logged_date: date,
    energy_level: int,
    stress_level: int,
) -> WellbeingLog:
    result = await session.execute(
        select(WellbeingLog).where(
            and_(
                WellbeingLog.user_id == user_id,
                WellbeingLog.logged_date == logged_date,
            )
        )
    )
    wellbeing_log = result.scalar_one_or_none()
    safe_energy = _clamp_level(energy_level)
    safe_stress = _clamp_level(stress_level)

    if wellbeing_log:
        wellbeing_log.energy_level = safe_energy
        wellbeing_log.stress_level = safe_stress
    else:
        wellbeing_log = WellbeingLog(
            user_id=user_id,
            logged_date=logged_date,
            energy_level=safe_energy,
            stress_level=safe_stress,
        )
        session.add(wellbeing_log)

    await session.commit()
    await session.refresh(wellbeing_log)
    return wellbeing_log


async def get_wellbeing_for_day(
    session: AsyncSession,
    user_id: int,
    target_day: date,
) -> dict[str, int | bool]:
    result = await session.execute(
        select(WellbeingLog).where(
            and_(
                WellbeingLog.user_id == user_id,
                WellbeingLog.logged_date == target_day,
            )
        )
    )
    wellbeing_log = result.scalar_one_or_none()
    if not wellbeing_log:
        return {
            "energy_level": 0,
            "stress_level": 0,
            "has_entry": False,
        }

    return {
        "energy_level": int(wellbeing_log.energy_level),
        "stress_level": int(wellbeing_log.stress_level),
        "has_entry": True,
    }


async def get_wellbeing_details_for_period(
    session: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
) -> dict[str, int | float | date | None]:
    result = await session.execute(
        select(WellbeingLog).where(
            and_(
                WellbeingLog.user_id == user_id,
                WellbeingLog.logged_date >= date_from,
                WellbeingLog.logged_date <= date_to,
            )
        )
    )
    logs = list(result.scalars())
    return _build_wellbeing_details(logs)
