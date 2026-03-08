from datetime import date, datetime, time, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import MedicationCourse, MedicationLog, User
from backend.services.rpg_service import EXP_TABLE, add_exp, remove_exp


def _build_medication_schedule_items(
    courses: list[MedicationCourse],
    logs: list[MedicationLog],
    target_day: date,
) -> list[dict[str, str | int | date]]:
    if not courses:
        return []

    logs_by_course = {
        log.course_id: log
        for log in logs
        if log.course_id is not None and log.scheduled_date == target_day
    }

    items: list[dict[str, str | int | date]] = []
    for course in sorted(courses, key=lambda item: (item.intake_time, item.title.lower(), item.id)):
        if not (course.start_date <= target_day <= course.end_date):
            continue
        log = logs_by_course.get(course.id)
        items.append(
            {
                "course_id": course.id,
                "title": course.title,
                "dose": course.dose,
                "intake_time": course.intake_time.strftime("%H:%M"),
                "start_date": course.start_date,
                "end_date": course.end_date,
                "days_left": max((course.end_date - target_day).days + 1, 0),
                "status": "taken" if log and log.status == "taken" else "skipped",
            }
        )
    return items


def _build_medication_calendar_marks(
    courses: list[MedicationCourse],
    logs: list[MedicationLog],
    date_from: date,
    date_to: date,
) -> dict[date, str]:
    statuses_by_day: dict[date, dict[str, int]] = {}

    day = date_from
    while day <= date_to:
        scheduled = sum(1 for course in courses if course.start_date <= day <= course.end_date and course.is_active)
        if scheduled:
            statuses_by_day[day] = {"scheduled": scheduled, "taken": 0, "skipped": 0}
        day += timedelta(days=1)

    for log in logs:
        scheduled_date = log.scheduled_date
        if scheduled_date is None or scheduled_date not in statuses_by_day:
            continue
        if log.status == "taken":
            statuses_by_day[scheduled_date]["taken"] += 1
        elif log.status == "skipped":
            statuses_by_day[scheduled_date]["skipped"] += 1

    marks: dict[date, str] = {}
    for day_key, values in statuses_by_day.items():
        scheduled = values["scheduled"]
        taken = values["taken"]
        skipped = values["skipped"]
        if taken == scheduled and scheduled > 0:
            marks[day_key] = "done"
        else:
            marks[day_key] = "skipped"
    return marks


def _build_medication_details(
    courses: list[MedicationCourse],
    logs: list[MedicationLog],
    date_from: date,
    date_to: date,
) -> dict[str, int | str]:
    scheduled_by_day: dict[date, int] = {}
    scheduled_by_title: dict[str, int] = {}
    unique_titles: set[str] = set()

    for course in courses:
        overlap_start = max(course.start_date, date_from)
        overlap_end = min(course.end_date, date_to)
        if overlap_start > overlap_end:
            continue
        day = overlap_start
        while day <= overlap_end:
            scheduled_by_day[day] = scheduled_by_day.get(day, 0) + 1
            scheduled_by_title[course.title] = scheduled_by_title.get(course.title, 0) + 1
            unique_titles.add(course.title)
            day += timedelta(days=1)

    total_scheduled = sum(scheduled_by_day.values())
    if total_scheduled == 0 and not logs:
        return {
            "total_logs": 0,
            "active_days": 0,
            "unique_titles": 0,
            "best_day_logs": 0,
            "top_title": "",
            "taken_count": 0,
            "skipped_count": 0,
        }

    taken_count = 0

    for log in logs:
        if log.status == "taken":
            taken_count += 1

    top_title = ""
    if scheduled_by_title:
        top_title = sorted(scheduled_by_title.items(), key=lambda item: (-item[1], item[0].lower()))[0][0]

    skipped_count = max(total_scheduled - taken_count, 0)

    return {
        "total_logs": total_scheduled,
        "active_days": len(scheduled_by_day),
        "unique_titles": len(unique_titles),
        "best_day_logs": max(scheduled_by_day.values()) if scheduled_by_day else 0,
        "top_title": top_title,
        "taken_count": taken_count,
        "skipped_count": skipped_count,
    }


