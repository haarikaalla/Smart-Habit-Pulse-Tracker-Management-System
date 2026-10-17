import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import Habit


def _payload(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON") from exc


def _serialize(habit):
    return {
        "id": habit.id,
        "name": habit.name,
        "completed": habit.completed,
        "target_per_week": habit.target_per_week,
        "created_at": habit.created_at.isoformat(),
        "updated_at": habit.updated_at.isoformat(),
    }


@login_required
def dashboard(request):
    return render(request, "dashboard.html")


@login_required
@require_http_methods(["GET", "POST"])
def habits(request):
    if request.method == "GET":
        rows = Habit.objects.filter(owner=request.user)
        return JsonResponse({"habits": [_serialize(row) for row in rows]})

    try:
        data = _payload(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    name = str(data.get("name", "")).strip()
    if not 1 <= len(name) <= 100:
        return JsonResponse({"error": "Name must contain 1–100 characters"}, status=422)

    try:
        target = int(data.get("target_per_week", 7))
    except (TypeError, ValueError):
        return JsonResponse({"error": "target_per_week must be an integer"}, status=422)
    if not 1 <= target <= 7:
        return JsonResponse({"error": "target_per_week must be between 1 and 7"}, status=422)

    habit = Habit.objects.create(owner=request.user, name=name, target_per_week=target)
    return JsonResponse({"habit": _serialize(habit)}, status=201)


@login_required
@require_http_methods(["PATCH", "DELETE"])
def habit_detail(request, habit_id):
    habit = get_object_or_404(Habit, id=habit_id, owner=request.user)
    if request.method == "DELETE":
        habit.delete()
        return JsonResponse({}, status=204)

    try:
        data = _payload(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    if "completed" in data and not isinstance(data["completed"], bool):
        return JsonResponse({"error": "completed must be a boolean"}, status=422)
    if "completed" in data:
        habit.completed = data["completed"]
    if "name" in data:
        name = str(data["name"]).strip()
        if not 1 <= len(name) <= 100:
            return JsonResponse({"error": "Name must contain 1–100 characters"}, status=422)
        habit.name = name

    with transaction.atomic():
        habit.save(update_fields=["name", "completed", "updated_at"])
    return JsonResponse({"habit": _serialize(habit)})


@login_required
@require_http_methods(["GET"])
def summary(request):
    rows = Habit.objects.filter(owner=request.user)
    total = rows.count()
    completed = rows.filter(completed=True).count()
    return JsonResponse(
        {
            "total": total,
            "completed": completed,
            "pending": total - completed,
            "completion_rate": round((completed / total) * 100, 1) if total else 0.0,
        }
    )
