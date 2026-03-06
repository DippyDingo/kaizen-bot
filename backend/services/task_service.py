from datetime import date, datetime

from sqlalchemy import and_, select
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
    result = await session.execute(
        select(Task)
        .where(and_(Task.user_id == user_id, Task.task_date == task_date))
        .order_by(Task.is_done.asc(), Task.id.asc())
    )
    return list(result.scalars().all())


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
