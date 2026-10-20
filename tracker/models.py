
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models.functions import Lower

hex_color = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Color must be a six-digit hexadecimal value such as #7C5CFC.",
)


class Habit(models.Model):
    class Category(models.TextChoices):
        HEALTH = "health", "Health"
        LEARNING = "learning", "Learning"
        MINDFULNESS = "mindfulness", "Mindfulness"
        PRODUCTIVITY = "productivity", "Productivity"
        SOCIAL = "social", "Social"
        FINANCE = "finance", "Finance"
        OTHER = "other", "Other"

    owner = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="habits",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=280, blank=True)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
    )
    color = models.CharField(max_length=7, default="#7C5CFC", validators=[hex_color])
    target_per_week = models.PositiveSmallIntegerField(
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
    )
    reminder_time = models.TimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["is_archived", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(target_per_week__gte=1, target_per_week__lte=7),
                name="habit_target_between_1_and_7",
            ),
            models.UniqueConstraint(
                Lower("name"),
                "owner",
                condition=models.Q(is_archived=False),
                name="unique_active_habit_name_per_owner",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "is_archived"], name="habit_owner_active_idx"),
            models.Index(fields=["owner", "category"], name="habit_owner_category_idx"),
        ]

    def __str__(self):
        return self.name


class HabitCheckIn(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="check_ins")
    completed_on = models.DateField()
    note = models.CharField(max_length=240, blank=True)
    effort = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-completed_on", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["habit", "completed_on"],
                name="unique_habit_checkin_per_day",
            ),
            models.CheckConstraint(
                condition=models.Q(effort__gte=1, effort__lte=5),
                name="checkin_effort_between_1_and_5",
            ),
        ]
        indexes = [
            models.Index(fields=["habit", "completed_on"], name="checkin_habit_date_idx"),
        ]

    def __str__(self):
        return f"{self.habit.name} on {self.completed_on:%Y-%m-%d}"
