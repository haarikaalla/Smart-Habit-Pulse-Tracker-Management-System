
from django.urls import path

from . import secure_views

urlpatterns = [
    path("health/live/", secure_views.health, name="health"),
    path("health/ready/", secure_views.readiness, name="readiness"),
    path("health/", secure_views.health, name="health_compat"),
    path("", secure_views.dashboard, name="home"),
    path("api/v1/habits/", secure_views.habits, name="habits"),
    path("api/v1/habits/<int:habit_id>/", secure_views.habit_detail, name="habit_detail"),
    path("api/v1/habits/<int:habit_id>/check-in/", secure_views.habit_check_in, name="habit_check_in"),
    path("api/v1/analytics/", secure_views.analytics, name="analytics"),
    path("api/v1/export/", secure_views.export_data, name="export_data"),
]