async def add_medication_log(
    session: AsyncSession,
    user: User,
    title: str,
    dose: str,
    logged_at: datetime | None = None,
) -> tuple[MedicationLog, int]:
    medication_log = MedicationLog(
        user_id=user.id,
        title=title.strip(),
        dose=dose.strip(),
        logged_at=logged_at or datetime.utcnow(),
    )
    session.add(medication_log)
    level_ups = add_exp(user, EXP_TABLE["medication_logged"])
    await session.commit()
    await session.refresh(medication_log)
    await session.refresh(user)
    return medication_log, level_ups


async def create_medication_course(
    session: AsyncSession,
    user: User,
    title: str,
    dose: str,
    intake_time: time,
    start_date: date,
    days_count: int,
) -> MedicationCourse:
    safe_days = max(1, days_count)
    course = MedicationCourse(
        user_id=user.id,
        title=title.strip(),
        dose=dose.strip(),
        intake_time=intake_time,
        start_date=start_date,
        end_date=start_date.fromordinal(start_date.toordinal() + safe_days - 1),
        is_active=True,
    )
    session.add(course)
    await session.commit()
    await session.refresh(course)
    return course


async def archive_medication_course(session: AsyncSession, user: User, course_id: int) -> bool:
    result = await session.execute(
        select(MedicationCourse).where(
            and_(
                MedicationCourse.id == course_id,
                MedicationCourse.user_id == user.id,
            )
        )
    )
    course = result.scalar_one_or_none()
    if not course:
        return False

    course.is_active = False
    await session.commit()
    return True


async def remove_last_medication_log(
    session: AsyncSession,
    user: User,
    target_day: date,
) -> tuple[str | None, str | None, int]:
    start_dt = datetime.combine(target_day, datetime.min.time())
    end_dt = datetime.combine(target_day, datetime.max.time())

    result = await session.execute(
        select(MedicationLog)
        .where(
            and_(
                MedicationLog.user_id == user.id,
                MedicationLog.logged_at >= start_dt,
                MedicationLog.logged_at <= end_dt,
            )
        )
        .order_by(MedicationLog.logged_at.desc(), MedicationLog.id.desc())
        .limit(1)
    )
    medication_log = result.scalar_one_or_none()
    if not medication_log:
        return None, None, 0

    title = medication_log.title
    dose = medication_log.dose
    await session.delete(medication_log)
    level_change = -remove_exp(user, EXP_TABLE["medication_logged"])
    await session.commit()
    await session.refresh(user)
    return title, dose, level_change


async def toggle_medication_intake_status(
    session: AsyncSession,
    user: User,
    course_id: int,
    target_day: date,
    status: str,
) -> tuple[str | None, MedicationCourse | None, int]:
    if status != "taken":
        return None, None, 0

    course_result = await session.execute(
        select(MedicationCourse).where(
            and_(
                MedicationCourse.id == course_id,
                MedicationCourse.user_id == user.id,
                MedicationCourse.is_active.is_(True),
                MedicationCourse.start_date <= target_day,
                MedicationCourse.end_date >= target_day,
            )
        )
    )
    course = course_result.scalar_one_or_none()
    if not course:
        return None, None, 0

    existing_result = await session.execute(
        select(MedicationLog).where(
            and_(
                MedicationLog.user_id == user.id,
                MedicationLog.course_id == course.id,
                MedicationLog.scheduled_date == target_day,
            )
        )
    )
    existing_log = existing_result.scalar_one_or_none()

    if existing_log and existing_log.status == status:
        await session.delete(existing_log)
        level_change = -remove_exp(user, EXP_TABLE["medication_logged"])
        await session.commit()
        await session.refresh(user)
        return "skipped", course, level_change

    if existing_log:
        previous_status = existing_log.status
        existing_log.status = status
        existing_log.logged_at = datetime.utcnow()
        level_change = add_exp(user, EXP_TABLE["medication_logged"]) if previous_status != "taken" else 0
        await session.commit()
        await session.refresh(user)
        return status, course, level_change

    medication_log = MedicationLog(
        user_id=user.id,
        course_id=course.id,
        title=course.title,
        dose=course.dose,
        scheduled_date=target_day,
        status=status,
        logged_at=datetime.utcnow(),
    )
    session.add(medication_log)
    level_change = 0
    level_change = add_exp(user, EXP_TABLE["medication_logged"])
    await session.commit()
    await session.refresh(user)
    return status, course, level_change


