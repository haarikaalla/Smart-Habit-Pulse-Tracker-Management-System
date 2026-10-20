from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F, Prefetch
from django.utils import timezone

from .models import Habit, HabitCheckIn


class DomainError(Exception):
    def __init__(self, message: str, *, code: str = "invalid_request", status: int = 422):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def parse_date(value: Any, *, default: date | None = None) -> date:
    if value in (None, "") and default is not None:
        return default
    try:
        parsed = date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise DomainError("Date must use YYYY-MM-DD format.", code="invalid_date") from exc
    if parsed > timezone.localdate():
        raise DomainError("Future check-ins are not allowed.", code="future_date")
    return parsed


def _clean_habit(habit: Habit) -> Habit:
    try:
        habit.full_clean(exclude=["owner"])
    except ValidationError as exc:
        message = next(iter(exc.message_dict.values()))[0] if exc.message_dict else str(exc)
        raise DomainError(message, code="validation_error") from exc
    return habit


def create_habit(*, owner, data: dict[str, Any]) -> Habit:
    habit = Habit(
        owner=owner,
        name=str(data.get("name", "")).strip(),
        description=str(data.get("description", "")).strip(),
        category=str(data.get("category", Habit.Category.OTHER)).lower(),
        color=str(data.get("color", "#7C5CFC")).upper(),
        target_per_week=data.get("target_per_week", 7),
        reminder_time=data.get("reminder_time") or None,
    )
    _clean_habit(habit)
    try:
        with transaction.atomic():
            habit.save()
    except IntegrityError as exc:
        raise DomainError(
            "You already have an active habit with this name.",
            code="duplicate_habit",
            status=409,
        ) from exc
    return habit


def update_habit(*, owner, habit_id: int, data: dict[str, Any]) -> Habit:
    expected_version = data.get("expected_version")
    if not isinstance(expected_version, int):
        raise DomainError("expected_version is required and must be an integer.", code="version_required")

    with transaction.atomic():
        try:
            habit = Habit.objects.select_for_update().get(id=habit_id, owner=owner, is_archived=False)
        except Habit.DoesNotExist as exc:
            raise DomainError("Habit not found.", code="not_found", status=404) from exc
        if habit.version != expected_version:
            raise DomainError(
                "This habit changed in another session. Refresh before saving again.",
                code="version_conflict",
                status=409,
            )

        editable = {"name", "description", "category", "color", "target_per_week", "reminder_time"}
        for field in editable.intersection(data):
            value = data[field]
            if field in {"name", "description"}:
                value = str(value).strip()
            if field == "category":
                value = str(value).lower()
            if field == "color":
                value = str(value).upper()
            if field == "reminder_time" and value == "":
                value = None
            setattr(habit, field, value)
        habit.version += 1
        _clean_habit(habit)
        try:
            habit.save()
        except IntegrityError as exc:
            raise DomainError(
                "You already have an active habit with this name.",
                code="duplicate_habit",
                status=409,
            ) from exc
    return habit


def archive_habit(*, owner, habit_id: int) -> None:
    updated = Habit.objects.filter(id=habit_id, owner=owner, is_archived=False).update(
        is_archived=True,
        archived_at=timezone.now(),
        version=F("version") + 1,
    )
    if not updated:
        raise DomainError("Habit not found.", code="not_found", status=404)
def set_check_in(*, owner, habit_id: int, data: dict[str, Any]) -> tuple[HabitCheckIn | None, bool]:
    completed = data.get("completed", True)
    if not isinstance(completed, bool):
        raise DomainError("completed must be true or false.", code="invalid_completed")
    completed_on = parse_date(data.get("date"), default=timezone.localdate())
    note = str(data.get("note", "")).strip()
    effort = data.get("effort", 3)
    if len(note) > 240:
        raise DomainError("Check-in notes cannot exceed 240 characters.", code="note_too_long")
    if not isinstance(effort, int) or not 1 <= effort <= 5:
        raise DomainError("effort must be an integer between 1 and 5.", code="invalid_effort")

    try:
        habit = Habit.objects.get(id=habit_id, owner=owner, is_archived=False)
    except Habit.DoesNotExist as exc:
        raise DomainError("Habit not found.", code="not_found", status=404) from exc

    with transaction.atomic():
        if not completed:
            deleted, _ = HabitCheckIn.objects.filter(habit=habit, completed_on=completed_on).delete()
            return None, bool(deleted)
        check_in, created = HabitCheckIn.objects.update_or_create(
            habit=habit,
            completed_on=completed_on,
            defaults={"note": note, "effort": effort},
        )
        return check_in, created


