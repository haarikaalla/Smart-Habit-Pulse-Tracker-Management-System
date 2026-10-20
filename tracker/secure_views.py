import json

from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .models import Habit
from .services import (
    DomainError,
    archive_habit,
    build_analytics,
    create_habit,
    habit_queryset,
    serialize_habit,
    set_check_in,
    update_habit,
)


def _error(message, *, code="invalid_request", status=400, fields=None):
    payload = {"error": {"code": code, "message": message}}
    if fields:
        payload["error"]["fields"] = fields
    return JsonResponse(payload, status=status)


def _domain_error(exc):
    return _error(exc.message, code=exc.code, status=exc.status)


def _payload(request):
    try:
        data = json.loads(request.body or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DomainError("Request body must be valid JSON.", code="invalid_json", status=400) from exc
    if not isinstance(data, dict):
        raise DomainError("Request body must be a JSON object.", code="invalid_json", status=400)
    return data


@require_http_methods(["GET"])
def health(request):
    return JsonResponse({"status": "ok", "service": "habitpulse", "api_version": "v1"})


@require_http_methods(["GET"])
def readiness(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unavailable", "database": "disconnected"}, status=503)
    return JsonResponse({"status": "ready", "database": "connected"})


@login_required
@require_http_methods(["GET"])
def dashboard(request):
    return render(request, "dashboard.html", {"categories": Habit.Category.choices})


@login_required
@require_http_methods(["GET", "POST"])
def habits(request):
    if request.method == "GET":
        include_archived = request.GET.get("archived") == "true"
        rows = habit_queryset(request.user, include_archived=include_archived)
        query = request.GET.get("q", "").strip()
        category = request.GET.get("category", "").strip().lower()
        if query:
            rows = rows.filter(name__icontains=query)
        if category:
            rows = rows.filter(category=category)
        return JsonResponse({"habits": [serialize_habit(row) for row in rows]})

    try:
        habit = create_habit(owner=request.user, data=_payload(request))
        habit.recent_check_ins = []
        return JsonResponse({"habit": serialize_habit(habit)}, status=201)
    except DomainError as exc:
        return _domain_error(exc)


@login_required
@require_http_methods(["GET", "PATCH", "DELETE"])
def habit_detail(request, habit_id):
    if request.method == "GET":
        habit = habit_queryset(request.user, include_archived=True).filter(id=habit_id).first()
        if not habit:
            return _error("Habit not found.", code="not_found", status=404)
        return JsonResponse({"habit": serialize_habit(habit)})

    try:
        if request.method == "DELETE":
            archive_habit(owner=request.user, habit_id=habit_id)
            return JsonResponse({"status": "archived"})
        habit = update_habit(owner=request.user, habit_id=habit_id, data=_payload(request))
        habit.recent_check_ins = list(habit.check_ins.order_by("completed_on"))
        return JsonResponse({"habit": serialize_habit(habit)})
    except DomainError as exc:
        return _domain_error(exc)


@login_required
@require_http_methods(["PUT"])
def habit_check_in(request, habit_id):
    try:
        check_in, changed = set_check_in(owner=request.user, habit_id=habit_id, data=_payload(request))
        return JsonResponse(
            {
                "completed": check_in is not None,
                "changed": changed,
                "check_in": (
                    {
                        "id": check_in.id,
                        "date": check_in.completed_on.isoformat(),
                        "note": check_in.note,
                        "effort": check_in.effort,
                    }
                    if check_in
                    else None
                ),
            }
        )
    except DomainError as exc:
        return _domain_error(exc)


@login_required
@require_http_methods(["GET"])
def analytics(request):
    try:
        days = int(request.GET.get("days", 28))
    except ValueError:
        return _error("days must be an integer.", code="invalid_days", status=422)
    return JsonResponse(build_analytics(request.user, days=days))


@login_required
@require_http_methods(["GET"])
def export_data(request):
    habits_data = []
    for habit in Habit.objects.filter(owner=request.user).prefetch_related("check_ins"):
        item = serialize_habit(habit)
        item["check_ins"] = [
            {
                "date": check_in.completed_on.isoformat(),
                "note": check_in.note,
                "effort": check_in.effort,
            }
            for check_in in habit.check_ins.all()
        ]
        habits_data.append(item)
    response = JsonResponse(
        {"schema_version": "1.0", "exported_user": request.user.get_username(), "habits": habits_data}
    )
    response["Content-Disposition"] = 'attachment; filename="habitpulse-export.json"'
    return response