async def list_day_medication_logs(
    session: AsyncSession,
    user_id: int,
    target_day: date,
    *,
    limit: int = 3,
) -> list[MedicationLog]:
    start_dt = datetime.combine(target_day, datetime.min.time())
    end_dt = datetime.combine(target_day, datetime.max.time())

    result = await session.execute(
        select(MedicationLog)
        .where(
            and_(
                MedicationLog.user_id == user_id,
                MedicationLog.logged_at >= start_dt,
                MedicationLog.logged_at <= end_dt,
            )
        )
        .order_by(MedicationLog.logged_at.desc(), MedicationLog.id.desc())
        .limit(limit)
    )
    return list(result.scalars())


async def list_medication_schedule_for_day(
    session: AsyncSession,
    user_id: int,
    target_day: date,
) -> list[dict[str, str | int | date]]:
    courses_result = await session.execute(
        select(MedicationCourse)
        .where(
            and_(
                MedicationCourse.user_id == user_id,
                MedicationCourse.is_active.is_(True),
                MedicationCourse.start_date <= target_day,
                MedicationCourse.end_date >= target_day,
            )
        )
        .order_by(MedicationCourse.intake_time.asc(), MedicationCourse.title.asc(), MedicationCourse.id.asc())
    )
    courses = list(courses_result.scalars())
    course_ids = [course.id for course in courses]
    if not course_ids:
        return []

    logs_result = await session.execute(
        select(MedicationLog).where(
            and_(
                MedicationLog.user_id == user_id,
                MedicationLog.scheduled_date == target_day,
                MedicationLog.course_id.in_(course_ids),
            )
        )
    )
    logs = list(logs_result.scalars())
    return _build_medication_schedule_items(courses, logs, target_day)


async def get_medication_calendar_marks(
    session: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
) -> dict[date, str]:
    courses_result = await session.execute(
        select(MedicationCourse).where(
            and_(
                MedicationCourse.user_id == user_id,
                MedicationCourse.is_active.is_(True),
                MedicationCourse.start_date <= date_to,
                MedicationCourse.end_date >= date_from,
            )
        )
    )
    courses = list(courses_result.scalars())
    if not courses:
        return {}

    logs_result = await session.execute(
        select(MedicationLog).where(
            and_(
                MedicationLog.user_id == user_id,
                MedicationLog.scheduled_date >= date_from,
                MedicationLog.scheduled_date <= date_to,
                MedicationLog.course_id.is_not(None),
            )
        )
    )
    logs = list(logs_result.scalars())
    return _build_medication_calendar_marks(courses, logs, date_from, date_to)


async def get_medication_details_for_period(
    session: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
) -> dict[str, int | str]:
    courses_result = await session.execute(
        select(MedicationCourse).where(
            and_(
                MedicationCourse.user_id == user_id,
                MedicationCourse.start_date <= date_to,
                MedicationCourse.end_date >= date_from,
            )
        )
    )
    courses = list(courses_result.scalars())

    result = await session.execute(
        select(MedicationLog).where(
            and_(
                MedicationLog.user_id == user_id,
                MedicationLog.scheduled_date >= date_from,
                MedicationLog.scheduled_date <= date_to,
            )
        )
    )
    logs = list(result.scalars())
    return _build_medication_details(courses, logs, date_from, date_to)
