
from django.contrib import admin

from .models import Habit, HabitCheckIn


class HabitCheckInInline(admin.TabularInline):
    model = HabitCheckIn
    extra = 0
    ordering = ("-completed_on",)


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "category", "target_per_week", "is_archived", "updated_at")
    list_filter = ("category", "is_archived")
    search_fields = ("name", "owner__username")
    readonly_fields = ("version", "created_at", "updated_at", "archived_at")
    inlines = (HabitCheckInInline,)


@admin.register(HabitCheckIn)
class HabitCheckInAdmin(admin.ModelAdmin):
    list_display = ("habit", "completed_on", "effort", "created_at")
    list_filter = ("completed_on", "effort")
    search_fields = ("habit__name", "habit__owner__username", "note")


