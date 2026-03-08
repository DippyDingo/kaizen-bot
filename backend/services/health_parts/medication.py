from datetime import date, datetime, time, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import MedicationCourse, MedicationLog, User
from backend.services.rpg_service import EXP_TABLE, add_exp, remove_exp


def _latest_course_logs_by_day(logs: list[MedicationLog]) -> dict[tuple[date, int], MedicationLog]:
    latest: dict[tuple[date, int], MedicationLog] = {}
    for log in logs:
        if log.course_id is None or log.scheduled_date is None:
            continue
        key = (log.scheduled_date, log.course_id)
        current = latest.get(key)
        if current is None:
            latest[key] = log
            continue
        current_marker = (current.logged_at, current.created_at, current.id)
        log_marker = (log.logged_at, log.created_at, log.id)
        if log_marker >= current_marker:
            latest[key] = log
    return latest


def _course_is_scheduled_on_day(course: MedicationCourse, target_day: date, *, active_only: bool = True) -> bool:
    if active_only and not course.is_active:
        return False
    return course.start_date <= target_day <= course.end_date


def _resolve_medication_item_status(
    log: MedicationLog | None,
    target_day: date,
    *,
    today: date | None = None,
) -> str:
    resolved_today = today or date.today()
    if log is not None:
        if log.status == "taken":
            return "taken"
        if log.status == "skipped":
            return "skipped"
    return "pending" if target_day >= resolved_today else "skipped"


def _build_medication_day_buckets(
    courses: list[MedicationCourse],
    logs: list[MedicationLog],
    date_from: date,
    date_to: date,
    *,
    today: date | None = None,
    active_only: bool = True,
) -> dict[date, dict[str, int]]:
    latest_logs = _latest_course_logs_by_day(logs)
    resolved_today = today or date.today()
    buckets: dict[date, dict[str, int]] = {}

    day = date_from
    while day <= date_to:
        day_courses = [course for course in courses if _course_is_scheduled_on_day(course, day, active_only=active_only)]
        if day_courses:
            bucket = {"scheduled": len(day_courses), "taken": 0, "pending": 0, "skipped": 0}
            for course in day_courses:
                status = _resolve_medication_item_status(
                    latest_logs.get((day, course.id)),
                    day,
                    today=resolved_today,
                )
                bucket[status] += 1
            buckets[day] = bucket
        day += timedelta(days=1)

    return buckets


def _build_medication_schedule_items(
    courses: list[MedicationCourse],
    logs: list[MedicationLog],
    target_day: date,
    *,
    today: date | None = None,
) -> list[dict[str, str | int | date]]:
    if not courses:
        return []

    latest_logs = _latest_course_logs_by_day(logs)
    resolved_today = today or date.today()

    items: list[dict[str, str | int | date]] = []
    for course in sorted(courses, key=lambda item: (item.intake_time, item.title.lower(), item.id)):
        if not _course_is_scheduled_on_day(course, target_day, active_only=True):
            continue
        log = latest_logs.get((target_day, course.id))
        items.append(
            {
                "course_id": course.id,
                "title": course.title,
                "dose": course.dose,
                "intake_time": course.intake_time.strftime("%H:%M"),
                "start_date": course.start_date,
                "end_date": course.end_date,
                "days_left": max((course.end_date - target_day).days + 1, 0),
                "status": _resolve_medication_item_status(log, target_day, today=resolved_today),
            }
        )
    return items


def _build_medication_calendar_marks(
    courses: list[MedicationCourse],
    logs: list[MedicationLog],
    date_from: date,
    date_to: date,
    *,
    today: date | None = None,
) -> dict[date, str]:
    day_buckets = _build_medication_day_buckets(courses, logs, date_from, date_to, today=today, active_only=True)
    marks: dict[date, str] = {}
    for day_key, values in day_buckets.items():
        if values["taken"] == values["scheduled"] and values["scheduled"] > 0:
            marks[day_key] = "done"
        elif values["skipped"] > 0:
            marks[day_key] = "skipped"
        else:
            marks[day_key] = "planned"
    return marks


def _build_medication_details(
    courses: list[MedicationCourse],
    logs: list[MedicationLog],
    date_from: date,
    date_to: date,
    *,
    today: date | None = None,
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
            "pending_count": 0,
            "skipped_count": 0,
        }

    day_buckets = _build_medication_day_buckets(courses, logs, date_from, date_to, today=today, active_only=False)
    taken_count = sum(values["taken"] for values in day_buckets.values())
    pending_count = sum(values["pending"] for values in day_buckets.values())
    skipped_count = sum(values["skipped"] for values in day_buckets.values())

    top_title = ""
    if scheduled_by_title:
        top_title = sorted(scheduled_by_title.items(), key=lambda item: (-item[1], item[0].lower()))[0][0]

    return {
        "total_logs": total_scheduled,
        "active_days": len(scheduled_by_day),
        "unique_titles": len(unique_titles),
        "best_day_logs": max(scheduled_by_day.values()) if scheduled_by_day else 0,
        "top_title": top_title,
        "taken_count": taken_count,
        "pending_count": pending_count,
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
        select(MedicationLog)
        .where(
            and_(
                MedicationLog.user_id == user.id,
                MedicationLog.course_id == course.id,
                MedicationLog.scheduled_date == target_day,
            )
        )
        .order_by(MedicationLog.logged_at.desc(), MedicationLog.created_at.desc(), MedicationLog.id.desc())
    )
    existing_logs = list(existing_result.scalars())
    existing_log = existing_logs[0] if existing_logs else None

    if existing_log and existing_log.status == status:
        for log in existing_logs:
            await session.delete(log)
        level_change = -remove_exp(user, EXP_TABLE["medication_logged"])
        await session.commit()
        await session.refresh(user)
        return _resolve_medication_item_status(None, target_day), course, level_change

    if existing_log:
        previous_status = existing_log.status
        existing_log.status = status
        existing_log.logged_at = datetime.utcnow()
        for stale_log in existing_logs[1:]:
            await session.delete(stale_log)
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
