from datetime import date, datetime

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Task, User
from backend.services.rpg_service import EXP_TABLE, add_exp, remove_exp


async def create_task(
    session: AsyncSession,
    user: User,
    title: str,
    task_date: date,
    priority: str = "medium",
) -> Task:
    task = Task(
        user_id=user.id,
        title=title,
        task_date=task_date,
        priority=priority,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def list_tasks_for_date(session: AsyncSession, user_id: int, task_date: date) -> list[Task]:
    priority_order = case(
        (Task.priority == "high", 0),
        (Task.priority == "medium", 1),
        (Task.priority == "low", 2),
        else_=3,
    )
    result = await session.execute(
        select(Task)
        .where(and_(Task.user_id == user_id, Task.task_date == task_date))
        .order_by(Task.is_done.asc(), priority_order.asc(), Task.id.asc())
    )
    return list(result.scalars().all())


async def get_task_totals(session: AsyncSession, user_id: int) -> tuple[int, int]:
    result = await session.execute(
        select(
            func.count(Task.id),
            func.coalesce(func.sum(case((Task.is_done.is_(True), 1), else_=0)), 0),
        ).where(Task.user_id == user_id)
    )
    total, done = result.one()
    return int(total or 0), int(done or 0)


async def get_task_totals_for_period(
    session: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
) -> tuple[int, int]:
    result = await session.execute(
        select(
            func.count(Task.id),
            func.coalesce(func.sum(case((Task.is_done.is_(True), 1), else_=0)), 0),
        ).where(
            and_(
                Task.user_id == user_id,
                Task.task_date >= date_from,
                Task.task_date <= date_to,
            )
        )
    )
    total, done = result.one()
    return int(total or 0), int(done or 0)


async def get_task_details_for_period(
    session: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
) -> dict[str, int]:
    result = await session.execute(
        select(
            func.count(Task.id),
            func.coalesce(func.sum(case((Task.is_done.is_(True), 1), else_=0)), 0),
            func.coalesce(func.sum(case((Task.priority == "high", 1), else_=0)), 0),
            func.coalesce(func.sum(case((Task.priority == "medium", 1), else_=0)), 0),
            func.coalesce(func.sum(case((Task.priority == "low", 1), else_=0)), 0),
            func.count(func.distinct(Task.task_date)),
        ).where(
            and_(
                Task.user_id == user_id,
                Task.task_date >= date_from,
                Task.task_date <= date_to,
            )
        )
    )
    total, done, high_count, medium_count, low_count, active_days = result.one()
    return {
        "total": int(total or 0),
        "done": int(done or 0),
        "high_count": int(high_count or 0),
        "medium_count": int(medium_count or 0),
        "low_count": int(low_count or 0),
        "active_days": int(active_days or 0),
    }


async def get_task_calendar_marks(
    session: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
) -> dict[date, dict[str, int | str]]:
    result = await session.execute(
        select(
            Task.task_date,
            func.count(Task.id),
            func.coalesce(func.sum(case((Task.is_done.is_(True), 1), else_=0)), 0),
        ).where(
            and_(
                Task.user_id == user_id,
                Task.task_date >= date_from,
                Task.task_date <= date_to,
            )
        )
        .group_by(Task.task_date)
    )

    marks: dict[date, dict[str, int | str]] = {}
    for task_date, total, done in result.all():
        total_int = int(total or 0)
        done_int = int(done or 0)
        if total_int <= 0:
            continue
        if done_int == total_int:
            status = "done"
        elif done_int > 0:
            status = "mixed"
        else:
            status = "open"
        marks[task_date] = {
            "total": total_int,
            "done": done_int,
            "status": status,
        }
    return marks


async def toggle_task_done(
    session: AsyncSession,
    user: User,
    task_id: int,
) -> tuple[Task | None, bool, int]:
    result = await session.execute(
        select(Task).where(and_(Task.id == task_id, Task.user_id == user.id))
    )
    task = result.scalar_one_or_none()
    if not task:
        return None, False, 0

    if task.is_done:
        task.is_done = False
        task.done_at = None
        level_change = -remove_exp(user, EXP_TABLE["task_completed"])
        await session.commit()
        await session.refresh(task)
        await session.refresh(user)
        return task, False, level_change

    task.is_done = True
    task.done_at = datetime.utcnow()
    level_change = add_exp(user, EXP_TABLE["task_completed"])
    await session.commit()
    await session.refresh(task)
    await session.refresh(user)
    return task, True, level_change


async def delete_task(
    session: AsyncSession,
    user: User,
    task_id: int,
) -> bool:
    result = await session.execute(
        select(Task).where(and_(Task.id == task_id, Task.user_id == user.id))
    )
    task = result.scalar_one_or_none()
    if not task:
        return False

    await session.delete(task)
    await session.commit()
    return True