def current_and_best_streak(completed_dates: set[date], *, today: date) -> tuple[int, int]:
    if not completed_dates:
        return 0, 0

    best = 0
    run = 0
    previous = None
    for day in sorted(completed_dates):
        run = run + 1 if previous and day == previous + timedelta(days=1) else 1
        best = max(best, run)
        previous = day

    cursor = today if today in completed_dates else today - timedelta(days=1)
    current = 0
    while cursor in completed_dates:
        current += 1
        cursor -= timedelta(days=1)
    return current, best


def habit_queryset(owner, *, include_archived: bool = False):
    rows = Habit.objects.filter(owner=owner)
    if not include_archived:
        rows = rows.filter(is_archived=False)
    return rows.prefetch_related(
        Prefetch(
            "check_ins",
            queryset=HabitCheckIn.objects.order_by("completed_on"),
            to_attr="recent_check_ins",
        )
    )


def serialize_habit(habit: Habit, *, today: date | None = None) -> dict[str, Any]:
    today = today or timezone.localdate()
    check_ins = list(getattr(habit, "recent_check_ins", habit.check_ins.all()))
    completed_dates = {item.completed_on for item in check_ins}
    week_start = today - timedelta(days=today.weekday())
    week_count = sum(day >= week_start for day in completed_dates)
    current_streak, best_streak = current_and_best_streak(completed_dates, today=today)
    return {
        "id": habit.id,
        "name": habit.name,
        "description": habit.description,
        "category": habit.category,
        "category_label": habit.get_category_display(),
        "color": habit.color,
        "target_per_week": habit.target_per_week,
        "reminder_time": habit.reminder_time.strftime("%H:%M") if habit.reminder_time else None,
        "is_archived": habit.is_archived,
        "version": habit.version,
        "today_completed": today in completed_dates,
        "week_completed": week_count,
        "week_progress": min(round(week_count / habit.target_per_week * 100), 100),
        "current_streak": current_streak,
        "best_streak": best_streak,
        "recent_dates": sorted((day.isoformat() for day in completed_dates), reverse=True)[:14],
        "created_at": habit.created_at.isoformat(),
        "updated_at": habit.updated_at.isoformat(),
    }


def build_analytics(owner, *, days: int = 28) -> dict[str, Any]:
    today = timezone.localdate()
    days = max(7, min(days, 84))
    start = today - timedelta(days=days - 1)
    habits = list(habit_queryset(owner))
    by_date: dict[date, int] = defaultdict(int)
    by_category: dict[str, dict[str, int]] = defaultdict(lambda: {"habits": 0, "check_ins": 0})
    habit_rows = []
    total_streak = 0
    best_streak = 0

    for habit in habits:
        dates = {item.completed_on for item in habit.recent_check_ins}
        scoped_dates = {day for day in dates if day >= start}
        for day in scoped_dates:
            by_date[day] += 1
        by_category[habit.category]["habits"] += 1
        by_category[habit.category]["check_ins"] += len(scoped_dates)
        serialized = serialize_habit(habit, today=today)
        total_streak += serialized["current_streak"]
        best_streak = max(best_streak, serialized["best_streak"])
        habit_rows.append(serialized)

    timeline = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        count = by_date[day]
        timeline.append(
            {
                "date": day.isoformat(),
                "completed": count,
                "available": len(habits),
                "rate": round(count / len(habits) * 100) if habits else 0,
            }
        )

    week_start = today - timedelta(days=today.weekday())
    week_check_ins = sum(value for day, value in by_date.items() if day >= week_start)
    weekly_goal = sum(habit.target_per_week for habit in habits)
    today_completed = by_date[today]
    return {
        "period": {"start": start.isoformat(), "end": today.isoformat(), "days": days},
        "summary": {
            "active_habits": len(habits),
            "today_completed": today_completed,
            "today_rate": round(today_completed / len(habits) * 100) if habits else 0,
            "weekly_check_ins": week_check_ins,
            "weekly_goal": weekly_goal,
            "weekly_adherence": min(round(week_check_ins / weekly_goal * 100), 100) if weekly_goal else 0,
            "total_current_streak": total_streak,
            "best_streak": best_streak,
            "period_check_ins": sum(by_date.values()),
        },
        "timeline": timeline,
        "categories": [
            {"category": key, **value}
            for key, value in sorted(by_category.items(), key=lambda item: item[1]["check_ins"], reverse=True)
        ],
        "habits": habit_rows,
    }
