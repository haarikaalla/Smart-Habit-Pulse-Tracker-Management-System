from django.shortcuts import render
from django.http import JsonResponse
from .models import Habit
from django.views.decorators.csrf import csrf_exempt
import json


def home(request):
    return render(request, 'index.html')


@csrf_exempt
def add_habit(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("name")

            if not name:
                return JsonResponse({"status": "fail", "error": "Name is required"})
            
            habit = Habit.objects.create(name=name)

            return JsonResponse({
                "status": "success",
                "habit": {
                    "id": habit.id,
                    "name": habit.name,
                    "completed": habit.completed,
                    "created_at": habit.created_at.strftime("%Y-%m-%d %H:%M:%S")
                }
            })
        except json.JSONDecodeError:
            return JsonResponse({"status": "fail", "error": "Invalid JSON"})
    
    return JsonResponse({"status": "fail", "error": "Invalid request method"})


def get_habits(request):
    habits = Habit.objects.all().order_by('-created_at')
    data = []

    for habit in habits:
        data.append({
            "id": habit.id,
            "name": habit.name,
            "completed": habit.completed,
            "created_at": habit.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return JsonResponse(data, safe=False)


@csrf_exempt
def update_habit(request, id):
    try:
        habit = Habit.objects.get(id=id)
    except Habit.DoesNotExist:
        return JsonResponse({"status": "fail", "error": "Habit not found"})

    if request.method == "PUT":
        data = json.loads(request.body)
        habit.completed = data.get("completed", habit.completed)
        habit.save()
        return JsonResponse({"status": "success"})
    
    if request.method == "DELETE":
        habit.delete()
        return JsonResponse({"status": "success"})

    return JsonResponse({"status": "fail", "error": "Invalid request method"})


# DASHBOARD
def dashboard_data(request):
    total = Habit.objects.count()
    completed = Habit.objects.filter(completed=True).count()
    pending = Habit.objects.filter(completed=False).count()

    return JsonResponse({
        "total": total,
        "completed": completed,
        "pending": pending
    })
